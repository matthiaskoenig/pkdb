import json
import os
import sys
import time

import pytest
from migration_fixtures import IMAGES, SHEETS, STUDY, v1_full_example, v1_study

from pkdb.domain.vocabulary import vocabulary_hash
from pkdb.migration import run as run_module
from pkdb.migration.convert import convert_study
from pkdb.migration.model import MigrationReport, NotConverted, VocabularyUsed
from pkdb.migration.registry import Registry
from pkdb.migration.run import migrate
from pkdb.references import NotFound, ReferenceResolver
from pkdb.studyformat.validation import is_v2_folder

# pkdb migrate locks the repository with flock, which Windows lacks; there it
# refuses to run (see test_cli.py).
fcntl = pytest.importorskip("fcntl", reason="pkdb migrate needs Linux or macOS")


class Resolved(ReferenceResolver):
    def resolve(self, seed, *, sid, name, existing=None, reset_overrides=False):
        return {"sid": sid, "name": name, "pmid": seed["pmid"], "title": "Resolved"}


class Unresolvable(ReferenceResolver):
    def resolve(self, *args, **kwargs):
        raise NotFound("No PubMed record found for 123")


def offline():
    return ReferenceResolver(offline=True)


def resolved():
    return Resolved(offline=True)


def unresolvable():
    return Unresolvable(offline=True)


def dying(task):
    """`_one` of a worker that stops on caffeine/Example once codeine/Example is written."""
    if task.v1.parent.name != "caffeine":
        return run_module._one(task)
    other = task.v1.parent.parent / "codeine" / "Example"
    deadline = time.monotonic() + 60
    while not is_v2_folder(other) and time.monotonic() < deadline:
        time.sleep(0.05)
    (task.work / "new" / "caffeine" / "Example").mkdir(parents=True)
    os._exit(1)


def go(root, vocabulary, **options):
    return migrate(
        options.pop("paths", [root / "studies"]),
        report=root / "migration.json",
        registry=options.pop("registry", None),
        approver=options.pop("approver", None),
        jobs=options.pop("jobs", 1),
        vocabulary=vocabulary,
        resolver_factory=options.pop("resolver_factory", offline),
        **options,
    )


def without_reference(root):
    folder = v1_full_example(root)
    (folder / "reference.json").unlink()
    return folder


def two_studies(root):
    """caffeine/Example and codeine/Example."""
    v1_full_example(root)
    v1_full_example(root / "other")
    (root / "other" / "studies" / "caffeine").rename(root / "studies" / "codeine")


def keep_v1(monkeypatch):
    """Let the gate find a mismatch, so every converted study stays v1."""
    monkeypatch.setattr(
        run_module,
        "judge",
        lambda v1, v2, vocabulary: run_module.StudyResult(
            study=f"{v1.parent.name}/{v1.name}", outcome="mismatch"
        ),
    )


