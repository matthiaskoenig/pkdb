import json
from datetime import date

import pytest
from lifecycle_fixtures import released_study

from pkdb.cli import main
from pkdb.lifecycle.release import ReleaseConflict, ReleaseRefused, check, release
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.jsonio import dump_json
from pkdb.studyformat.metadata import read_metadata
from pkdb.studyformat.review_edit import Author, add_item
from pkdb.studyformat.validation import validate_folder

APPROVED = {
    "status": "approved",
    "reviewers": ["bo"],
    "approved_by": "bo",
    "approved": "2026-10-01T00:00:00Z",
}


def numbers(done):
    """The location and the PKDB identifier of each released study."""
    return [(item.location, item.pkdb_id) for item in done]


@pytest.fixture
def approved_studies(tmp_path, valid_files):
    def make(*locations, highest=None, base=tmp_path):
        folders = []
        for place in locations:
            folder = base / "studies" / place
            folder.mkdir(parents=True)
            for name, content in valid_files.items():
                path = folder / name.replace("Example", folder.name, 1)
                if isinstance(content, bytes):
                    path.write_bytes(content)
                else:
                    path.write_text(content, encoding="utf-8", newline="")
            assert format_folder(folder).ok
            (folder / "review.json").write_text(dump_json(APPROVED), encoding="utf-8")
            folders.append(folder)
        if highest is not None:
            released_study(base, "other/Old", pkdb_id=highest)
        return base, *folders

    return make


def test_studies_are_numbered_in_argument_order(approved_studies, sf_vocabulary):
    root, first, second = approved_studies(
        "caffeine/B", "caffeine/A", highest="PKDB00009"
    )
    assert numbers(
        release(root, [first, second], sf_vocabulary, on=date(2026, 10, 10))
    ) == [
        ("caffeine/B", "PKDB00010"),
        ("caffeine/A", "PKDB00011"),
    ]
    released = read_metadata(second).metadata.release
    assert released is not None
    assert (released.pkdb_id, released.date) == ("PKDB00011", date(2026, 10, 10))


def test_the_first_study_gets_the_first_identifier(approved_studies, sf_vocabulary):
    root, first = approved_studies("caffeine/A")
    assert numbers(release(root, [first], sf_vocabulary, on=date(2026, 10, 10))) == [
        ("caffeine/A", "PKDB00001")
    ]


def test_one_refused_study_stops_the_whole_release(approved_studies, sf_vocabulary):
    root, first, second = approved_studies("caffeine/A", "caffeine/B")
    (second / "review.json").write_text(
        dump_json({"status": "in_review"}), encoding="utf-8"
    )
    with pytest.raises(ReleaseRefused) as refused:
        release(root, [first, second], sf_vocabulary, on=date(2026, 10, 10))
    assert [(r.location, r.reasons) for r in refused.value.refusals] == [
        ("caffeine/B", ["The review status is in_review; a study must be approved"])
    ]
    assert read_metadata(first).metadata.release is None


def test_an_open_item_a_validation_error_and_a_release_refuse(
    approved_studies, sf_vocabulary
):
    root, item, broken, again = approved_studies("c/Item", "c/Broken", "c/Again")
    (item / "review.json").write_text(dump_json({"status": "draft"}), encoding="utf-8")
    add_item(item, Author("bo"), kind="question", text="Why?")
    review = json.loads((item / "review.json").read_text(encoding="utf-8"))
    review |= APPROVED
    (item / "review.json").write_text(dump_json(review), encoding="utf-8")
    assert format_folder(item).ok
    (broken / "reference.json").unlink()
    release(root, [again], sf_vocabulary, on=date(2026, 10, 10))
    assert check(item, sf_vocabulary) == ["1 review item is open"]
    assert check(broken, sf_vocabulary) == ["Validation has 1 error"]
    assert check(again, sf_vocabulary) == ["The study is already released as PKDB00001"]


