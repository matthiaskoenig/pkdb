import json
import socket

import httpx2
import pytest
from check_fixtures import git, study_checkout

import pkdb.checks
import pkdb.client
from pkdb.cache import bundled_vocabulary
from pkdb.checks import CheckError, CheckReport, Problem, check, select, vocabulary_for
from pkdb.domain.vocabulary import Vocabulary
from pkdb.schemas.validation import ValidationReport
from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.jsonio import dump_json


@pytest.fixture
def checkout(tmp_path, valid_files):
    """Build a git checkout with one commit of format 2 and format 1 studies."""

    def build(*locations, format_1=()):
        return study_checkout(
            tmp_path / "data", valid_files, *locations, format_1=format_1
        )

    return build


def patch_study(folder, **fields):
    """Add fields to the study.json of a format 2 study and format it again."""
    path = folder / "study.json"
    metadata = json.loads(path.read_text(encoding="utf-8")) | fields
    path.write_text(dump_json(metadata), encoding="utf-8")
    assert format_folder(folder).ok


def add_unused_intervention(folder):
    """A second intervention that no row uses: a validation warning."""
    path = folder / "interventions.tsv"
    header, row = path.read_text(encoding="utf-8").splitlines(keepends=True)
    path.write_text(header + row + row.replace("\tD1\t", "\tD2\t"), encoding="utf-8")
    assert format_folder(folder).ok


def codes(report):
    return {(problem.study, problem.code) for problem in report.problems}


