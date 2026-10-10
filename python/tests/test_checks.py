import json
import os
import shutil
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
from pkdb.studyformat.validation import validate_folder


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
    # An unstaged change selects nothing.
    (studies["caffeine/A"] / "subjects.tsv").write_text(
        (studies["caffeine/A"] / "subjects.tsv").read_text() + "\n", encoding="utf-8"
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


def test_changes_on_the_base_after_the_fork_are_not_selected(checkout):
    root, studies = checkout("caffeine/A", "caffeine/B")
    git(root, "checkout", "-q", "-b", "feature")
    (studies["caffeine/B"] / "notes.txt").write_text("x", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "change B")
    git(root, "checkout", "-q", "main")
    (studies["caffeine/A"] / "notes.txt").write_text("x", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "change A")
    git(root, "checkout", "-q", "feature")
    # Only the changes since the merge base count: main...HEAD, not main..HEAD.
    assert select(root, changed="main") == ([studies["caffeine/B"]], [])


def test_a_shallow_clone_without_the_merge_base_is_a_usage_error(tmp_path, checkout):
    root, studies = checkout("caffeine/A", "caffeine/B")
    git(root, "checkout", "-q", "-b", "feature")
    (studies["caffeine/B"] / "notes.txt").write_text("x", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "change B")
    git(root, "checkout", "-q", "main")
    (studies["caffeine/A"] / "notes.txt").write_text("x", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "change A")
    clone = tmp_path / "clone"
    url = root.as_uri()
    git(tmp_path, "clone", "-q", "--depth", "1", "--branch", "feature", url, "clone")
    git(clone, "fetch", "-q", "--depth", "1", "origin", "main:refs/remotes/origin/main")
    with pytest.raises(CheckError, match="no merge base"):
        select(clone, changed="origin/main")


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


def test_a_study_that_lost_its_study_json_is_checked(checkout, sf_vocabulary):
    root, studies = checkout("caffeine/A")
    git(root, "rm", "-q", "studies/caffeine/A/study.json")
    folders, deleted = select(root, staged=True)
    assert folders == [studies["caffeine/A"]] and deleted == []
    report = check(root, folders, sf_vocabulary, staged=True)
    assert ("caffeine/A", "missing_file") in codes(report) and not report.ok
    git(root, "commit", "-q", "-m", "Remove study.json")
    assert select(root, changed="HEAD~1") == ([studies["caffeine/A"]], [])
    git(root, "rm", "-r", "-q", "studies/caffeine/A")
    git(root, "commit", "-q", "-m", "Remove the study")
    assert select(root, changed="HEAD~2") == ([], ["caffeine/A"])


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
    with pytest.raises(CheckError, match="does not exist"):
        select(root, paths=[caffeine / "Missing"])


def test_without_a_selection_every_study_is_selected(checkout):
    root, studies = checkout("caffeine/A", "codeine/C", format_1=["caffeine/Old"])
    hidden = root / "studies" / "caffeine" / ".A.new" / "A"
    hidden.mkdir(parents=True)
    (hidden / "study.json").write_text("{}", encoding="utf-8")
    # A study.json deeper down is no study, and neither is a folder without one.
    nested = studies["caffeine/A"] / "old"
    nested.mkdir()
    (nested / "study.json").write_text("{}", encoding="utf-8")
    (root / "studies" / "caffeine" / "Empty").mkdir()
    folders, deleted = select(root)
    assert [f.name for f in folders] == ["A", "Old", "C"] and deleted == []
    with pytest.raises(CheckError, match=r"A/old is not a study folder"):
        select(root, paths=[root / "studies" / "caffeine"])


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
    with pytest.raises(CheckError, match="The base nosuchbase is not a commit"):
        select(root, changed="nosuchbase")
    # An empty base would compare HEAD with itself and check nothing.
    for empty in ("", "  "):
        with pytest.raises(CheckError, match="The base is empty"):
            select(root, changed=empty)
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
        message="subjects.tsv is not in canonical form (first difference in line 1); run pkdb format",
        file="subjects.tsv",
        row=1,
    )


def test_a_table_without_rows_is_not_canonical(checkout, sf_vocabulary):
    root, studies = checkout("caffeine/A")
    path = studies["caffeine/A"] / "scatters_Fig2.tsv"
    path.write_text(path.read_text(encoding="utf-8").splitlines()[0] + "\n")
    report = check(root, [studies["caffeine/A"]], sf_vocabulary)
    assert (
        Problem(
            study="caffeine/A",
            code="not_canonical",
            message="scatters_Fig2.tsv has no rows; run pkdb format to remove it",
            file="scatters_Fig2.tsv",
        )
        in report.problems
    )


