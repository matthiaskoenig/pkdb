"""Write the migration report as JSON for tools and as Markdown for maintainers and curators."""

import json
import os
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from pkdb.cache import atomic_text
from pkdb.migration.model import (
    Decision,
    DroppedRow,
    MigrationReport,
    Outcome,
    StudyResult,
)
from pkdb.studyformat.text import natural_key

CLASS_ORDER: tuple[Outcome, ...] = (
    "mismatch",
    "not_converted",
    "invalid_v1",
    "intended",
    "identical",
)

DECISION_HEADINGS = {
    "group_count_1": "Groups with count 1 (now individuals)",
    "array_output": "Array outputs",
    "geometric_spread": "Geometric means with sd, se or cv",
    "schedule": "Converted dosing schedules",
    "unreferenced_sheet": "Sheets that study.json never used",
    "registry_date": "Dates that differ from the registry",
    "image_converted": "Converted images",
    "removed_file": "Removed data files",
    "scatter_label": "Renamed scatter outputs",
    "output_label": "Dropped output labels",
    "valueless_row": "Dropped rows without any value",
    "access_private": "Public studies without a release (now private)",
    "label_renamed": "Renamed timecourse labels",
    "reference_replaced": "Replaced reference snapshots",
    "reference_resolved": "Resolved missing references",
    "creator_fallback": "Studies without a creator",
}
# Rows without any value that the converter dropped: thousands, so migration.md
# lists them per sheet, and only for studies that replace their format 1 folder.
VALUELESS = "valueless_row"
PROVEN: tuple[Outcome, ...] = ("identical", "intended")
# Reasons of studies that are not converted, listed again under manual decisions.
REASON_HEADINGS = {
    "registry_sid": "Identifiers that differ from the registry",
    "sheet_name": "Sheet names outside the source pattern",
}


