import json

from pkdb.migration.model import (
    Change,
    Decision,
    Difference,
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
    assert "| caffeine/A1999 | D1: time 0, interval 12, doses 3 |" in text
    assert "### Studies with two PKDB identifiers" in text
    assert "| caffeine/A1999 | PKDB00001, PKDB00002 |" in text
    assert "### Registry paths that do not exist" in text
    assert "### Sheet names outside the source pattern" in text
    assert "| studies/caffeine/F2004 | papers/caffeine/F2004 | yes |" in text
    assert "caffeine/B2000\n" in text
    assert "—" not in text


def test_cells_escape_pipes_and_line_breaks():
    report = MigrationReport(
        dry_run=False,
        studies=[StudyResult(study="x/Y", outcome="not_converted", reason="a|b\nc")],
    )
    assert "| x/Y | a\\|b c |" in markdown(report)
    assert "Written." in markdown(report)


def test_every_decision_kind_appears_under_a_heading():
    kinds = [
        "output_label",
        "access_private",
        "label_renamed",
        "reference_replaced",
        "reference_resolved",
        "future_kind",
    ]
    report = MigrationReport(
        dry_run=True,
        studies=[
            StudyResult(
                study="x/Y",
                outcome="intended",
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
        "future_kind",
    ]:
        assert f"### {heading}\n" in text
    assert "| x/Y | detail future_kind |" in text