def test_each_problem_is_listed_once(checkout, sf_vocabulary):
    root, studies = checkout("caffeine/A")
    folder = studies["caffeine/A"]
    subjects = (folder / "subjects.tsv").read_text(encoding="utf-8")
    (folder / "subjects.tsv").write_text("<<<<<<< HEAD\n" + subjects, encoding="utf-8")
    (folder / "review.json").write_text('{"status": "draft"}', encoding="utf-8")
    report = check(root, [folder], sf_vocabulary)
    assert sorted((p.code, p.file, p.row) for p in report.problems) == [
        ("merge_conflict", "subjects.tsv", 1),
        ("not_canonical", "review.json", 1),
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


def test_staged_checks_leave_out_files_that_git_does_not_track(checkout, sf_vocabulary):
    root, studies = checkout("caffeine/A")
    folder = studies["caffeine/A"]
    (root / ".gitignore").write_text("Ignored.xlsx\n", encoding="utf-8")
    add_unused_intervention(folder)
    git(root, "add", "-A")
    # Neither file goes into the commit, so pre-commit must not fail on them.
    (folder / "Example.xlsx").write_bytes(b"x")
    (folder / "Ignored.xlsx").write_bytes(b"x")
    folders, _ = select(root, staged=True)
    staged = check(root, folders, sf_vocabulary, staged=True)
    assert staged.ok
    assert [(p.code, p.file) for p in staged.problems] == [
        ("unused_intervention", "interventions.tsv"),
        ("untracked_errors", None),
    ]
    assert staged.problems[1].message == (
        "Errors in files that git does not track can hide other errors of the study: "
        "Example.xlsx, Ignored.xlsx; add the files with git add or remove them"
    )
    everything = check(root, folders, sf_vocabulary)
    assert {(p.code, p.file) for p in everything.problems} == {
        ("unknown_file", "Example.xlsx"),
        ("unknown_file", "Ignored.xlsx"),
        ("unused_intervention", "interventions.tsv"),
    }
    git(root, "add", "studies/caffeine/A/Example.xlsx")
    tracked = check(root, folders, sf_vocabulary, staged=True)
    assert [(p.code, p.file) for p in tracked.problems] == [
        ("unknown_file", "Example.xlsx"),
        ("unused_intervention", "interventions.tsv"),
        ("untracked_errors", None),
    ]


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

    def unreadable(folder, vocabulary):
        if folder.name == "A":
            raise PermissionError(13, "Permission denied", str(folder / "subjects.tsv"))
        return validate_folder(folder, vocabulary)

    monkeypatch.setattr(pkdb.checks, "validate_folder", unreadable)
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


def test_a_file_name_that_is_not_utf_8_is_a_problem_of_its_study(
    checkout, sf_vocabulary
):
    root, studies = checkout("caffeine/A", "caffeine/B")
    bad = os.fsencode(studies["caffeine/A"]) + b"/caf\xe9.txt"
    try:
        with open(bad, "wb") as stream:
            stream.write(b"x\n")
    except OSError, UnicodeDecodeError:
        # APFS refuses the name; Windows file names are Unicode, and Python reads a
        # bytes path there as UTF-8.
        pytest.skip("the platform refuses a file name that is not UTF-8")
    report = check(root, [studies["caffeine/A"], studies["caffeine/B"]], sf_vocabulary)
    assert report.checked == ["caffeine/A", "caffeine/B"]
    assert report.problems
    assert {(p.study, p.code) for p in report.problems} == {
        ("caffeine/A", "unreadable_study")
    }
    assert not report.ok


def test_an_unexpected_error_of_one_study_does_not_stop_the_others(
    checkout, sf_vocabulary, monkeypatch
):
    root, studies = checkout("caffeine/A", "caffeine/B")

    def broken(folder, vocabulary):
        if folder.name == "A":
            raise UnicodeEncodeError("utf-8", "\udce9", 0, 1, "surrogates not allowed")
        return validate_folder(folder, vocabulary)

    monkeypatch.setattr(pkdb.checks, "validate_folder", broken)
    patch_study(studies["caffeine/B"], issue=3)
    add_unused_intervention(studies["caffeine/B"])
    report = check(root, [studies["caffeine/A"], studies["caffeine/B"]], sf_vocabulary)
    assert report.checked == ["caffeine/A", "caffeine/B"]
    failed = [p for p in report.problems if p.code == "unreadable_study"]
    assert [p.study for p in failed] == ["caffeine/A"]
    assert "UnicodeEncodeError" in failed[0].message
    assert any(p.study == "caffeine/B" for p in report.problems)
    assert not report.ok


def test_an_os_error_of_one_study_does_not_stop_the_others(
    checkout, sf_vocabulary, monkeypatch
):
    root, studies = checkout("caffeine/A", "caffeine/B")

    def broken(folder, vocabulary):
        if folder.name == "A":
            raise OSError(5, "Input/output error")
        return validate_folder(folder, vocabulary)

    monkeypatch.setattr(pkdb.checks, "validate_folder", broken)
    report = check(root, [studies["caffeine/A"], studies["caffeine/B"]], sf_vocabulary)
    assert [(p.study, p.code) for p in report.problems] == [
        ("caffeine/A", "unreadable_file")
    ]
    assert report.checked == ["caffeine/A", "caffeine/B"]


def test_repository_checks_consider_only_studies_that_git_tracks(
    checkout, sf_vocabulary
):
    root, studies = checkout("caffeine/A", "codeine/C")
    patch_study(studies["caffeine/A"], issue=7)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "Name the issue")
    copy = root / "studies" / "caffeine" / "Copy"
    shutil.copytree(studies["caffeine/A"], copy)
    folders = [studies["codeine/C"]]
    # An untracked copy is left out, as the commit and CI leave it out.
    assert check(root, folders, sf_vocabulary, staged=True).ok
    assert check(root, folders, sf_vocabulary).ok
    git(root, "add", "studies/caffeine/Copy/study.json")
    report = check(root, folders, sf_vocabulary, staged=True)
    assert codes(report) == {(None, "duplicate_identifier")}
    assert "caffeine/A, caffeine/Copy" in report.problems[0].message


