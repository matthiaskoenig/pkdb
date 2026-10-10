import json

import pytest

from pkdb.migration.model import (
    Change,
    Decision,
    Difference,
    DroppedRow,
    MigrationReport,
    PaperMove,
    RegistryFindings,
    StudyResult,
)
from pkdb.migration.report import markdown, write_report

REPORT = MigrationReport(
    dry_run=True,
    studies=[
        StudyResult(study="caffeine/B2000", outcome="identical", written=False),
        StudyResult(
            study="caffeine/A1999",
            outcome="mismatch",
            differences=[Difference(path="measurements[x].sd", a="0.5", b="0.6")],
            issues=["measurement_unit"],
            decisions=[
                Decision(kind="schedule", detail="D1: time 0, interval 12, doses 3")
            ],
        ),
        StudyResult(
            study="caffeine/C2001",
            outcome="not_converted",
            reason="sheet_name: Sheet Fig1.2 is not a source name",
        ),
        StudyResult(
            study="caffeine/C2001a",
            outcome="not_converted",
            reason="registry_sid: study.json has the identifier PKDB00001",
        ),
        StudyResult(
            study="caffeine/D2002",
            outcome="intended",
            changes=[Change(kind="group_count_1", count=1, examples=["all"])],
        ),
    ],
    skipped=["caffeine/E2003"],
    papers=[
        PaperMove(
            source="studies/caffeine/F2004",
            target="papers/caffeine/F2004",
            files=["F2004.pdf", "F2004.xlsx"],
            workbook=True,
        )
    ],
    registry=RegistryFindings(
        double_identifiers={"caffeine/A1999": ["PKDB00001", "PKDB00002"]},
        missing_paths=["caffeine/Gone1990"],
    ),
)


def test_the_json_report_is_sorted_and_complete(tmp_path):
    md = write_report(REPORT, tmp_path / "migration.json")
    data = json.loads((tmp_path / "migration.json").read_text())
    assert [s["study"] for s in data["studies"]] == [
        "caffeine/A1999",
        "caffeine/B2000",
        "caffeine/C2001",
        "caffeine/C2001a",
        "caffeine/D2002",
    ]
    assert md == tmp_path / "migration.md"
    assert md.read_text() == markdown(REPORT)


def test_the_markdown_summary_and_sections():
    text = markdown(REPORT)
    assert text.startswith("# Study format 2 migration\n\nDry run.\n")
    assert "| mismatch | 1 |" in text
    assert "| Skipped (format 2) | 1 |" in text
    assert "| caffeine/A1999 | measurements[x].sd | 0.5 | 0.6 |" in text
    assert "| caffeine/A1999 | measurement_unit |" in text
    assert "| caffeine/C2001 | sheet_name: Sheet Fig1.2 is not a source name |" in text
    assert "| caffeine/D2002 | group_count_1 x 1 |" in text
    assert "### Converted dosing schedules" in text
    assert "| Study | Detail | Written |" in text
    assert "| caffeine/A1999 | D1: time 0, interval 12, doses 3 | no |" in text
    assert "### Studies with two PKDB identifiers" in text
    assert "| caffeine/A1999 | PKDB00001, PKDB00002 |" in text
    assert "### Registry paths that do not exist" in text
    assert "### Sheet names outside the source pattern" in text
    assert (
        "### Identifiers that differ from the registry\n\n| Study | Reason |\n"
        "| --- | --- |\n"
        "| caffeine/C2001a | registry_sid: study.json has the identifier PKDB00001 |\n"
    ) in text
    assert "| studies/caffeine/F2004 | papers/caffeine/F2004 | yes |" in text
    assert "caffeine/B2000\n" in text
    assert "\u2014" not in text


def test_cells_escape_pipes_and_line_breaks():
    report = MigrationReport(
        dry_run=False,
        studies=[StudyResult(study="x/Y", outcome="not_converted", reason="a|b\nc")],
    )
    assert "| x/Y | a\\|b c |" in markdown(report)


@pytest.mark.parametrize(
    ("dry_run", "interrupted", "written", "status"),
    [
        (False, False, 2, "Written: 2 studies."),
        (False, False, 1, "Written: 1 study."),
        (False, True, 0, "Interrupted. Written: 0 studies."),
        (True, False, 0, "Dry run."),
    ],
)
def test_the_header_says_how_many_studies_were_written(
    dry_run, interrupted, written, status
):
    studies = [
        StudyResult(study=f"x/S{n}", outcome="identical", written=n < written)
        for n in range(3)
    ]
    report = MigrationReport(dry_run=dry_run, interrupted=interrupted, studies=studies)
    assert markdown(report).startswith(f"# Study format 2 migration\n\n{status}\n")


