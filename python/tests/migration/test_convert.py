import json
from datetime import date

import openpyxl
import pytest
from migration_fixtures import SHEETS, STUDY, v1_full_example, v1_study, write_sheets

from pkdb.migration.convert import convert_study, is_v1_file
from pkdb.migration.model import NotConverted
from pkdb.migration.registry import Registry
from pkdb.references import NotFound, ReferenceResolver


class NoNetwork(ReferenceResolver):
    def resolve(self, *args, **kwargs):
        raise AssertionError("the converter must keep an existing reference.json")


class Unresolvable(ReferenceResolver):
    def resolve(self, *args, **kwargs):
        raise NotFound("No PubMed record found for 123")


class Resolved(ReferenceResolver):
    def resolve(self, seed, *, sid, name, existing=None, reset_overrides=False):
        return {"sid": sid, "name": name, "pmid": seed["pmid"], "title": "Resolved"}


def files(folder):
    return {path.name: path.read_bytes() for path in sorted(folder.iterdir())}


def convert(v1, tmp_path, *, resolver=None):
    return convert_study(
        v1,
        tmp_path / "v2" / "caffeine" / v1.name,
        registry=Registry(),
        approver=None,
        resolver=resolver or NoNetwork(offline=True),
    )


def rows(path):
    header, *lines = [line.split("\t") for line in path.read_text().splitlines()]
    return [dict(zip(header, line, strict=True)) for line in lines]


def rewrite_study(v1, **changes):
    study = json.loads((v1 / "study.json").read_text())
    (v1 / "study.json").write_text(json.dumps({**study, **changes}))


@pytest.mark.parametrize("workbook", [True, False])
def test_the_converted_folder_equals_the_format_2_twin(tmp_path, valid_study, workbook):
    v1 = v1_full_example(tmp_path / "v1", workbook=workbook)
    target = tmp_path / "v2" / "caffeine" / "Example"
    conversion = convert_study(
        v1, target, registry=Registry(), approver=None, resolver=NoNetwork(offline=True)
    )
    assert conversion.folder == target
    assert files(target) == files(valid_study)
    assert conversion.decisions == []


def test_a_registered_study_is_released_and_approved(tmp_path):
    v1 = v1_full_example(tmp_path / "v1")
    registry = Registry({"PKDB00042": ("caffeine/Example", date(2020, 1, 2))})
    target = tmp_path / "v2" / "caffeine" / "Example"
    convert_study(
        v1,
        target,
        registry=registry,
        approver="mkoenig",
        resolver=NoNetwork(offline=True),
    )
    metadata = json.loads((target / "study.json").read_text())
    assert metadata["release"] == {"pkdb_id": "PKDB00042", "date": "2020-01-02"}
    review = json.loads((target / "review.json").read_text())
    assert (review["status"], review["approved_by"]) == ("approved", "mkoenig")


def test_a_stale_hidden_tsv_beside_the_workbook_is_ignored_and_removed(tmp_path):
    v1 = v1_full_example(tmp_path / "v1", workbook=True)
    write_sheets(v1, "Example", {"Tab2": [["mean", "sd"], [99, 9]]}, workbook=False)
    conversion = convert(v1, tmp_path)
    assert not list(conversion.folder.glob(".*.tsv"))
    assert "2.5" in (conversion.folder / "outputs_Tab2.tsv").read_text()
    assert "99" not in (conversion.folder / "outputs_Tab2.tsv").read_text()
    assert conversion.decisions == []