def test_a_changed_study_json_is_a_conflict_that_keeps_earlier_numbers(
    approved_studies, sf_vocabulary, monkeypatch
):
    from pkdb.lifecycle import release as module
    from pkdb.studyformat.revision import RevisionConflict

    root, first, second = approved_studies("c/A", "c/B")
    real = module.patch_metadata

    def patch(folder, patch, revision):
        if folder == second:
            raise RevisionConflict("study.json", "a", "b", None)
        return real(folder, patch, revision)

    monkeypatch.setattr(module, "patch_metadata", patch)
    with pytest.raises(ReleaseConflict) as conflict:
        release(root, [first, second], sf_vocabulary, on=date(2026, 10, 10))
    assert "c/B" in str(conflict.value)
    assert "c/A: PKDB00001" in str(conflict.value)
    kept = read_metadata(first).metadata.release
    assert kept is not None and kept.pkdb_id == "PKDB00001"


def test_the_command_releases_and_prints_the_number(
    approved_studies, sf_vocabulary, capsys, monkeypatch
):
    root, first = approved_studies("caffeine/A")
    monkeypatch.setattr("pkdb.tables_cli._vocabulary", lambda args: sf_vocabulary)
    argv = ["--no-update", "release", str(first), "--date", "2026-10-10"]
    assert main([*argv, "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "released": [
            {
                "location": "caffeine/A",
                "pkdb_id": "PKDB00001",
                "date": "2026-10-10",
                "access": "private",
            }
        ]
    }


def test_access_is_written_in_the_release_patch(
    approved_studies, sf_vocabulary, monkeypatch
):
    from pkdb.lifecycle import release as module

    root, first, second = approved_studies("caffeine/A", "caffeine/B")
    real = module.patch_metadata
    patches = []

    def patch(folder, patch, revision):
        patches.append((folder, patch))
        return real(folder, patch, revision)

    monkeypatch.setattr(module, "patch_metadata", patch)
    done = release(
        root, [first, second], sf_vocabulary, on=date(2026, 10, 10), access="public"
    )
    assert [(item.location, item.access) for item in done] == [
        ("caffeine/A", "public"),
        ("caffeine/B", "public"),
    ]
    released = {"date": "2026-10-10"}
    assert patches == [
        (first, {"release": {"pkdb_id": "PKDB00001", **released}, "access": "public"}),
        (second, {"release": {"pkdb_id": "PKDB00002", **released}, "access": "public"}),
    ]
    assert read_metadata(first).metadata.access == "public"
    assert not [
        issue
        for issue in validate_folder(first, sf_vocabulary).issues
        if issue.severity == "error"
    ]


def test_the_command_publishes_with_access_public(
    approved_studies, sf_vocabulary, capsys, monkeypatch
):
    root, first = approved_studies("caffeine/A")
    monkeypatch.setattr("pkdb.tables_cli._vocabulary", lambda args: sf_vocabulary)
    argv = ["--no-update", "release", str(first), "--date", "2026-10-10"]
    assert main([*argv, "--access", "public", "--format", "human"]) == 0
    assert capsys.readouterr().out == "caffeine/A: PKDB00001\n"
    metadata = read_metadata(first).metadata
    assert metadata.access == "public" and metadata.release is not None


