import json

import pytest
from check_fixtures import study_checkout

from pkdb.cli import main


@pytest.fixture
def checkout(tmp_path, valid_files):
    """Build a git checkout with one commit of format 2 and format 1 studies."""

    def build(*locations, format_1=()):
        return study_checkout(
            tmp_path / "data", valid_files, *locations, format_1=format_1
        )

    return build


@pytest.fixture
def vocabulary_file(tmp_path_factory, sf_vocabulary):
    """The vocabulary of the test studies as a snapshot file outside the checkout."""
    path = tmp_path_factory.mktemp("vocabulary") / "vocabulary.json"
    sf_vocabulary.save(path)
    return str(path)


@pytest.fixture
def run(capsys, monkeypatch, vocabulary_file):
    """Run pkdb check, from the folder `cwd` when given: the exit code, stdout and stderr."""

    def call(*args, cwd=None):
        if cwd is not None:
            monkeypatch.chdir(cwd)
        argv = ["--no-update", "check", "--vocabulary", vocabulary_file, *args]
        code = main(argv)
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    return call


def test_clean_checkout_exits_0_with_the_summary(checkout, run):
    root, _ = checkout("caffeine/A", "caffeine/B", format_1=["codeine/C"])
    code, out, _ = run("--format", "human", cwd=root)
    assert code == 0
    assert out.strip() == (
        "Checked 2 format 2 studies, skipped 1 format 1 studies: 0 errors, 0 warnings."
    )


def test_not_canonical_study_exits_1_and_names_the_file(checkout, run):
    root, studies = checkout("caffeine/A")
    table = studies["caffeine/A"] / "subjects.tsv"
    table.write_bytes(table.read_bytes().replace(b"\n", b"\r\n"))
    code, out, _ = run("--format", "human", cwd=root)
    assert code == 1
    assert "caffeine/A subjects.tsv" in out
    assert "not_canonical" in out
    assert " 1 errors" in out.splitlines()[-1]


def test_staged_with_nothing_staged_checks_nothing(checkout, run):
    root, _ = checkout("caffeine/A")
    code, out, _ = run("--staged", "--format", "human", cwd=root)
    assert code == 0
    assert out.startswith("Checked 0 format 2 studies, skipped 0 format 1 studies")


def test_staged_and_changed_exclude_each_other(checkout, run):
    root, _ = checkout("caffeine/A")
    with pytest.raises(SystemExit) as stop:
        run("--staged", "--changed", "x", cwd=root)
    assert stop.value.code == 2


def test_a_selection_mode_excludes_paths(checkout, run):
    root, _ = checkout("caffeine/A")
    code, _, err = run("--staged", "studies/caffeine/A", cwd=root)
    assert code == 2
    assert "not several" in err


def test_outside_a_git_repository_exits_2_naming_git(tmp_path, run):
    (tmp_path / "studies" / "caffeine" / "A").mkdir(parents=True)
    code, _, err = run("--staged", cwd=tmp_path)
    assert code == 2
    assert "git" in err.lower()


def test_no_checkout_exits_2(tmp_path, run):
    code, _, err = run(cwd=tmp_path)
    assert code == 2
    assert "studies" in err


def test_unknown_base_exits_2(checkout, run):
    root, _ = checkout("caffeine/A")
    code, _, err = run("--changed", "nope", cwd=root)
    assert code == 2
    assert err.strip()


def test_json_output_parses(checkout, run):
    root, _ = checkout("caffeine/A", format_1=["codeine/C"])
    code, out, _ = run("--format", "json", cwd=root)
    data = json.loads(out)
    assert code == 0
    assert data["checked"] == ["caffeine/A"]
    assert data["format_1"] == 1
    assert data["problems"] == []


def test_root_and_paths_select_studies(checkout, run):
    root, _ = checkout("caffeine/A", "caffeine/B")
    code, out, _ = run(
        "--root", str(root), "--format", "json", str(root / "studies/caffeine/B")
    )
    assert code == 0
    assert json.loads(out)["checked"] == ["caffeine/B"]