def test_other_tables_and_json_files_are_removed_and_listed(tmp_path):
    v1 = v1_full_example(tmp_path / "v1")
    (v1 / "notes.csv").write_text("a,b\n")
    (v1 / "Example_Fig1.json").write_text("{}")
    (v1 / "Example_supplement.docx").write_bytes(b"doc")
    (v1 / "Example_Fig9.png").write_bytes(b"png")
    conversion = convert(v1, tmp_path)
    assert (conversion.folder / "Example_supplement.docx").read_bytes() == b"doc"
    assert (conversion.folder / "Example_Fig9.png").read_bytes() == b"png"
    assert not (conversion.folder / "notes.csv").exists()
    assert not (conversion.folder / "Example_Fig1.json").exists()
    assert [(d.kind, d.detail) for d in conversion.decisions] == [
        ("removed_file", "Example_Fig1.json"),
        ("removed_file", "notes.csv"),
    ]


def test_files_that_both_formats_ignore_are_neither_copied_nor_listed(tmp_path):
    v1 = v1_full_example(tmp_path / "v1")
    (v1 / ".DS_Store").write_bytes(b"finder")
    (v1 / "~$Example.xlsx").write_bytes(b"lock")
    (v1 / ".Example.xlsx.pkdb-base").write_bytes(b"state")
    conversion = convert(v1, tmp_path)
    assert not {".DS_Store", "~$Example.xlsx", ".Example.xlsx.pkdb-base"} & set(
        files(conversion.folder)
    )
    assert conversion.decisions == []


def test_hidden_folders_are_kept(tmp_path):
    v1 = v1_full_example(tmp_path / "v1")
    (v1 / ".misc").mkdir()
    (v1 / ".misc" / "data.xlsx").write_bytes(b"xlsx")
    conversion = convert(v1, tmp_path)
    assert (conversion.folder / ".misc" / "data.xlsx").read_bytes() == b"xlsx"
    assert conversion.decisions == []


@pytest.mark.parametrize(
    ("images", "source"), [((), ""), (("TabGroups",), "TabGroups")]
)
def test_groups_from_a_sheet_take_the_sheet_as_source_only_with_its_image(
    tmp_path, images, source
):
    group = {
        "source": "TabGroups",
        "name": "col==name",
        "count": "col==count",
        "characteristica": [{"measurement_type": "species", "choice": "Homo sapiens"}],
    }
    v1 = v1_study(
        tmp_path / "v1",
        {**STUDY, "groupset": {"groups": [group]}},
        {**SHEETS, "TabGroups": [["name", "count"], ["all", 2]]},
        ("TabA", "Tab2", "Fig1", *images),
    )
    conversion = convert(v1, tmp_path)
    subjects = rows(conversion.folder / "subjects.tsv")
    characteristica = rows(conversion.folder / "characteristica.tsv")
    assert [row["source"] for row in subjects if row["name"] == "all"] == [source]
    assert [row["source"] for row in characteristica if row["subjects"] == "all"] == [
        source
    ]
    assert conversion.decisions == []


def test_unreferenced_sheets_are_listed(tmp_path):
    v1 = v1_full_example(tmp_path / "v1")
    book = openpyxl.load_workbook(v1 / "Example.xlsx")
    book.create_sheet("Fig9").append(["time", "mean"])
    book.save(v1 / "Example.xlsx")
    write_sheets(v1, "Example", {"Tab8": [["mean"], [1]]}, workbook=False)
    conversion = convert(v1, tmp_path)
    assert [(d.kind, d.detail) for d in conversion.decisions] == [
        ("unreferenced_sheet", "Fig9"),
        ("unreferenced_sheet", "Tab8"),
    ]


def test_v1_files_are_tables_workbooks_and_json_files_but_reference_json():
    dropped = ["study.json", "Example.xlsx", "Example.xls", ".Example_Tab2.tsv"]
    dropped += ["data.tsv", "notes.CSV", "Example_Fig1.json"]
    kept = ["reference.json", "Example.pdf", "Example_Tab2.png", "Example.docx"]
    assert all(is_v1_file(name, "Example") for name in dropped)
    assert not any(is_v1_file(name, "Example") for name in kept)


