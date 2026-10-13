"""A change of documentation only skips the test jobs of continuous integration."""

import importlib.util
from pathlib import Path

import pytest
from check_fixtures import git

spec = importlib.util.spec_from_file_location(
    "ci_changes", Path(__file__).resolve().parents[2] / "scripts/ci_changes.py"
)
assert spec is not None and spec.loader is not None
changes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(changes)


@pytest.mark.parametrize(
    ("path", "docs"),
    [
        ("docs/installation.md", True),
        ("docs/images/curation/overview-light.png", True),
        ("release-notes/unreleased.md", True),
        ("README.md", True),
        ("CLAUDE.md", True),
        ("zensical.toml", True),
        # the client tests read it
        ("docs/study-format.md", False),
        ("python/README.md", False),
        ("backend/src/pkdb_server/app.py", False),
        ("frontend/src/main.ts", False),
        (".github/workflows/docs.yml", False),
        ("compose.test.yaml", False),
        ("docsx/index.md", False),
        ("CITATION.cff", False),
    ],
)
def test_docs_are_the_docs_folder_release_notes_and_markdown_at_the_root(path, docs):
    assert changes.is_docs(path) is docs


def test_a_change_is_code_unless_every_path_is_documentation():
    assert changes.code_changed(["docs/index.md", "README.md"]) is False
    assert changes.code_changed(["docs/index.md", "python/src/pkdb/cli.py"]) is True
    # nothing to judge is no reason to skip the tests
    assert changes.code_changed([]) is True


@pytest.fixture
def repository(tmp_path):
    """A clone whose main branch holds python/cli.py and docs/index.md."""
    git(tmp_path, "init", "-q")
    (tmp_path / "python").mkdir()
    (tmp_path / "python" / "cli.py").write_text("print('pkdb')\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "index.md").write_text("# PK-DB\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def merge_pull_request(repository: Path, change) -> None:
    """Check out the merge commit of a pull request that makes `change`, as CI does."""
    git(repository, "switch", "-q", "-c", "topic")
    change(repository)
    git(repository, "add", "--all")
    git(repository, "commit", "-q", "-m", "topic")
    git(repository, "switch", "-q", "main")
    git(repository, "merge", "-q", "--no-ff", "-m", "merge", "topic")


def edit_docs(root: Path) -> None:
    (root / "docs" / "index.md").write_text("# PK-DB, edited\n", encoding="utf-8")


def edit_code(root: Path) -> None:
    (root / "python" / "cli.py").write_text("print('PK-DB')\n", encoding="utf-8")


def test_a_pull_request_of_docs_only_skips_the_tests(repository):
    merge_pull_request(repository, edit_docs)
    assert changes.decide("pull_request", "refs/pull/1/merge", "", repository) is False


def test_a_pull_request_of_code_runs_the_tests(repository):
    merge_pull_request(repository, edit_code)
    assert changes.decide("pull_request", "refs/pull/1/merge", "", repository) is True


def test_a_file_moved_from_code_into_docs_is_a_change_of_code(repository):
    merge_pull_request(
        repository,
        lambda root: (root / "python" / "cli.py").rename(root / "docs" / "cli.py"),
    )
    assert changes.decide("pull_request", "refs/pull/1/merge", "", repository) is True


def test_a_push_is_compared_with_the_commit_before_it(repository):
    before = git(repository, "rev-parse", "HEAD").strip()
    edit_docs(repository)
    git(repository, "commit", "-q", "-am", "docs")
    assert changes.decide("push", "refs/heads/develop", before, repository) is False
    edit_code(repository)
    git(repository, "commit", "-q", "-am", "code")
    assert changes.decide("push", "refs/heads/develop", before, repository) is True


@pytest.mark.parametrize(
    ("event", "ref", "before"),
    [
        ("push", "refs/tags/v0.13.0", ""),
        ("workflow_dispatch", "refs/heads/develop", ""),
        # the first push of a branch has no commit before it
        ("push", "refs/heads/develop", "0" * 40),
        # a commit that the clone lacks and cannot fetch
        ("push", "refs/heads/develop", "1" * 40),
    ],
)
def test_releases_manual_runs_and_unknown_history_run_the_tests(
    repository, event, ref, before
):
    edit_docs(repository)
    git(repository, "commit", "-q", "-am", "docs")
    assert changes.decide(event, ref, before, repository) is True


def test_the_decision_is_printed_and_appended_to_the_output_file(
    repository, tmp_path_factory, monkeypatch, capsys
):
    output = tmp_path_factory.mktemp("github") / "output"
    output.write_text("earlier=1\n", encoding="utf-8")
    monkeypatch.chdir(repository)
    arguments = ["--event", "workflow_dispatch", "--ref", "refs/heads/develop"]
    assert changes.main([*arguments, "--output", str(output)]) == 0
    assert output.read_text(encoding="utf-8") == "earlier=1\ncode=true\n"
    assert capsys.readouterr().out == "code=true\n"