def _cell(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    lines = [
        "| " + " | ".join(header) + " |",
        "|" + "|".join(" --- " for _ in header) + "|",
    ]
    lines += ["| " + " | ".join(_cell(cell) for cell in row) + " |" for row in rows]
    return lines


def _sorted(report: MigrationReport) -> MigrationReport:
    studies = sorted(report.studies, key=lambda s: natural_key(s.study))
    return report.model_copy(update={"studies": studies})


def _by_outcome(report: MigrationReport) -> dict[str, list[StudyResult]]:
    grouped: dict[str, list[StudyResult]] = defaultdict(list)
    for study in report.studies:
        grouped[study.outcome].append(study)
    return grouped


def _summary(
    report: MigrationReport, grouped: dict[str, list[StudyResult]]
) -> list[str]:
    rows = [[name, str(len(grouped[name]))] for name in CLASS_ORDER]
    rows += [
        ["Skipped (format 2)", str(len(report.skipped))],
        ["Moved to papers/", str(len(report.papers))],
        ["Empty folders removed", str(len(report.removed_empty))],
        ["Recovered swaps", str(len(report.recovered))],
    ]
    return ["## Summary", "", *_table(["Class", "Studies"], rows), ""]


def _classes(grouped: dict[str, list[StudyResult]]) -> list[str]:
    lines: list[str] = []
    for name in CLASS_ORDER:
        studies = grouped[name]
        if not studies:
            continue
        lines += [f"## {name} ({len(studies)})", ""]
        if name == "mismatch":
            lines += _table(
                ["Study", "Path", "A", "B"],
                [[s.study, d.path, d.a, d.b] for s in studies for d in s.differences],
            )
            issues = [[s.study, ", ".join(s.issues)] for s in studies if s.issues]
            if issues:
                lines += ["", "Format 2 issue codes:", ""]
                lines += _table(["Study", "Issue codes"], issues)
        elif name == "not_converted":
            lines += _table(
                ["Study", "Reason"], [[s.study, s.reason or ""] for s in studies]
            )
        elif name == "invalid_v1":
            lines += _table(
                ["Study", "Issue codes"],
                [[s.study, ", ".join(s.issues)] for s in studies],
            )
        elif name == "intended":
            lines += _table(
                ["Study", "Changes"],
                [
                    [s.study, ", ".join(f"{c.kind} x {c.count}" for c in s.changes)]
                    for s in studies
                ],
            )
        else:
            lines.append(_cell(", ".join(s.study for s in studies)))
        lines.append("")
    return lines


def _decisions(
    report: MigrationReport, grouped: dict[str, list[StudyResult]]
) -> list[str]:
    lines = ["## Manual decisions", ""]
    by_kind: dict[str, list[list[str]]] = defaultdict(list)
    for study in report.studies:
        written = "yes" if study.written else "no"
        for decision in study.decisions:
            by_kind[decision.kind].append([study.study, decision.detail, written])
    unknown = sorted(kind for kind in by_kind if kind not in DECISION_HEADINGS)
    for kind in [*DECISION_HEADINGS, *unknown]:
        if kind == VALUELESS:
            lines += _valueless(report)
        elif kind in by_kind:
            heading = DECISION_HEADINGS.get(kind, kind)
            lines += [
                f"### {heading}",
                "",
                *_table(["Study", "Detail", "Written"], by_kind[kind]),
                "",
            ]
    lines += _registry(report)
    for code, heading in REASON_HEADINGS.items():
        refused = [
            [s.study, s.reason or ""]
            for s in grouped["not_converted"]
            if (s.reason or "").split(":", 1)[0] == code
        ]
        if refused:
            lines += [f"### {heading}", "", *_table(["Study", "Reason"], refused), ""]
    lines += _papers(report)
    if lines[-2:] == ["## Manual decisions", ""]:
        lines += ["None.", ""]
    return lines


def _count(number: int, noun: str, plural: str | None = None) -> str:
    return f"{number} {noun if number == 1 else plural or noun + 's'}"


def _ranges(numbers: Iterable[int]) -> str:
    """Sorted numbers with runs as ranges, such as `3-5, 8, 11-12`."""
    runs: list[list[int]] = []
    for number in sorted(set(numbers)):
        if runs and number == runs[-1][1] + 1:
            runs[-1][1] = number
        else:
            runs.append([number, number])
    return ", ".join(str(a) if a == b else f"{a}-{b}" for a, b in runs)


def _valueless_rows(study: StudyResult, decisions: list[Decision]) -> list[list[str]]:
    """The dropped rows of a study: one table row per table and format 1 file.

    Each lists the rows as ranges, or the places in study.json, the count and
    the measurements. A decision without its place shows its detail.
    """
    written = "yes" if study.written else "no"
    groups: dict[tuple[str, str], list[DroppedRow]] = defaultdict(list)
    lines = []
    for decision in decisions:
        row = decision.dropped
        if row is None:
            lines.append([study.study, "", "", decision.detail, "1", "", written])
        else:
            file = " ".join(filter(None, (row.file, row.sheet)))
            groups[row.table, file].append(row)
    for (table, file), rows in groups.items():
        numbers = _ranges(row.row for row in rows if row.row is not None)
        paths = dict.fromkeys(row.path for row in rows if row.row is None and row.path)
        measurements = dict.fromkeys(row.measurement for row in rows)
        places = ", ".join(filter(None, (numbers, *paths)))
        lines.append(
            [
                study.study,
                table,
                file,
                places,
                str(len(rows)),
                ", ".join(measurements),
                written,
            ]
        )
    return lines


def _valueless(report: MigrationReport) -> list[str]:
    """Dropped rows without any value, per study, table and format 1 file.

    Only studies that replace their format 1 folder are listed, in a dry run
    those that would; migration.json lists every dropped row of every study.
    """
    lines: list[list[str]] = []
    left = 0
    studies = 0
    for study in report.studies:
        decisions = [d for d in study.decisions if d.kind == VALUELESS]
        if not decisions:
            continue
        if study.outcome in PROVEN:
            lines += _valueless_rows(study, decisions)
        else:
            left += len(decisions)
            studies += 1
    if not lines and not left:
        return []
    text = [f"### {DECISION_HEADINGS[VALUELESS]}", ""]
    if lines:
        header = ["Study", "Table", "Format 1 file", "Rows", "Count", "Measurements"]
        text += [*_table([*header, "Written"], lines), ""]
    if left:
        text += [
            f"Studies that stay format 1 are listed in migration.json only: "
            f"{_count(left, 'row')} of {_count(studies, 'study', 'studies')}.",
            "",
        ]
    return text


def _registry(report: MigrationReport) -> list[str]:
    lines: list[str] = []
    if report.registry.deleted:
        lines += ["### Identifier registry", "", "Registry file deleted.", ""]
    doubles = report.registry.double_identifiers
    if doubles:
        rows = [
            [study, ", ".join(ids)]
            for study, ids in sorted(doubles.items(), key=lambda i: natural_key(i[0]))
        ]
        lines += [
            "### Studies with two PKDB identifiers",
            "",
            *_table(["Study", "Identifiers"], rows),
            "",
        ]
    if report.registry.missing_paths:
        rows = [
            [path] for path in sorted(report.registry.missing_paths, key=natural_key)
        ]
        lines += [
            "### Registry paths that do not exist",
            "",
            *_table(["Path"], rows),
            "",
        ]
    return lines


def _papers(report: MigrationReport) -> list[str]:
    if not report.papers:
        return []
    rows = [[p.source, p.target, "yes" if p.workbook else "no"] for p in report.papers]
    return [
        "### Folders moved to papers/",
        "",
        *_table(["Source", "Target", "Workbook"], rows),
        "",
    ]


def _status(report: MigrationReport) -> str:
    """Such as `Written: 3 studies.`, `Dry run.` or `Interrupted. Written: 1 study.`"""
    if report.dry_run:
        status = "Dry run."
    else:
        count = sum(study.written for study in report.studies)
        status = f"Written: {count} {'study' if count == 1 else 'studies'}."
    return f"Interrupted. {status}" if report.interrupted else status


def _vocabulary(report: MigrationReport) -> list[str]:
    """The vocabulary of the run, which decides how studies are converted."""
    used = report.vocabulary
    if used is None:
        return []
    return [f"Vocabulary: {used.version} (sha256 {used.hash}).", ""]


def markdown(report: MigrationReport) -> str:
    report = _sorted(report)
    grouped = _by_outcome(report)
    lines = [
        "# Study format 2 migration",
        "",
        _status(report),
        "",
        *_vocabulary(report),
        *(line for warning in report.warnings for line in (f"Warning: {warning}", "")),
        *_summary(report, grouped),
        *_classes(grouped),
        *_decisions(report, grouped),
    ]
    return "\n".join(lines).rstrip("\n") + "\n"


def check_report_path(path: Path) -> None:
    """Refuse a report path that the run could not write, before the run starts."""
    if path.suffix.lower() == ".md":
        raise ValueError(
            f"The report {path} cannot end in .md, because the Markdown report "
            "is written next to it; name a .json file."
        )
    folder = path.parent
    if not folder.is_dir():
        raise ValueError(f"The folder {folder} of the report does not exist.")
    if not os.access(folder, os.W_OK | os.X_OK):
        raise ValueError(f"The folder {folder} of the report is not writable.")


def write_report(report: MigrationReport, path: Path) -> Path:
    report = _sorted(report)
    text = (
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n"
    )
    atomic_text(path, text)
    md_path = path.with_suffix(".md")
    atomic_text(md_path, markdown(report))
    return md_path