def test_outside_git_the_repository_checks_scan_every_study(tmp_path, valid_files):
    from check_fixtures import format_2_study

    root = tmp_path / "plain"
    first = format_2_study(root, "caffeine/A", valid_files)
    second = format_2_study(root, "caffeine/B", valid_files)
    patch_study(first, issue=7)
    patch_study(second, issue=7)
    report = check(root, [], Vocabulary(version="v", measurements=()))
    assert codes(report) == {(None, "duplicate_identifier")}


def write_non_utf_8_file(folder):
    bad = os.fsencode(folder) + b"/caf\xe9.txt"
    try:
        with open(bad, "wb") as stream:
            stream.write(b"x\n")
    except OSError, UnicodeDecodeError:
        pytest.skip("the platform refuses a file name that is not UTF-8")


def test_staged_checks_leave_out_an_untracked_file_that_is_not_utf_8(
    checkout, sf_vocabulary
):
    root, studies = checkout("caffeine/A")
    write_non_utf_8_file(studies["caffeine/A"])
    folders = [studies["caffeine/A"]]
    staged = check(root, folders, sf_vocabulary, staged=True)
    assert staged.ok
    assert [(p.code, p.severity) for p in staged.problems] == [
        ("untracked_errors", "warning")
    ]
    assert "caf\\udce9.txt" in staged.problems[0].message
    # CI sees the file when it is tracked, and names it.
    git(root, "add", "-A")
    tracked = check(root, folders, sf_vocabulary, staged=True)
    assert [(p.code, p.file) for p in tracked.problems] == [
        ("unreadable_study", "caf\\udce9.txt")
    ]
    assert "caf\\udce9.txt" in tracked.problems[0].message
    json.dumps(tracked.model_dump(mode="json"), ensure_ascii=False).encode("utf-8")


def test_a_key_error_of_one_study_is_reported_and_the_others_are_checked(
    checkout, sf_vocabulary, monkeypatch
):
    root, studies = checkout("caffeine/A", "caffeine/B")

    def broken(folder, vocabulary):
        if folder.name == "A":
            raise KeyError("measurement")
        return validate_folder(folder, vocabulary)

    monkeypatch.setattr(pkdb.checks, "validate_folder", broken)
    patch_study(studies["caffeine/B"], issue=3)
    add_unused_intervention(studies["caffeine/B"])
    report = check(root, [studies["caffeine/A"], studies["caffeine/B"]], sf_vocabulary)
    failed = [p for p in report.problems if p.study == "caffeine/A"]
    assert [(p.code, p.severity) for p in failed] == [("unreadable_study", "error")]
    assert "KeyError" in failed[0].message
    assert any(p.study == "caffeine/B" for p in report.problems)
    assert not report.ok


