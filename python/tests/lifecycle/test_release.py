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

APPROVED = {
    "status": "approved",
    "reviewers": ["bo"],
    "approved_by": "bo",
    "approved": "2026-10-01T00:00:00Z",
}


@pytest.fixture
def approved_studies(tmp_path, valid_files):
    def make(*locations, highest=None):
        folders = []
        for place in locations:
            folder = tmp_path / "studies" / place
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
            released_study(tmp_path, "other/Old", pkdb_id=highest)
        return tmp_path, *folders

    return make


def test_studies_are_numbered_in_argument_order(approved_studies, sf_vocabulary):
    root, first, second = approved_studies(
        "caffeine/B", "caffeine/A", highest="PKDB00009"
    )
    assert release(root, [first, second], sf_vocabulary, on=date(2026, 10, 10)) == [
        ("caffeine/B", "PKDB00010"),
        ("caffeine/A", "PKDB00011"),
    ]
    released = read_metadata(second).metadata.release
    assert released is not None
    assert (released.pkdb_id, released.date) == ("PKDB00011", date(2026, 10, 10))


def test_the_first_study_gets_the_first_identifier(approved_studies, sf_vocabulary):
    root, first = approved_studies("caffeine/A")
    assert release(root, [first], sf_vocabulary, on=date(2026, 10, 10)) == [
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
            {"location": "caffeine/A", "pkdb_id": "PKDB00001", "date": "2026-10-10"}
        ]
    }


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
    other = tmp_path / "other"
    (other / "studies" / "caffeine").mkdir(parents=True)
    (other / "studies" / "caffeine" / "A").symlink_to(first, target_is_directory=True)
    # A symbolic link resolves into the first checkout, so use a copy instead.
    (other / "studies" / "caffeine" / "A").unlink()
    import shutil

    shutil.copytree(first, other / "studies" / "caffeine" / "A")
    assert main([*base, str(first), str(other / "studies" / "caffeine" / "A")]) == 2