def files_below(root):
    """Every file of the checkout outside .git with its bytes."""
    return {
        path: path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


def test_staged_files_select_their_studies(checkout):
    root, studies = checkout("caffeine/A", "caffeine/B", "codeine/C")
    (studies["caffeine/A"] / "subjects.tsv").write_text(
        (studies["caffeine/A"] / "subjects.tsv").read_text() + "", encoding="utf-8"
    )
    (studies["codeine/C"] / "notes.txt").write_text("x", encoding="utf-8")
    git(root, "add", "studies/codeine/C/notes.txt")
    folders, deleted = select(root, staged=True)
    assert [f.name for f in folders] == ["C"] and deleted == []


def test_changes_since_a_base_select_their_studies(checkout):
    root, studies = checkout("caffeine/A", "caffeine/B")
    git(root, "tag", "base")
    (studies["caffeine/B"] / "notes.txt").write_text("x", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-m", "change B")
    folders, _ = select(root, changed="base")
    assert [f.name for f in folders] == ["B"]


def test_a_moved_and_a_deleted_study_are_handled(checkout):
    root, studies = checkout("caffeine/A", "caffeine/B")
    git(root, "mv", "studies/caffeine/A", "studies/caffeine/A2")
    git(root, "rm", "-r", "-q", "studies/caffeine/B")
    folders, deleted = select(root, staged=True)
    assert [f.name for f in folders] == ["A2"]
    assert sorted(deleted) == ["caffeine/A", "caffeine/B"]


def test_a_deleted_study_with_files_left_behind_is_deleted(checkout):
    root, studies = checkout("caffeine/A", "caffeine/B")
    git(root, "rm", "-r", "-q", "studies/caffeine/B")
    # git rm keeps untracked files, such as the workbook that git ignores.
    (studies["caffeine/B"]).mkdir(exist_ok=True)
    (studies["caffeine/B"] / "B.xlsx").write_bytes(b"x")
    assert select(root, staged=True) == ([], ["caffeine/B"])


def test_paths_with_spaces_and_umlauts_are_selected(checkout):
    root, studies = checkout("caffeine/Bayer Study_1", "caffeine/Jönsson2015")
    for folder in studies.values():
        (folder / "notes.txt").write_text("x", encoding="utf-8")
    git(root, "add", "-A")
    folders, _ = select(root, staged=True)
    assert sorted(f.name for f in folders) == ["Bayer Study_1", "Jönsson2015"]


def test_files_outside_study_folders_select_nothing(checkout):
    root, _ = checkout("caffeine/A")
    (root / "README.md").write_text("x", encoding="utf-8")
    (root / "studies" / "study_identifiers.json").write_text("{}", encoding="utf-8")
    (root / "studies" / "caffeine" / "notes.txt").write_text("x", encoding="utf-8")
    hidden = root / "studies" / "caffeine" / ".A.new" / "A"
    hidden.mkdir(parents=True)
    (hidden / "study.json").write_text("{}", encoding="utf-8")
    git(root, "add", "-A")
    assert select(root, staged=True) == ([], [])


def test_paths_select_the_studies_below_them(checkout):
    root, studies = checkout("caffeine/A", "caffeine/B", "codeine/C")
    caffeine = root / "studies" / "caffeine"
    folders, deleted = select(root, paths=[caffeine, caffeine / "A"])
    assert folders == [studies["caffeine/A"], studies["caffeine/B"]]
    assert deleted == []
    with pytest.raises(CheckError, match="outside"):
        select(root, paths=[root])
    with pytest.raises(CheckError, match="directory"):
        select(root, paths=[caffeine / "Missing"])


def test_without_a_selection_every_study_is_selected(checkout):
    root, studies = checkout("caffeine/A", "codeine/C", format_1=["caffeine/Old"])
    hidden = root / "studies" / "caffeine" / ".A.new" / "A"
    hidden.mkdir(parents=True)
    (hidden / "study.json").write_text("{}", encoding="utf-8")
    folders, deleted = select(root)
    assert [f.name for f in folders] == ["A", "Old", "C"] and deleted == []


def test_a_checkout_without_studies_has_nothing_to_check(tmp_path, sf_vocabulary):
    with pytest.raises(CheckError, match="no studies folder"):
        select(tmp_path)
    with pytest.raises(CheckError, match="no studies folder"):
        check(tmp_path, [], sf_vocabulary)
    hidden = tmp_path / "studies" / "caffeine" / ".A.new" / "A"
    hidden.mkdir(parents=True)
    assert select(tmp_path) == ([], [])
    (hidden / "study.json").write_text("{}", encoding="utf-8")
    assert select(tmp_path) == ([], [])
    assert check(tmp_path, [], sf_vocabulary) == CheckReport()
    with pytest.raises(CheckError, match="not several"):
        select(tmp_path, staged=True, changed="HEAD")


def test_git_problems_are_usage_errors(tmp_path, checkout):
    with pytest.raises(CheckError, match="git"):
        select(tmp_path, staged=True)
    root, _ = checkout("caffeine/A")
    with pytest.raises(CheckError, match="nosuchbase"):
        select(root, changed="nosuchbase")
    # A base is never read as a git option, which could write a file.
    with pytest.raises(CheckError, match="--output"):
        select(root, changed=f"--output={tmp_path / 'diff.txt'}")
    assert not list(tmp_path.glob("diff.txt*"))


def test_a_valid_format_2_study_passes_and_format_1_is_skipped(checkout, sf_vocabulary):
    root, studies = checkout("caffeine/A", format_1=["caffeine/Old"])
    report = check(
        root,
        [studies["caffeine/A"], root / "studies" / "caffeine" / "Old"],
        sf_vocabulary,
    )
    assert report.ok and report.checked == ["caffeine/A"] and report.format_1 == 1
    assert report.problems == [] and report.deleted == []


def test_problems_of_form_validation_workbooks_and_the_repository(
    checkout, sf_vocabulary
):
    root, studies = checkout("caffeine/A", "caffeine/B")
    folder = studies["caffeine/A"]
    patch_study(studies["caffeine/B"], issue=7)
    patch_study(folder, issue=7)
    (folder / "subjects.tsv").write_text(
        (folder / "subjects.tsv").read_text(encoding="utf-8").replace("\t", "\t ", 1),
        encoding="utf-8",
    )
    (folder / "Example.xlsx").write_bytes(b"x")
    (folder / "A.xlsx").write_bytes(b"x")
    git(
        root,
        "add",
        "-f",
        "studies/caffeine/A/Example.xlsx",
        "studies/caffeine/A/A.xlsx",
    )
    report = check(root, [folder, studies["caffeine/B"]], sf_vocabulary)
    codes = {(p.study, p.code) for p in report.problems}
    assert ("caffeine/A", "not_canonical") in codes
    assert not report.ok
    assert ("caffeine/A", "unknown_file") in codes
    assert ("caffeine/A", "workbook_tracked") in codes
    assert (None, "duplicate_identifier") in codes
    assert report.checked == ["caffeine/A", "caffeine/B"]
    assert not any(p.study == "caffeine/B" for p in report.problems)
    form = next(p for p in report.problems if p.code == "not_canonical")
    assert form == Problem(
        study="caffeine/A",
        code="not_canonical",
        message="subjects.tsv is not in canonical form; run pkdb format",
        file="subjects.tsv",
    )


def test_each_problem_is_listed_once(checkout, sf_vocabulary):
    root, studies = checkout("caffeine/A")
    folder = studies["caffeine/A"]
    subjects = (folder / "subjects.tsv").read_text(encoding="utf-8")
    (folder / "subjects.tsv").write_text("<<<<<<< HEAD\n" + subjects, encoding="utf-8")
    (folder / "review.json").write_text('{"status": "draft"}', encoding="utf-8")
    report = check(root, [folder], sf_vocabulary)
    # Formatting and validation both find the conflict and the review.json form.
    assert sorted((p.code, p.file, p.row) for p in report.problems) == [
        ("merge_conflict", "subjects.tsv", 1),
        ("not_canonical", "review.json", None),
    ]


def test_a_tracked_workbook_and_state_file_are_problems(checkout, sf_vocabulary):
    root, studies = checkout("caffeine/A", "caffeine/B")
    a, b = studies["caffeine/A"], studies["caffeine/B"]
    (a / "A.xlsx").write_bytes(b"x")
    git(root, "add", "studies/caffeine/A/A.xlsx")
    git(root, "commit", "-q", "-m", "Track the workbook")
    (a / ".A.xlsx.pkdb-base").write_bytes(b"x")
    git(root, "add", "studies/caffeine/A/.A.xlsx.pkdb-base")
    (b / "B.xlsx").write_bytes(b"x")
    (b / ".B.xlsx.pkdb-base").write_bytes(b"x")
    report = check(root, [a, b], sf_vocabulary)
    assert report.problems == [
        Problem(
            study="caffeine/A",
            code="workbook_tracked",
            message="A.xlsx and .A.xlsx.pkdb-base are generated; remove them from git with git rm --cached",
            file="A.xlsx",
        )
    ]
    assert not report.ok


def test_studies_with_one_issue_are_a_repository_problem(checkout, sf_vocabulary):
    root, studies = checkout("caffeine/A", "caffeine/B", "codeine/C")
    patch_study(studies["caffeine/A"], issue=7)
    patch_study(studies["caffeine/B"], issue=7)
    report = check(root, [studies["codeine/C"]], sf_vocabulary)
    assert report.problems == [
        Problem(
            study=None,
            code="duplicate_identifier",
            message="Issue #7 is named by several studies: caffeine/A, caffeine/B",
        )
    ]
    assert not report.ok


def test_unreadable_studies_and_the_registry_file_are_repository_problems(
    checkout, sf_vocabulary
):
    root, studies = checkout("caffeine/A", "caffeine/B")
    patch_study(
        studies["caffeine/A"], release={"pkdb_id": "PKDB00001", "date": "2026-09-28"}
    )
    (root / "studies" / "study_identifiers.json").write_text(
        json.dumps({"PKDB00001": ["caffeine/Z", "2026-09-28"]}), encoding="utf-8"
    )
    (studies["caffeine/B"] / "study.json").write_text(
        '{"format": 2, "reference": 5}', encoding="utf-8"
    )
    report = check(root, [], sf_vocabulary)
    assert codes(report) == {(None, "unreadable_study"), (None, "registry_file")}
    unreadable = next(p for p in report.problems if p.code == "unreadable_study")
    assert unreadable.message.startswith("caffeine/B: ")
    assert report.checked == [] and not report.ok


def test_validation_warnings_do_not_fail_the_check(checkout, sf_vocabulary):
    root, studies = checkout("caffeine/A")
    add_unused_intervention(studies["caffeine/A"])
    report = check(root, [studies["caffeine/A"]], sf_vocabulary)
    assert [(p.code, p.severity, p.file, p.row) for p in report.problems] == [
        ("unused_intervention", "warning", "interventions.tsv", 3)
    ]
    assert report.ok


def test_errors_left_out_of_the_validation_report_fail_the_check(
    checkout, sf_vocabulary, monkeypatch
):
    root, studies = checkout("caffeine/A")
    monkeypatch.setattr(
        pkdb.checks,
        "validate_folder",
        lambda folder, vocabulary: ValidationReport(error_count=3),
    )
    report = check(root, [studies["caffeine/A"]], sf_vocabulary)
    assert [(p.code, p.message) for p in report.problems] == [
        (
            "validation_incomplete",
            "3 more errors are not listed; run pkdb validate to see them",
        )
    ]
    assert not report.ok


def test_an_unreadable_file_is_a_problem_of_its_study(
    checkout, sf_vocabulary, monkeypatch
):
    root, studies = checkout("caffeine/A", "caffeine/B")

    def unreadable(folder, *, check):
        if folder.name == "A":
            raise PermissionError(13, "Permission denied", str(folder / "subjects.tsv"))
        return format_folder(folder, check=check)

    monkeypatch.setattr(pkdb.checks, "format_folder", unreadable)
    report = check(root, [studies["caffeine/A"], studies["caffeine/B"]], sf_vocabulary)
    assert report.problems == [
        Problem(
            study="caffeine/A",
            code="unreadable_file",
            message="Cannot read subjects.tsv: Permission denied",
            file="subjects.tsv",
        )
    ]
    assert report.checked == ["caffeine/A", "caffeine/B"]


def test_check_never_writes(checkout, sf_vocabulary):
    root, studies = checkout("caffeine/A", "caffeine/B")
    folder = studies["caffeine/A"]
    (folder / "subjects.tsv").write_text(
        (folder / "subjects.tsv").read_text(encoding="utf-8") + "\n", encoding="utf-8"
    )
    (folder / "A.xlsx").write_bytes(b"x")
    git(root, "add", "-A")
    status = git(root, "status", "--porcelain", "--ignored", "--untracked-files=all")
    files = files_below(root)
    folders, _ = select(root, staged=True)
    report = check(root, folders, vocabulary_for(root, None))
    assert {p.code for p in report.problems} >= {"not_canonical", "workbook_tracked"}
    assert files_below(root) == files
    assert git(root, "status", "--porcelain", "--ignored", "--untracked-files=all") == (
        status
    )


def test_check_never_contacts_the_network(checkout, sf_vocabulary, monkeypatch):
    root, studies = checkout("caffeine/A", "caffeine/B")

    def refuse(*args, **kwargs):
        raise AssertionError("pkdb check must not contact the network")

    monkeypatch.setattr(pkdb.client.Client, "__init__", refuse)
    monkeypatch.setattr(httpx2.HTTPTransport, "handle_request", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    patch_study(studies["caffeine/A"], issue=7)
    (studies["caffeine/B"] / "notes.txt").write_text("x", encoding="utf-8")
    git(root, "add", "-A")
    folders, _ = select(root, staged=True)
    report = check(root, folders, vocabulary_for(root, None))
    assert report.checked == ["caffeine/A", "caffeine/B"]


def test_vocabulary_lock_is_used_when_present(tmp_path, monkeypatch):
    monkeypatch.setenv("PKDB_CACHE_DIR", str(tmp_path / "cache"))
    root = tmp_path / "data"
    (root / "studies").mkdir(parents=True)
    assert vocabulary_for(root, None).version == bundled_vocabulary().version
    Vocabulary(version="locked", measurements=()).save(root / "vocabulary.lock.json")
    assert vocabulary_for(root, None).version == "locked"
    explicit = tmp_path / "explicit.json"
    Vocabulary(version="explicit", measurements=()).save(explicit)
    assert vocabulary_for(root, explicit).version == "explicit"
    (root / "vocabulary.lock.json").write_text("{", encoding="utf-8")
    with pytest.raises(CheckError, match="vocabulary.lock.json"):
        vocabulary_for(root, None)
    with pytest.raises(CheckError, match="missing.json"):
        vocabulary_for(root, tmp_path / "missing.json")
    assert not (tmp_path / "cache").exists()