def test_a_deleted_registry_is_named():
    report = MigrationReport(dry_run=False, registry=RegistryFindings(deleted=True))
    assert "### Identifier registry\n\nRegistry file deleted.\n" in markdown(report)
    assert "Registry file deleted." not in markdown(REPORT)


def test_an_interrupted_run_says_so_first():
    report = MigrationReport(dry_run=True, interrupted=True, warnings=["Look."])
    assert markdown(report).startswith(
        "# Study format 2 migration\n\nInterrupted. Dry run.\n\nWarning: Look.\n"
    )


def test_every_decision_kind_appears_under_a_heading():
    kinds = [
        "output_label",
        "access_private",
        "label_renamed",
        "reference_replaced",
        "reference_resolved",
        "creator_fallback",
        "valueless_row",
        "future_kind",
    ]
    report = MigrationReport(
        dry_run=True,
        studies=[
            StudyResult(
                study="x/Y",
                outcome="intended",
                written=True,
                decisions=[Decision(kind=k, detail=f"detail {k}") for k in kinds],
            )
        ],
    )
    text = markdown(report)
    for heading in [
        "Dropped output labels",
        "Public studies without a release (now private)",
        "Renamed timecourse labels",
        "Replaced reference snapshots",
        "Resolved missing references",
        "Dropped rows without any value",
        "future_kind",
    ]:
        assert f"### {heading}\n" in text
    assert "| x/Y | detail future_kind | yes |" in text
    assert "### Studies without a creator\n" in text


def dropped(table, file, measurement, *, sheet=None, row=None, path=None):
    place = DroppedRow(
        table=table,
        file=file,
        sheet=sheet,
        row=row,
        path=path,
        measurement=measurement,
    )
    detail = f"{table}: {place.place()}, {measurement}"
    return Decision(kind="valueless_row", detail=detail, dropped=place)


DROPPED = MigrationReport(
    dry_run=True,
    studies=[
        StudyResult(
            study="x/A",
            outcome="intended",
            decisions=[
                *(
                    dropped("outputs_Tab1.tsv", "A.xlsx", m, sheet="Tab1", row=row)
                    for row, m in ((8, "cmax"), (3, "tmax"), (4, "tmax"), (5, "cmax"))
                ),
                dropped("outputs_Tab2.tsv", ".A_Tab2.tsv", "auc_end", row=2),
                dropped(
                    "characteristica.tsv", "study.json", "age", path="groupset.groups.0"
                ),
                Decision(kind="schedule", detail="D1: time 0, interval 12, doses 3"),
            ],
        ),
        StudyResult(
            study="x/B",
            outcome="mismatch",
            decisions=[
                dropped("outputs_Tab1.tsv", "B.xlsx", "tmax", sheet="Tab1", row=3),
                dropped("outputs_Tab1.tsv", "B.xlsx", "tmax", sheet="Tab1", row=4),
            ],
        ),
    ],
)


def test_dropped_rows_are_listed_per_file_for_studies_that_are_written():
    text = markdown(DROPPED)
    section = text.split("### Dropped rows without any value\n\n")[1].split("###")[0]
    assert section.splitlines() == [
        "| Study | Table | Format 1 file | Rows | Count | Measurements | Written |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        "| x/A | outputs_Tab1.tsv | A.xlsx Tab1 | 3-5, 8 | 4 | cmax, tmax | no |",
        "| x/A | outputs_Tab2.tsv | .A_Tab2.tsv | 2 | 1 | auc_end | no |",
        "| x/A | characteristica.tsv | study.json | groupset.groups.0 | 1 | age | no |",
        "",
        "Studies that stay format 1 are listed in migration.json only: "
        "2 rows of 1 study.",
    ]


def test_the_json_report_lists_every_dropped_row(tmp_path):
    write_report(DROPPED, tmp_path / "migration.json")
    data = json.loads((tmp_path / "migration.json").read_text())
    decisions = [d for study in data["studies"] for d in study["decisions"]]
    assert [d["kind"] for d in decisions].count("valueless_row") == 8
    assert decisions[0]["dropped"] == {
        "table": "outputs_Tab1.tsv",
        "file": "A.xlsx",
        "sheet": "Tab1",
        "row": 8,
        "path": None,
        "label": None,
        "subject": None,
        "measurement": "cmax",
        "substance": None,
        "tissue": None,
        "comment": None,
    }
    # Other decisions have no place.
    assert "dropped" not in decisions[6]
    assert MigrationReport.model_validate(data) == DROPPED