def tree(root):
    """Every path below root with the bytes of each file."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes() if path.is_file() else None
        for path in sorted(root.rglob("*"))
    }


def interrupted(root):
    """caffeine/Example as a run interrupted after the first rename of its swap leaves it."""
    folder = v1_full_example(root)
    backup = root / ".pkdb-migrate" / "v1" / "caffeine" / "Example"
    backup.parent.mkdir(parents=True)
    folder.rename(backup)
    return backup


def written_report(root):
    """The JSON report that the last run wrote."""
    return MigrationReport.model_validate_json((root / "migration.json").read_text())


def interrupt_second_swap(monkeypatch):
    """Swap the first proven study, then stop the run as Ctrl-C would."""
    swap = run_module._swap
    swaps = []

    def interrupted_swap(root, folder):
        swaps.append(folder)
        if len(swaps) > 1:
            raise KeyboardInterrupt
        swap(root, folder)

    monkeypatch.setattr(run_module, "_swap", interrupted_swap)


def backup_of_example(root):
    """A v1 backup of caffeine/Example as an interrupted swap leaves it."""
    backup = root / ".pkdb-migrate" / "v1" / "caffeine" / "Example"
    backup.parent.mkdir(parents=True)
    v1_full_example(root / "old").rename(backup)
    return backup


def test_a_proven_study_replaces_its_v1_folder(tmp_path, sf_vocabulary):
    folder = v1_full_example(tmp_path)
    report = go(tmp_path, sf_vocabulary)
    assert [(s.study, s.outcome, s.written) for s in report.studies] == [
        ("caffeine/Example", "identical", True)
    ]
    assert is_v2_folder(folder) and not (folder / "Example.xlsx").exists()
    assert not (tmp_path / ".pkdb-migrate").exists()
    assert (tmp_path / "migration.md").exists()


def test_a_dry_run_writes_only_the_report(tmp_path, sf_vocabulary):
    folder = v1_full_example(tmp_path)
    before = sorted(p.name for p in folder.iterdir())
    report = go(tmp_path, sf_vocabulary, dry_run=True)
    assert report.studies[0].written is False
    assert sorted(p.name for p in folder.iterdir()) == before
    assert (tmp_path / "migration.json").exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "migration.json",
        "migration.md",
        "studies",
    ]


def test_a_mismatch_stays_v1(tmp_path, sf_vocabulary, monkeypatch):
    folder = v1_full_example(tmp_path)
    keep_v1(monkeypatch)
    report = go(tmp_path, sf_vocabulary)
    assert report.studies[0].written is False
    assert (folder / "Example.xlsx").exists()


def test_a_rerun_skips_converted_studies_and_retries_the_rest(tmp_path, sf_vocabulary):
    v1_full_example(tmp_path)
    # The converter refuses Broken late, after it wrote part of the work folder.
    broken = v1_study(
        tmp_path, {**STUDY, "name": "Broken", "sid": "Broken"}, SHEETS, IMAGES
    )
    (broken / "Broken_Tab2.jpg").write_bytes(b"jpg")
    first = go(tmp_path, sf_vocabulary)
    assert [(s.study, s.outcome, s.written) for s in first.studies] == [
        ("caffeine/Broken", "not_converted", False),
        ("caffeine/Example", "identical", True),
    ]
    assert first.studies[0].reason is not None
    assert first.studies[0].reason.startswith("image_conflict: ")
    assert (broken / "Broken.xlsx").exists()
    # Example is format 2 now: it is skipped, and its first result carried forward.
    second = go(tmp_path, sf_vocabulary)
    assert second.skipped == []
    assert [s.study for s in second.studies] == ["caffeine/Broken", "caffeine/Example"]
    assert second.studies[1] == first.studies[1]
    (tmp_path / "migration.json").unlink()
    third = go(tmp_path, sf_vocabulary)
    assert third.skipped == ["caffeine/Example"]
    assert [s.study for s in third.studies] == ["caffeine/Broken"]


def test_folders_without_study_json_move_to_papers_and_empty_ones_go(
    tmp_path, sf_vocabulary
):
    paper = tmp_path / "studies" / "caffeine" / "Paper2001"
    paper.mkdir(parents=True)
    (paper / "Paper2001.pdf").write_bytes(b"%PDF")
    (paper / "Paper2001.xlsx").write_bytes(b"xlsx")
    (tmp_path / "studies" / "caffeine" / "Empty2002" / "figures").mkdir(parents=True)
    report = go(tmp_path, sf_vocabulary)
    assert [(m.target, m.workbook) for m in report.papers] == [
        ("papers/caffeine/Paper2001", True)
    ]
    assert report.papers[0].source == "studies/caffeine/Paper2001"
    assert report.papers[0].files == ["Paper2001.pdf", "Paper2001.xlsx"]
    assert (tmp_path / "papers" / "caffeine" / "Paper2001" / "Paper2001.xlsx").exists()
    assert not paper.exists()
    assert report.removed_empty == ["caffeine/Empty2002"]
    assert not (tmp_path / "studies" / "caffeine" / "Empty2002").exists()


def test_a_dry_run_lists_paper_moves_and_empty_folders_but_keeps_them(
    tmp_path, sf_vocabulary
):
    paper = tmp_path / "studies" / "caffeine" / "Paper2001"
    paper.mkdir(parents=True)
    (paper / "Paper2001.pdf").write_bytes(b"%PDF")
    empty = tmp_path / "studies" / "caffeine" / "Empty10"
    empty.mkdir()
    (tmp_path / "studies" / "caffeine" / "Empty9").mkdir()
    report = go(tmp_path, sf_vocabulary, dry_run=True)
    assert [(m.target, m.workbook) for m in report.papers] == [
        ("papers/caffeine/Paper2001", False)
    ]
    assert report.removed_empty == ["caffeine/Empty9", "caffeine/Empty10"]
    assert (paper / "Paper2001.pdf").exists() and empty.is_dir()
    assert not (tmp_path / "papers").exists()


def test_a_paper_folder_never_replaces_an_existing_one(tmp_path, sf_vocabulary):
    paper = tmp_path / "studies" / "caffeine" / "Paper2001"
    paper.mkdir(parents=True)
    (paper / "Paper2001.pdf").write_bytes(b"%PDF")
    existing = tmp_path / "papers" / "caffeine" / "Paper2001"
    existing.mkdir(parents=True)
    (existing / "notes.txt").write_text("keep")
    report = go(tmp_path, sf_vocabulary)
    assert report.papers == []
    [result] = report.studies
    assert (result.study, result.outcome) == ("caffeine/Paper2001", "not_converted")
    assert result.reason is not None and result.reason.startswith("papers_exists: ")
    assert (paper / "Paper2001.pdf").exists()
    assert sorted(p.name for p in existing.iterdir()) == ["notes.txt"]


def test_a_format_2_folder_without_study_json_stays(tmp_path, sf_vocabulary):
    folder = tmp_path / "studies" / "caffeine" / "Draft2003"
    folder.mkdir(parents=True)
    (folder / "review.json").write_text("{}")
    report = go(tmp_path, sf_vocabulary)
    assert (report.skipped, report.papers) == (["caffeine/Draft2003"], [])
    assert (folder / "review.json").exists()


def test_an_exception_in_one_study_does_not_stop_the_run(
    tmp_path, sf_vocabulary, monkeypatch
):
    two_studies(tmp_path)

    def flaky(v1, target, **options):
        if v1.parent.name == "caffeine":
            raise RuntimeError("boom")
        return convert_study(v1, target, **options)

    monkeypatch.setattr(run_module, "convert_study", flaky)
    report = go(tmp_path, sf_vocabulary)
    assert [(s.study, s.outcome, s.reason, s.written) for s in report.studies] == [
        (
            "caffeine/Example",
            "not_converted",
            "converter_error: RuntimeError: boom",
            False,
        ),
        ("codeine/Example", "identical", None, True),
    ]
    assert (tmp_path / "studies" / "caffeine" / "Example" / "Example.xlsx").exists()


def test_an_unreadable_v1_study_is_invalid_v1(tmp_path, sf_vocabulary):
    folder = v1_full_example(tmp_path)
    (folder / "study.json").write_text("{", encoding="utf-8")
    [result] = go(tmp_path, sf_vocabulary).studies
    assert (result.outcome, result.decisions, result.written) == (
        "invalid_v1",
        [],
        False,
    )
    assert (folder / "Example.xlsx").exists()


def test_a_refused_conversion_leaves_no_work_folder(
    tmp_path, sf_vocabulary, monkeypatch
):
    folder = v1_full_example(tmp_path)
    work = tmp_path / "work"

    def late(v1, target, **options):
        target.mkdir(parents=True)
        (target / "study.json").write_text("{}")
        raise NotConverted("format", "reference.json: not formatted")

    monkeypatch.setattr(run_module, "convert_study", late)
    task = run_module.Task(
        v1=folder,
        work=work,
        registry=Registry(),
        approver=None,
        vocabulary=sf_vocabulary,
        dry_run=False,
        resolver_factory=offline,
    )
    result = run_module._one(task)
    assert (result.outcome, result.reason) == (
        "not_converted",
        "format: reference.json: not formatted",
    )
    assert not (work / "new" / "caffeine" / "Example").exists()


def test_a_missing_reference_is_resolved_in_the_work_area(tmp_path, sf_vocabulary):
    folder = without_reference(tmp_path)
    before = sorted(p.name for p in folder.iterdir())
    dry = go(tmp_path, sf_vocabulary, dry_run=True, resolver_factory=resolved)
    assert sorted(p.name for p in folder.iterdir()) == before
    report = go(tmp_path, sf_vocabulary, resolver_factory=resolved)
    for result in (dry.studies[0], report.studies[0]):
        assert result.outcome == "identical"
        assert [(d.kind, d.detail) for d in result.decisions][0] == (
            "reference_resolved",
            "Created reference.json from PubMed 123",
        )
    assert report.studies[0].written and is_v2_folder(folder)
    assert json.loads((folder / "reference.json").read_text())["title"] == "Resolved"


def test_a_reference_that_cannot_be_resolved_keeps_the_study_v1(
    tmp_path, sf_vocabulary
):
    folder = without_reference(tmp_path)
    before = sorted(p.name for p in folder.iterdir())
    [result] = go(tmp_path, sf_vocabulary, resolver_factory=unresolvable).studies
    assert result.outcome == "not_converted"
    assert result.reason == (
        "reference: Cannot create reference.json from PubMed 123: "
        "No PubMed record found for 123"
    )
    assert sorted(p.name for p in folder.iterdir()) == before
    assert not (tmp_path / ".pkdb-migrate").exists()


def test_an_interrupted_swap_is_restored_on_the_next_run(
    tmp_path, sf_vocabulary, monkeypatch
):
    before = tree(interrupted(tmp_path))
    keep_v1(monkeypatch)
    report = go(tmp_path, sf_vocabulary)
    assert report.recovered == ["caffeine/Example"]
    assert tree(tmp_path / "studies" / "caffeine" / "Example") == before
    assert not (tmp_path / ".pkdb-migrate").exists()


def test_a_dry_run_refuses_to_start_after_an_interrupted_run(tmp_path, sf_vocabulary):
    interrupted(tmp_path)
    before = tree(tmp_path)
    with pytest.raises(run_module.RunRefused) as refused:
        go(tmp_path, sf_vocabulary, dry_run=True)
    assert str(refused.value) == (
        f"An interrupted run left .pkdb-migrate in {tmp_path}; "
        "run pkdb migrate without --dry-run to finish or undo it."
    )
    assert tree(tmp_path) == before


def test_a_second_run_is_refused_while_one_runs(tmp_path, sf_vocabulary):
    interrupted(tmp_path)
    before = tree(tmp_path)
    descriptor = os.open(tmp_path, os.O_RDONLY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for dry_run in (False, True):
            with pytest.raises(run_module.RunRefused) as refused:
                go(tmp_path, sf_vocabulary, dry_run=dry_run)
            assert str(refused.value) == (
                f"Another pkdb migrate is running in {tmp_path}; wait for it to finish."
            )
    finally:
        os.close(descriptor)
    assert tree(tmp_path) == before
    assert go(tmp_path, sf_vocabulary).recovered == ["caffeine/Example"]


def test_a_run_without_file_locks_is_refused(tmp_path, sf_vocabulary, monkeypatch):
    v1_full_example(tmp_path)
    before = tree(tmp_path)
    monkeypatch.setitem(sys.modules, "fcntl", None)
    with pytest.raises(run_module.RunRefused, match="needs Linux or macOS"):
        go(tmp_path, sf_vocabulary)
    assert tree(tmp_path) == before


def test_a_finished_swap_drops_its_backup_on_the_next_run(tmp_path, sf_vocabulary):
    folder = v1_full_example(tmp_path)
    go(tmp_path, sf_vocabulary)
    backup_of_example(tmp_path)  # interrupted after the second rename of a swap
    report = go(tmp_path, sf_vocabulary)
    assert (report.recovered, report.skipped) == (["caffeine/Example"], [])
    assert [(s.study, s.written) for s in report.studies] == [
        ("caffeine/Example", True)
    ]
    assert is_v2_folder(folder) and not (tmp_path / ".pkdb-migrate").exists()


def test_a_backup_beside_a_v1_folder_stops_the_run(tmp_path, sf_vocabulary):
    v1_full_example(tmp_path)
    backup = backup_of_example(tmp_path)
    with pytest.raises(ValueError) as error:
        go(tmp_path, sf_vocabulary)
    folder = tmp_path / "studies" / "caffeine" / "Example"
    assert str(error.value) == (
        f"{backup} and {folder} both hold the format 1 study caffeine/Example. "
        f"Keep the right one in {folder}, delete {backup} and run again."
    )
    assert (backup / "Example.xlsx").exists()


def test_a_failed_swap_puts_the_v1_folder_back(tmp_path, sf_vocabulary, monkeypatch):
    folder = v1_full_example(tmp_path)
    rename = run_module._rename

    def failing(source, target):
        if source.parent.parent.name == "new":
            raise OSError("disk full")
        rename(source, target)

    monkeypatch.setattr(run_module, "_rename", failing)
    [result] = go(tmp_path, sf_vocabulary).studies
    assert (result.outcome, result.written) == ("not_converted", False)
    assert result.reason == "swap: OSError: disk full"
    assert (folder / "Example.xlsx").exists()
    assert not (tmp_path / ".pkdb-migrate").exists()


def test_a_swap_that_cannot_be_undone_is_recovered_by_the_next_run(
    tmp_path, sf_vocabulary, monkeypatch
):
    folder = v1_full_example(tmp_path)
    rename = run_module._rename

    def failing(source, target):
        if source.parent.parent.name in ("new", "v1"):
            raise OSError("disk full")
        rename(source, target)

    monkeypatch.setattr(run_module, "_rename", failing)
    with pytest.raises(run_module.SwapError):
        go(tmp_path, sf_vocabulary)
    assert not folder.exists()
    assert (tmp_path / ".pkdb-migrate" / "v1" / "caffeine" / "Example").is_dir()
    assert written_report(tmp_path).interrupted
    monkeypatch.setattr(run_module, "_rename", rename)
    keep_v1(monkeypatch)
    report = go(tmp_path, sf_vocabulary)
    assert report.recovered == ["caffeine/Example"]
    assert (folder / "Example.xlsx").exists()


def test_a_backup_left_behind_is_never_deleted_unseen(
    tmp_path, sf_vocabulary, monkeypatch
):
    folder = v1_full_example(tmp_path)
    remove = run_module._remove
    monkeypatch.setattr(run_module, "_remove", lambda path: None)
    with pytest.raises(run_module.SwapError):
        go(tmp_path, sf_vocabulary)
    assert (tmp_path / ".pkdb-migrate" / "v1" / "caffeine" / "Example").is_dir()
    monkeypatch.setattr(run_module, "_remove", remove)
    report = go(tmp_path, sf_vocabulary)
    assert (report.recovered, report.skipped) == (["caffeine/Example"], [])
    assert [(s.study, s.written) for s in report.studies] == [
        ("caffeine/Example", True)
    ]
    assert is_v2_folder(folder) and not (tmp_path / ".pkdb-migrate").exists()


def test_the_registry_is_deleted_once_every_study_is_released(tmp_path, sf_vocabulary):
    v1_full_example(tmp_path)
    registry = tmp_path / "studies" / "study_identifiers.json"
    registry.write_text(json.dumps({"PKDB00042": ["caffeine/Example", "2020-01-02"]}))
    report = go(tmp_path, sf_vocabulary, registry=registry, approver="mkoenig")
    assert report.registry.deleted
    assert not registry.exists()
    assert "Registry file deleted." in (tmp_path / "migration.md").read_text()


def test_the_registry_stays_while_a_study_is_unreleased(tmp_path, sf_vocabulary):
    v1_full_example(tmp_path)
    registry = tmp_path / "studies" / "study_identifiers.json"
    registry.write_text(
        json.dumps(
            {
                "PKDB00042": ["caffeine/Example", "2020-01-02"],
                "PKDB00043": ["caffeine/Missing", "2020-01-02"],
            }
        )
    )
    dry = go(
        tmp_path, sf_vocabulary, registry=registry, approver="mkoenig", dry_run=True
    )
    report = go(tmp_path, sf_vocabulary, registry=registry, approver="mkoenig")
    assert (dry.registry.deleted, report.registry.deleted) == (False, False)
    assert report.registry.missing_paths == ["caffeine/Missing"]
    assert registry.exists()


def test_a_substance_or_study_path_limits_the_run(tmp_path, sf_vocabulary):
    v1_full_example(tmp_path)
    other = v1_study(tmp_path, STUDY, SHEETS, (), substance="codeine")
    empty = tmp_path / "studies" / "codeine" / "Empty2002"
    empty.mkdir()
    substance = tmp_path / "studies" / "caffeine"
    report = go(tmp_path, sf_vocabulary, dry_run=True, paths=[substance])
    assert ([s.study for s in report.studies], report.removed_empty) == (
        ["caffeine/Example"],
        [],
    )
    report = go(tmp_path, sf_vocabulary, dry_run=True, paths=[other, other])
    assert [s.study for s in report.studies] == ["codeine/Example"]


def test_two_jobs_convert_studies_in_parallel(tmp_path, sf_vocabulary):
    two_studies(tmp_path)
    report = go(tmp_path, sf_vocabulary, jobs=2)
    assert [(s.study, s.outcome, s.written) for s in report.studies] == [
        ("caffeine/Example", "identical", True),
        ("codeine/Example", "identical", True),
    ]


def test_a_stopped_worker_process_does_not_stop_the_run(
    tmp_path, sf_vocabulary, monkeypatch
):
    two_studies(tmp_path)
    folder = tmp_path / "studies" / "caffeine" / "Example"
    before = sorted(p.name for p in folder.iterdir())
    removed = []
    remove = run_module._remove

    def recorded(path):
        removed.append(path)
        remove(path)

    monkeypatch.setattr(run_module, "_one", dying)
    monkeypatch.setattr(run_module, "_remove", recorded)
    report = go(tmp_path, sf_vocabulary, jobs=2)
    assert [(s.study, s.outcome, s.reason, s.written) for s in report.studies] == [
        ("caffeine/Example", "not_converted", run_module.STOPPED, False),
        ("codeine/Example", "identical", None, True),
    ]
    assert sorted(p.name for p in folder.iterdir()) == before
    assert tmp_path / ".pkdb-migrate" / "new" / "caffeine" / "Example" in removed
    assert not (tmp_path / ".pkdb-migrate").exists()
    written = json.loads((tmp_path / "migration.json").read_text())
    assert [s["study"] for s in written["studies"]] == [
        "caffeine/Example",
        "codeine/Example",
    ]


def test_paths_outside_a_studies_folder_are_refused(tmp_path, sf_vocabulary):
    with pytest.raises(ValueError, match="studies"):
        migrate(
            [tmp_path],
            report=tmp_path / "r.json",
            registry=None,
            approver=None,
            jobs=1,
            vocabulary=sf_vocabulary,
        )


def test_the_repository_root_contains_the_studies_folder(tmp_path):
    study = tmp_path / "studies" / "caffeine" / "Example"
    study.mkdir(parents=True)
    assert run_module.repository_root(study) == tmp_path
    assert run_module.repository_root(tmp_path / "studies") == tmp_path
    with pytest.raises(ValueError, match="studies"):
        run_module.repository_root(tmp_path.parent)


def test_an_interrupted_run_writes_its_report(tmp_path, sf_vocabulary, monkeypatch):
    two_studies(tmp_path)
    interrupt_second_swap(monkeypatch)
    with pytest.raises(KeyboardInterrupt):
        go(tmp_path, sf_vocabulary)
    report = written_report(tmp_path)
    assert report.interrupted
    assert [(s.study, s.outcome, s.written) for s in report.studies] == [
        ("caffeine/Example", "identical", True)
    ]
    text = (tmp_path / "migration.md").read_text()
    assert text.startswith("# Study format 2 migration\n\nInterrupted. ")
    assert (tmp_path / "studies" / "codeine" / "Example" / "Example.xlsx").exists()


def test_a_rerun_carries_the_studies_that_earlier_runs_wrote_forward(
    tmp_path, sf_vocabulary, monkeypatch
):
    two_studies(tmp_path)
    interrupt_second_swap(monkeypatch)
    with pytest.raises(KeyboardInterrupt):
        go(tmp_path, sf_vocabulary)
    monkeypatch.undo()
    first = written_report(tmp_path).studies[0]
    report = go(tmp_path, sf_vocabulary)
    assert not report.interrupted and report.skipped == []
    assert [(s.study, s.outcome, s.written) for s in report.studies] == [
        ("caffeine/Example", "identical", True),
        ("codeine/Example", "identical", True),
    ]
    assert report.studies[0] == first
    assert written_report(tmp_path) == report
    # A run over one substance keeps the results of the others.
    v1_full_example(tmp_path / "third")
    (tmp_path / "third" / "studies" / "caffeine").rename(
        tmp_path / "studies" / "morphine"
    )
    report = go(tmp_path, sf_vocabulary, paths=[tmp_path / "studies" / "morphine"])
    assert [(s.study, s.written) for s in report.studies] == [
        ("caffeine/Example", True),
        ("codeine/Example", True),
        ("morphine/Example", True),
    ]


def test_results_that_were_not_written_are_not_carried_forward(tmp_path, sf_vocabulary):
    v1_full_example(tmp_path)
    go(tmp_path, sf_vocabulary, dry_run=True)
    report = go(tmp_path, sf_vocabulary, dry_run=True)
    assert [(s.study, s.written) for s in report.studies] == [
        ("caffeine/Example", False)
    ]


def test_an_unreadable_earlier_report_is_replaced_with_a_warning(
    tmp_path, sf_vocabulary
):
    v1_full_example(tmp_path)
    (tmp_path / "migration.json").write_text("{", encoding="utf-8")
    report = go(tmp_path, sf_vocabulary, dry_run=True)
    assert report.warnings == [
        "The earlier report migration.json could not be read, "
        "so this report lists only this run."
    ]
    assert [s.study for s in written_report(tmp_path).studies] == ["caffeine/Example"]
    text = (tmp_path / "migration.md").read_text()
    assert "\nWarning: The earlier report migration.json could not be read" in text


def test_the_report_warns_while_it_holds_studies_of_another_vocabulary(
    tmp_path, sf_vocabulary
):
    two_studies(tmp_path)
    v1_full_example(tmp_path / "third")
    (tmp_path / "third" / "studies" / "caffeine").rename(
        tmp_path / "studies" / "morphine"
    )
    first = vocabulary_hash(sf_vocabulary)
    report = go(tmp_path, sf_vocabulary, paths=[tmp_path / "studies" / "caffeine"])
    assert report.vocabulary == VocabularyUsed(version="studyformat-test", hash=first)
    assert [(s.study, s.vocabulary) for s in report.studies] == [
        ("caffeine/Example", first)
    ]
    assert report.warnings == []
    other = sf_vocabulary.model_copy(update={"version": "other"})
    warning = (
        f"1 written study was converted with the vocabulary sha256 {first}, "
        "not with the vocabulary of this run."
    )
    # The warning stays while the report holds the study of the first vocabulary.
    for substance in ("codeine", "morphine"):
        report = go(tmp_path, other, paths=[tmp_path / "studies" / substance])
        assert report.warnings == [warning]
        assert written_report(tmp_path).warnings == [warning]
    assert [(s.study, s.vocabulary) for s in report.studies] == [
        ("caffeine/Example", first),
        ("codeine/Example", vocabulary_hash(other)),
        ("morphine/Example", vocabulary_hash(other)),
    ]
    text = (tmp_path / "migration.md").read_text()
    assert f"\nWarning: {warning}\n" in text
    assert f"\nVocabulary: other (sha256 {vocabulary_hash(other)}).\n" in text


def test_a_refused_path_leaves_the_report_as_it_was(tmp_path, sf_vocabulary):
    v1_full_example(tmp_path)
    go(tmp_path, sf_vocabulary)
    before = tree(tmp_path)
    with pytest.raises(ValueError, match="is not a folder"):
        go(tmp_path, sf_vocabulary, paths=[tmp_path / "studies" / "caffeine" / "Gone"])
    assert tree(tmp_path) == before