@pytest.mark.parametrize("error", [CheckError("git failed"), KeyboardInterrupt()])
def test_a_usage_error_and_an_interrupt_stop_the_check(
    checkout, sf_vocabulary, monkeypatch, error
):
    root, studies = checkout("caffeine/A")

    def broken(folder, vocabulary):
        raise error

    monkeypatch.setattr(pkdb.checks, "validate_folder", broken)
    with pytest.raises(type(error)):
        check(root, [studies["caffeine/A"]], sf_vocabulary)


def test_a_path_that_does_not_exist_is_named(checkout):
    root, _ = checkout("caffeine/A")
    with pytest.raises(CheckError, match="Missing does not exist"):
        select(root, paths=[root / "studies" / "caffeine" / "Missing"])


def test_a_studies_folder_that_cannot_be_listed_is_a_usage_error(checkout, monkeypatch):
    root, _ = checkout("caffeine/A")

    def denied(root):
        raise PermissionError(13, "Permission denied", str(root / "studies"))

    monkeypatch.setattr(pkdb.checks, "checkout_folders", denied)
    with pytest.raises(CheckError, match="Cannot list .*studies: Permission denied"):
        select(root)


def test_a_copy_inside_another_work_tree_scans_every_study(tmp_path, valid_files):
    from check_fixtures import format_2_study

    outer = tmp_path / "outer"
    outer.mkdir()
    git(outer, "init", "-q")
    root = outer / "pkdb_data"
    first = format_2_study(root, "caffeine/A", valid_files)
    second = format_2_study(root, "caffeine/B", valid_files)
    patch_study(first, issue=7)
    patch_study(second, issue=7)
    report = check(root, [], Vocabulary(version="v", measurements=()))
    assert codes(report) == {(None, "duplicate_identifier")}


def test_a_content_decoding_error_does_not_blame_a_file_name(
    checkout, sf_vocabulary, monkeypatch
):
    root, studies = checkout("caffeine/A")
    write_non_utf_8_file(studies["caffeine/A"])

    def broken(folder, vocabulary):
        raise UnicodeDecodeError("utf-8", b"\xe9", 0, 1, "invalid continuation byte")

    monkeypatch.setattr(pkdb.checks, "validate_folder", broken)
    report = check(root, [studies["caffeine/A"]], sf_vocabulary)
    assert [(p.code, p.file) for p in report.problems] == [("unreadable_study", None)]


def test_a_symlinked_or_differently_spelled_root_is_still_the_top_of_the_work_tree(
    checkout, sf_vocabulary, tmp_path
):
    root, studies = checkout("caffeine/A", "caffeine/B")
    patch_study(studies["caffeine/A"], issue=7)
    patch_study(studies["caffeine/B"], issue=7)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "Name the issue")
    link = tmp_path / "link"
    try:
        link.symlink_to(root, target_is_directory=True)
    except OSError, NotImplementedError:
        pytest.skip("the platform refuses symbolic links")
    # Tracked studies are found through the link, so the duplicate shows once.
    report = check(link, [], sf_vocabulary, staged=True)
    assert codes(report) == {(None, "duplicate_identifier")}
    # An untracked copy is still left out through the link.
    copy = root / "studies" / "caffeine" / "Copy"
    shutil.copytree(studies["caffeine/A"], copy)
    report = check(link, [], sf_vocabulary, staged=True)
    assert "Copy" not in report.problems[0].message


def test_the_top_of_the_work_tree_is_compared_by_identity(
    checkout, sf_vocabulary, tmp_path, monkeypatch
):
    root, studies = checkout("caffeine/A", "caffeine/B")
    patch_study(studies["caffeine/A"], issue=7)
    patch_study(studies["caffeine/B"], issue=7)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "Name the issue")
    link = tmp_path / "link"
    try:
        link.symlink_to(root, target_is_directory=True)
    except OSError, NotImplementedError:
        pytest.skip("the platform refuses symbolic links")
    git_call = pkdb.checks._git

    def spelled_through_the_link(folder, *args, **options):
        if args[:2] == ("rev-parse", "--show-toplevel"):
            return f"{link}\n".encode()
        return git_call(folder, *args, **options)

    monkeypatch.setattr(pkdb.checks, "_git", spelled_through_the_link)
    assert pkdb.checks._tracked_studies(root) is not None
    report = check(root, [], sf_vocabulary, staged=True)
    assert codes(report) == {(None, "duplicate_identifier")}