def test_a_study_without_subjects_is_not_converted(tmp_path):
    v1 = v1_full_example(tmp_path / "v1")
    rewrite_study(
        v1,
        groupset={},
        individualset={},
        outputset={},
        dataset={},
        interventionset={},
    )
    with pytest.raises(NotConverted) as error:
        convert(v1, tmp_path)
    assert error.value.code == "no_subjects"
    assert not (tmp_path / "v2" / "caffeine" / "Example").exists()


def test_an_unreadable_study_is_not_converted(tmp_path):
    v1 = v1_full_example(tmp_path / "v1")
    rewrite_study(v1, name="Other")
    with pytest.raises(NotConverted) as error:
        convert(v1, tmp_path)
    assert (error.value.code, error.value.message) == (
        "unreadable",
        "Study name must match its folder",
    )


def test_metadata_that_format_2_cannot_hold_is_not_converted(tmp_path):
    v1 = v1_full_example(tmp_path / "v1")
    rewrite_study(v1, creator="Jane Doe")
    with pytest.raises(NotConverted) as error:
        convert(v1, tmp_path)
    assert error.value.code == "metadata"
    assert "creator" in error.value.message


def test_a_numeric_sid_and_pubmed_id_become_text(tmp_path):
    v1 = v1_full_example(tmp_path / "v1")
    reference = {"sid": 123, "name": "Example", "pmid": 123, "title": "Example study"}
    (v1 / "reference.json").write_text(json.dumps(reference))
    conversion = convert(v1, tmp_path)
    reference = json.loads((conversion.folder / "reference.json").read_text())
    assert (reference["sid"], reference["pmid"]) == ("123", "123")


def test_a_reference_json_that_format_2_cannot_hold_is_not_converted(tmp_path):
    v1 = v1_full_example(tmp_path / "v1")
    rewrite_study(v1, reference="Example")
    reference = {"sid": "Example", "name": "Example", "pmid": "Example"}
    (v1 / "reference.json").write_text(json.dumps(reference))
    with pytest.raises(NotConverted) as error:
        convert(v1, tmp_path)
    assert error.value.code == "format", error.value.message
    assert error.value.message.startswith("reference.json: ")


def test_a_reference_json_that_misses_the_pubmed_id_is_resolved(tmp_path):
    v1 = v1_full_example(tmp_path / "v1")
    (v1 / "reference.json").write_text(json.dumps({"sid": "123", "name": "Example"}))
    conversion = convert(v1, tmp_path, resolver=Resolved(offline=True))
    reference = json.loads((conversion.folder / "reference.json").read_text())
    assert (reference["pmid"], reference["title"]) == ("123", "Resolved")
    assert [(d.kind, d.detail) for d in conversion.decisions] == [
        ("reference_replaced", "Replaced reference.json (SID 123) with PubMed 123")
    ]


def test_a_reference_that_cannot_be_resolved_is_not_converted(tmp_path):
    v1 = v1_full_example(tmp_path / "v1")
    (v1 / "reference.json").write_text(json.dumps({"sid": "123", "name": "Example"}))
    with pytest.raises(NotConverted) as error:
        convert(v1, tmp_path, resolver=Unresolvable(offline=True))
    assert error.value.code == "reference"
    assert "No PubMed record found for 123" in error.value.message


@pytest.mark.parametrize(
    ("name", "content", "error"),
    [("Example", "over", FileExistsError), ("Other", None, ValueError)],
)
def test_the_target_is_an_empty_folder_named_like_the_study(
    tmp_path, name, content, error
):
    v1 = v1_full_example(tmp_path / "v1")
    target = tmp_path / "v2" / "caffeine" / name
    if content is not None:
        target.mkdir(parents=True)
        (target / "left.txt").write_text(content)
    with pytest.raises(error):
        convert_study(
            v1,
            target,
            registry=Registry(),
            approver=None,
            resolver=NoNetwork(offline=True),
        )
    assert not (tmp_path / "v2" / "caffeine" / "Other").exists()