def test_the_command_hints_at_a_released_study_that_stays_private(
    approved_studies, sf_vocabulary, capsys, monkeypatch
):
    root, first = approved_studies("caffeine/A")
    monkeypatch.setattr("pkdb.tables_cli._vocabulary", lambda args: sf_vocabulary)
    argv = ["--no-update", "release", str(first), "--date", "2026-10-10"]
    assert main([*argv, "--format", "human"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "caffeine/A: PKDB00001",
        "caffeine/A stays private. Set its access to public with pkdb study patch "
        "to publish it; pkdb release --access public does both at once.",
    ]
    assert read_metadata(first).metadata.access == "private"


def test_the_command_writes_nothing_when_a_study_is_refused(
    approved_studies, sf_vocabulary, capsys, monkeypatch
):
    root, first, second = approved_studies("caffeine/A", "caffeine/B")
    (second / "review.json").write_text(
        dump_json({"status": "draft"}), encoding="utf-8"
    )
    monkeypatch.setattr("pkdb.tables_cli._vocabulary", lambda args: sf_vocabulary)
    code = main(["--no-update", "release", str(first), str(second), "--format", "json"])
    assert code == 1
    assert json.loads(capsys.readouterr().out)["refused"][0]["location"] == "caffeine/B"
    assert read_metadata(first).metadata.release is None


def test_the_command_rejects_wrong_arguments(
    approved_studies, sf_vocabulary, tmp_path, capsys, monkeypatch
):
    root, first = approved_studies("caffeine/A")
    monkeypatch.setattr("pkdb.tables_cli._vocabulary", lambda args: sf_vocabulary)
    base = ["--no-update", "release"]
    assert main([*base, str(first), str(first)]) == 2
    assert main([*base, str(root / "studies")]) == 2
    with pytest.raises(SystemExit) as bad:
        main([*base, str(first), "--date", "10.10.2026"])
    assert bad.value.code == 2
    link = first.parent / "Link"
    link.symlink_to(first, target_is_directory=True)
    assert main([*base, str(first), str(link)]) == 2
    assert main([*base, str(first), str(first / "..") + "/A"]) == 2
    _, second = approved_studies("caffeine/A", base=tmp_path / "other")
    assert main([*base, str(first), str(second)]) == 2


def test_the_command_takes_substance_and_name_of_the_checkout(
    approved_studies, sf_vocabulary, capsys, monkeypatch
):
    root, first, second = approved_studies("caffeine/A", "caffeine/B")
    monkeypatch.setattr("pkdb.tables_cli._vocabulary", lambda args: sf_vocabulary)
    base = ["--no-update", "release", "--format", "json"]
    monkeypatch.chdir(root / "studies" / "caffeine")
    # A folder path and SUBSTANCE/NAME of the checkout that holds the current folder.
    assert main([*base, "A", "caffeine/B"]) == 0
    released = json.loads(capsys.readouterr().out)["released"]
    assert [item["location"] for item in released] == ["caffeine/A", "caffeine/B"]
    _, third = approved_studies("caffeine/C")
    monkeypatch.chdir(root.parent)
    assert main([*base, "caffeine/C", "--root", str(root)]) == 0
    assert json.loads(capsys.readouterr().out)["released"][0]["pkdb_id"] == "PKDB00003"


def test_the_command_refuses_unknown_and_ambiguous_locations(
    approved_studies, sf_vocabulary, tmp_path, capsys, monkeypatch
):
    root, first = approved_studies("caffeine/A")
    monkeypatch.setattr("pkdb.tables_cli._vocabulary", lambda args: sf_vocabulary)
    base = ["--no-update", "release", "--root", str(root)]
    monkeypatch.chdir(tmp_path)
    assert main([*base, "caffeine/Missing"]) == 2
    assert capsys.readouterr().err == (
        "Neither caffeine/Missing nor studies/caffeine/Missing of the checkout is a "
        "study format 2 folder\n"
    )
    # caffeine/A of the current folder is another study than that of the checkout.
    other, _ = approved_studies("caffeine/A", base=tmp_path / "other")
    monkeypatch.chdir(other / "studies")
    assert main([*base, "caffeine/A"]) == 2
    assert capsys.readouterr().err.startswith(
        "caffeine/A is the folder of another study than studies/caffeine/A of the "
        "checkout; give the path of the folder"
    )
    assert read_metadata(first).metadata.release is None


def test_an_unreadable_study_json_elsewhere_stops_before_any_write(
    approved_studies, sf_vocabulary
):
    root, first = approved_studies("caffeine/A")
    released_study(root, "other/Broken")
    (root / "studies" / "other" / "Broken" / "study.json").write_text(
        "{", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="Broken"):
        release(root, [first], sf_vocabulary, on=date(2026, 10, 10))
    assert read_metadata(first).metadata.release is None


@pytest.mark.parametrize("output", ["human", "json"])
def test_the_command_reports_an_unknown_largest_identifier(
    approved_studies, sf_vocabulary, capsys, monkeypatch, output
):
    root, first = approved_studies("caffeine/A")
    (root / "studies" / "study_identifiers.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr("pkdb.tables_cli._vocabulary", lambda args: sf_vocabulary)
    argv = ["--no-update", "release", str(first), "--format", output]
    assert main(argv) == 1
    message = (
        "Cannot find the largest identifier: studies/study_identifiers.json: must "
        "be a JSON object; no study was released"
    )
    captured = capsys.readouterr()
    if output == "json":
        assert json.loads(captured.out) == {"error": message}
    else:
        assert captured.err == f"{message}\n"
    assert read_metadata(first).metadata.release is None


def test_the_registry_file_number_is_counted(approved_studies, sf_vocabulary):
    root, first = approved_studies("caffeine/A")
    (root / "studies" / "study_identifiers.json").write_text(
        dump_json({"PKDB00020": ["old/Study", "2020-01-01"]}), encoding="utf-8"
    )
    assert numbers(release(root, [first], sf_vocabulary, on=date(2026, 10, 10))) == [
        ("caffeine/A", "PKDB00021")
    ]


def test_an_approved_study_with_only_warnings_is_released(
    approved_studies, sf_vocabulary, monkeypatch
):
    from pkdb.studyformat import review_edit
    from pkdb.studyformat.issues import make_issue

    root, first = approved_studies("caffeine/A")
    real = review_edit.validate_folder

    def with_warning(folder, vocabulary):
        report = real(folder, vocabulary)
        warning = make_issue("unused_subject", "Subject all is not used")
        assert warning.severity == "warning"
        report.issues.append(warning)
        return report

    monkeypatch.setattr(review_edit, "validate_folder", with_warning)
    assert check(first, sf_vocabulary) == []
    assert numbers(release(root, [first], sf_vocabulary, on=date(2026, 10, 10))) == [
        ("caffeine/A", "PKDB00001")
    ]


def test_the_command_exits_with_1_on_a_conflict(
    approved_studies, sf_vocabulary, capsys, monkeypatch
):
    from pkdb.lifecycle import release as module
    from pkdb.studyformat.revision import RevisionConflict

    root, first = approved_studies("caffeine/A")
    monkeypatch.setattr("pkdb.tables_cli._vocabulary", lambda args: sf_vocabulary)

    def conflict(folder, patch, revision):
        raise RevisionConflict("study.json", "a", "b", None)

    monkeypatch.setattr(module, "patch_metadata", conflict)
    assert main(["--no-update", "release", str(first), "--format", "json"]) == 1
    assert "caffeine/A" in json.loads(capsys.readouterr().out)["error"]


def test_a_later_write_error_names_the_studies_already_written(
    approved_studies, sf_vocabulary, monkeypatch
):
    from pkdb.lifecycle import release as module

    root, first, second = approved_studies("c/A", "c/B")
    real = module.patch_metadata

    def patch(folder, patch, revision):
        if folder == second:
            raise OSError("disk full")
        return real(folder, patch, revision)

    monkeypatch.setattr(module, "patch_metadata", patch)
    with pytest.raises(ReleaseConflict, match="disk full.*c/A: PKDB00001"):
        release(root, [first, second], sf_vocabulary, on=date(2026, 10, 10))


def test_release_and_approval_refuse_the_same_study(approved_studies, sf_vocabulary):
    from pkdb.studyformat.review_edit import ApprovalRefused, set_status

    root, broken = approved_studies("caffeine/A")
    (broken / "reference.json").unlink()
    (broken / "review.json").write_text(
        dump_json({"status": "in_review"}), encoding="utf-8"
    )
    with pytest.raises(ApprovalRefused) as refused:
        set_status(broken, Author("bo"), "approved", vocabulary=sf_vocabulary)
    assert check(broken, sf_vocabulary) == [
        "The review status is in_review; a study must be approved",
        str(refused.value),
    ]
