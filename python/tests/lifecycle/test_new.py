import hashlib
import json
from pathlib import Path
from typing import Any

import httpx2
import pytest

from pkdb.cli import main
from pkdb.identity import Author
from pkdb.lifecycle.new import NewStudyRefused, create_study
from pkdb.references import ReferenceResolver
from pkdb.schemas.provenance import AutomaticCuration
from pkdb.schemas.validation import ValidationIssue
from pkdb.studyformat.formatter import FormatResult, format_folder
from pkdb.studyformat.metadata import read_metadata
from pkdb.studyformat.review_edit import read_review
from pkdb.studyformat.validation import is_v2_folder

PUBMED = """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID>
<Article><Journal><Title>Test journal</Title><JournalIssue><PubDate><Year>2020</Year></PubDate></JournalIssue></Journal>
<ArticleTitle>Caffeine in healthy volunteers</ArticleTitle>
<AuthorList><Author><ForeName>Ada</ForeName><LastName>Smith</LastName></Author></AuthorList></Article>
</MedlineCitation></PubmedArticle></PubmedArticleSet>"""
CSL = {
    "DOI": "10.1234/example",
    "title": "Caffeine by DOI",
    "container-title": "Journal",
    "issued": {"date-parts": [[2021]]},
    "author": [{"family": "Jones", "given": "Bo"}],
}
NEW = ["new", "caffeine/Smith2020", "--pmid", "123", "--user", "ana", "--no-issue"]
OPTIONS = ["--licence", "open", "--access", "private", "--offline"]


@pytest.fixture
def checkout(tmp_path):
    (tmp_path / "studies").mkdir()
    return tmp_path


@pytest.fixture
def resolver(monkeypatch):
    """An offline resolver whose cache, the default one of the test, knows PMID 123 and a DOI."""
    monkeypatch.setattr("pkdb.references.time.sleep", lambda _: None)

    def respond(request):
        if request.url.host == "doi.org":
            return httpx2.Response(200, json=CSL)
        return httpx2.Response(200, text=PUBMED)

    with httpx2.Client(transport=httpx2.MockTransport(respond)) as client:
        online = ReferenceResolver(client=client)
        online.pubmed("123")
        online.doi("10.1234/example")
    return ReferenceResolver(offline=True)


def new(checkout, resolver, location="caffeine/Smith2020", **options):
    arguments: dict[str, Any] = {
        "pmid": "123",
        "doi": None,
        "licence": "open",
        "access": "private",
        "author": Author("ana"),
        **options,
    }
    return create_study(checkout, location, resolver=resolver, **arguments)


def papers(checkout, *names, content=None):
    """The paper folder of caffeine/Smith2020 with files whose content is their name."""
    folder = checkout / "papers" / "caffeine" / "Smith2020"
    folder.mkdir(parents=True)
    for name in names:
        (folder / name).write_bytes(name.encode() if content is None else content)
    return folder


def files(folder):
    """Every file and folder below `folder` with the content of the files."""
    return {
        path.relative_to(folder): path.read_bytes() if path.is_file() else None
        for path in folder.rglob("*")
    }


def assert_nothing_written(checkout):
    assert not (checkout / "studies" / "caffeine").exists()
    assert not list((checkout / "studies").rglob(".*.new"))


def test_a_new_study_is_a_valid_draft(checkout, resolver):
    result = create_study(
        checkout,
        "caffeine/Smith2020",
        pmid="123",
        doi=None,
        licence="open",
        access="private",
        author=Author("ana"),
        resolver=resolver,
    )
    folder = checkout / "studies" / "caffeine" / "Smith2020"
    assert result.folder == folder and is_v2_folder(folder)
    metadata = read_metadata(folder).metadata
    assert metadata.reference is not None
    assert (
        metadata.creator,
        metadata.licence,
        metadata.access,
        metadata.reference.pmid,
    ) == ("ana", "open", "private", "123")
    assert metadata.provenance.kind == "manual_curation" and metadata.issue is None
    assert metadata.curators == []
    assert read_review(folder).review.status == "draft"
    assert (folder / "subjects.tsv").read_text(encoding="utf-8") == (
        "study\tname\tparent\tcount\tsource\tcomment\nSmith2020\tall\t\t\t\t\n"
    )
    reference = json.loads((folder / "reference.json").read_text(encoding="utf-8"))
    assert (reference["sid"], reference["name"]) == ("123", "Smith2020")
    assert reference["title"] == "Caffeine in healthy volunteers"
    assert result.reference == "Created reference.json from PubMed 123"
    assert (result.moved, result.left) == ([], [])
    assert not list((checkout / "studies" / "caffeine").glob(".*"))
    assert not format_folder(folder, check=True).changes


def test_a_study_of_a_doi(checkout, resolver):
    result = new(checkout, resolver, pmid=None, doi="10.1234/example")
    metadata = read_metadata(result.folder).metadata
    assert metadata.reference is not None
    assert (metadata.reference.pmid, metadata.reference.doi) == (
        None,
        "10.1234/example",
    )
    assert result.reference == "Created reference.json from DOI 10.1234/example"


def test_papers_move_into_the_study(checkout, resolver):
    paper = papers(
        checkout,
        "Smith2020.pdf",
        "Smith2020_Tab1.png",
        "Smith2020_notes.png",
        "Smith2020.xlsx",
    )
    result = create_study(
        checkout,
        "caffeine/Smith2020",
        pmid="123",
        doi=None,
        licence="open",
        access="private",
        author=Author("ana"),
        resolver=resolver,
    )
    assert sorted(result.moved) == ["Smith2020.pdf", "Smith2020_Tab1.png"]
    assert sorted(result.left) == ["Smith2020.xlsx", "Smith2020_notes.png"]
    assert (result.folder / "Smith2020_Tab1.png").exists()
    assert not (paper / "Smith2020.pdf").exists()
    assert sorted(path.name for path in paper.iterdir()) == result.left
    for name in result.moved:
        assert (result.folder / name).read_bytes() == name.encode()
    assert (result.misnamed, result.warnings) == ({}, [])


def test_paper_files_that_differ_only_in_case_stay(checkout, resolver):
    paper = papers(
        checkout,
        "Smith2020.PDF",
        "smith2020_tab1.png",
        "Smith2020_Fig1.PNG",
        "Smith2020_text.png",
        "Smith2020_notes.PNG",
    )
    result = new(checkout, resolver)
    assert result.moved == []
    assert sorted(result.left) == sorted(path.name for path in paper.iterdir())
    assert result.misnamed == {
        "Smith2020.PDF": "Smith2020.pdf",
        "smith2020_tab1.png": "Smith2020_Tab1.png",
        "Smith2020_Fig1.PNG": "Smith2020_Fig1.png",
        "Smith2020_text.png": "Smith2020_Text.png",
    }


def test_a_paper_file_that_cannot_be_removed_is_a_warning(
    checkout, resolver, monkeypatch
):
    paper = papers(checkout, "Smith2020.pdf", "Smith2020_Tab1.png")
    unlink = Path.unlink

    def refuse(path, missing_ok=False):
        if path.parent == paper and path.name == "Smith2020.pdf":
            raise PermissionError(13, "Permission denied")
        unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", refuse)
    result = new(checkout, resolver)
    assert is_v2_folder(result.folder)
    assert result.moved == ["Smith2020.pdf", "Smith2020_Tab1.png"]
    assert result.warnings == [
        "Smith2020.pdf is in the study but stays in papers/caffeine/Smith2020: "
        "Permission denied. Remove it by hand."
    ]
    assert sorted(path.name for path in paper.iterdir()) == ["Smith2020.pdf"]
    assert not list((checkout / "studies").rglob(".*.new"))


def test_an_emptied_paper_folder_is_removed(checkout, resolver):
    papers(checkout, "Smith2020.pdf", "Smith2020_Fig2A.png", "Smith2020_Text.png")
    (checkout / "papers" / "codeine" / "Other").mkdir(parents=True)
    result = new(checkout, resolver)
    assert sorted(result.moved) == [
        "Smith2020.pdf",
        "Smith2020_Fig2A.png",
        "Smith2020_Text.png",
    ]
    assert not (checkout / "papers" / "caffeine").exists()
    assert (checkout / "papers" / "codeine" / "Other").is_dir()


def test_an_agent_records_an_automatic_curation(checkout, resolver):
    paper = checkout / "papers" / "caffeine" / "Smith2020"
    paper.mkdir(parents=True)
    (paper / "Smith2020.pdf").write_bytes(b"%PDF")
    result = create_study(
        checkout,
        "caffeine/Smith2020",
        pmid="123",
        doi=None,
        licence="closed",
        access="private",
        author=Author("ana", agent="claude"),
        resolver=resolver,
        agent_version="5.5",
        run_id="run-1",
    )
    metadata = read_metadata(result.folder).metadata
    provenance = metadata.provenance
    assert isinstance(provenance, AutomaticCuration)
    assert (
        provenance.source_key,
        provenance.method,
        provenance.version,
        provenance.run_id,
    ) == ("pkdb.ai", "claude", "5.5", "run-1")
    assert provenance.assets[0].url == "Smith2020.pdf"
    assert provenance.assets[0].sha256 == hashlib.sha256(b"%PDF").hexdigest()
    assert metadata.creator == "ana"


def test_an_agent_names_every_asset(checkout, resolver, tmp_path):
    papers(checkout, "Smith2020.pdf", content=b"%PDF")
    supplement = tmp_path / "supplement.pdf"
    supplement.write_bytes(b"more")
    result = new(
        checkout,
        resolver,
        author=Author("ana", agent="claude"),
        agent_version="5.5",
        run_id="run-1",
        assets=[supplement],
    )
    provenance = read_metadata(result.folder).metadata.provenance
    assert isinstance(provenance, AutomaticCuration)
    assert [(asset.url, asset.sha256) for asset in provenance.assets] == [
        ("Smith2020.pdf", hashlib.sha256(b"%PDF").hexdigest()),
        ("supplement.pdf", hashlib.sha256(b"more").hexdigest()),
    ]
    assert supplement.exists() and not (result.folder / "supplement.pdf").exists()


def test_an_agent_without_a_pdf_may_name_an_asset(checkout, resolver, tmp_path):
    asset = tmp_path / "paper.pdf"
    asset.write_bytes(b"%PDF")
    result = new(
        checkout,
        resolver,
        author=Author("ana", agent="claude"),
        agent_version="5.5",
        run_id="run-1",
        assets=[asset],
    )
    provenance = read_metadata(result.folder).metadata.provenance
    assert isinstance(provenance, AutomaticCuration)
    assert [asset.url for asset in provenance.assets] == ["paper.pdf"]


@pytest.mark.parametrize(
    "options, message",
    [
        ({"pmid": "123", "doi": "10.1000/x"}, "PubMed ID or a DOI"),
        ({"pmid": None, "doi": None}, "PubMed ID or a DOI"),
        (
            {"pmid": "123", "doi": None, "author": Author("ana", agent="claude")},
            "--agent-version",
        ),
        (
            {
                "pmid": "123",
                "doi": None,
                "author": Author("ana", agent="claude"),
                "agent_version": "5.5",
                "run_id": "run-1",
            },
            "An automatic curation names what it read: put Smith2020.pdf into "
            "papers/caffeine/Smith2020/ or pass --asset FILE",
        ),
        ({"pmid": "123", "doi": None, "agent_version": "5.5"}, "pass --agent"),
        ({"pmid": "123", "doi": None, "assets": [Path("a.pdf")]}, "pass --agent"),
        ({"pmid": "0123", "doi": None}, "reference.pmid"),
        ({"pmid": "123", "doi": None, "licence": "free"}, "licence"),
        ({"pmid": "123", "doi": None, "access": "everyone"}, "access"),
        ({"pmid": "999", "doi": None}, "No cached pubmed metadata for 999"),
        (
            {"pmid": None, "doi": "10.1234/missing"},
            "No cached doi metadata for 10.1234/missing",
        ),
    ],
)
def test_refusals_write_nothing(checkout, resolver, options, message):
    arguments: dict[str, Any] = {
        "licence": "open",
        "access": "private",
        "author": Author("ana"),
        **options,
    }
    with pytest.raises(NewStudyRefused, match=message):
        create_study(checkout, "caffeine/Smith2020", resolver=resolver, **arguments)
    assert not (checkout / "studies" / "caffeine" / "Smith2020").exists()
    assert not list((checkout / "studies").rglob(".*.new"))
    assert not (checkout / "studies" / "caffeine").exists()


@pytest.mark.parametrize(
    "location, message",
    [
        ("caffeine", "is not <substance>/<name>"),
        ("caffeine/Smith 2020", "must use letters"),
        ("caffeine/publication", "reserved"),
    ],
)
def test_invalid_names_are_refused(checkout, resolver, location, message):
    with pytest.raises(NewStudyRefused, match=message):
        new(checkout, resolver, location=location)
    assert_nothing_written(checkout)


def test_an_asset_must_be_a_file(checkout, resolver, tmp_path):
    with pytest.raises(NewStudyRefused, match="missing.pdf is not a file"):
        new(
            checkout,
            resolver,
            author=Author("ana", agent="claude"),
            agent_version="5.5",
            run_id="run-1",
            assets=[tmp_path / "missing.pdf"],
        )
    assert_nothing_written(checkout)


def test_a_public_study_is_refused(checkout, resolver):
    papers(checkout, "Smith2020.pdf")
    before = files(checkout / "papers")
    with pytest.raises(NewStudyRefused) as refused:
        new(checkout, resolver, access="public")
    assert str(refused.value) == (
        "A new study is private until its release; create it with --access private "
        "and set access to public when you release it."
    )
    assert files(checkout / "papers") == before
    assert_nothing_written(checkout)


def test_an_agent_is_told_about_a_pdf_that_differs_in_case(checkout, resolver):
    papers(checkout, "Smith2020.PDF")
    with pytest.raises(NewStudyRefused) as refused:
        new(
            checkout,
            resolver,
            author=Author("ana", agent="claude"),
            agent_version="5.5",
            run_id="run-1",
        )
    assert str(refused.value) == (
        "An automatic curation names what it read: rename "
        "papers/caffeine/Smith2020/Smith2020.PDF to Smith2020.pdf or pass --asset FILE"
    )
    assert_nothing_written(checkout)


def test_a_refused_reference_leaves_the_papers(checkout, resolver):
    paper = papers(checkout, "Smith2020.pdf", "Smith2020_Tab1.png")
    before = files(checkout / "papers")
    with pytest.raises(NewStudyRefused, match="Cannot create reference.json"):
        new(checkout, resolver, pmid="999")
    assert files(checkout / "papers") == before and paper.is_dir()
    assert_nothing_written(checkout)


def test_an_unformattable_folder_is_refused(checkout, resolver, monkeypatch):
    def broken(folder):
        issue = ValidationIssue(code="invalid_json", message="subjects.tsv is broken")
        return FormatResult(folder, issues=[issue])

    monkeypatch.setattr("pkdb.lifecycle.new.format_folder", broken)
    with pytest.raises(NewStudyRefused, match="subjects.tsv is broken"):
        new(checkout, resolver)
    assert_nothing_written(checkout)


def test_a_crash_leaves_no_partial_study(checkout, resolver, monkeypatch):
    before = files(papers(checkout, "Smith2020.pdf").parent.parent)

    def crash(folder):
        raise KeyboardInterrupt

    monkeypatch.setattr("pkdb.lifecycle.new.format_folder", crash)
    with pytest.raises(KeyboardInterrupt):
        new(checkout, resolver)
    assert files(checkout / "papers") == before
    assert_nothing_written(checkout)


def test_an_existing_substance_folder_stays_after_a_refusal(checkout, resolver):
    released = checkout / "studies" / "caffeine" / "Other"
    released.mkdir(parents=True)
    with pytest.raises(NewStudyRefused):
        new(checkout, resolver, pmid="999")
    assert sorted(path.name for path in released.parent.iterdir()) == ["Other"]


def test_an_existing_study_is_refused(checkout, resolver):
    create_study(
        checkout,
        "caffeine/Smith2020",
        pmid="123",
        doi=None,
        licence="open",
        access="private",
        author=Author("ana"),
        resolver=resolver,
    )
    with pytest.raises(NewStudyRefused, match="exists"):
        create_study(
            checkout,
            "caffeine/Smith2020",
            pmid="123",
            doi=None,
            licence="open",
            access="private",
            author=Author("ana"),
            resolver=resolver,
        )


@pytest.mark.parametrize(
    "location, message",
    [
        (
            "Caffeine/Smith2020",
            "studies/Caffeine differs from studies/caffeine only in case",
        ),
        (
            "caffeine/smith2020",
            "studies/caffeine/smith2020 differs from studies/caffeine/Smith2020 only in case",
        ),
    ],
)
def test_a_name_that_differs_only_in_case_is_refused(
    checkout, resolver, location, message
):
    (checkout / "studies" / "caffeine" / "Smith2020").mkdir(parents=True)
    with pytest.raises(NewStudyRefused, match=message):
        new(checkout, resolver, location=location)
    assert sorted(path.name for path in (checkout / "studies").iterdir()) == [
        "caffeine"
    ]


def test_a_leftover_of_an_interrupted_run_is_refused(checkout, resolver):
    leftover = checkout / "studies" / "caffeine" / ".Smith2020.new" / "Smith2020"
    leftover.mkdir(parents=True)
    (leftover / "study.json").write_text("{}", encoding="utf-8")
    with pytest.raises(NewStudyRefused) as refused:
        new(checkout, resolver)
    assert str(refused.value) == (
        "studies/caffeine/.Smith2020.new exists: another pkdb new of "
        "caffeine/Smith2020 may be running, or one was interrupted. Remove the "
        "folder only when no pkdb new is running."
    )
    assert (leftover / "study.json").exists()
    assert not (checkout / "studies" / "caffeine" / "Smith2020").exists()


def test_new_command(checkout, resolver, monkeypatch, capsys):
    monkeypatch.chdir(checkout / "studies")
    assert main([*NEW, *OPTIONS, "--format", "json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output == {
        "location": "caffeine/Smith2020",
        "path": str(checkout / "studies" / "caffeine" / "Smith2020"),
        "moved": [],
        "left": [],
        "misnamed": {},
        "reference": "Created reference.json from PubMed 123",
        "paper": "Smith (2020) Caffeine in healthy volunteers",
        "warnings": [],
    }
    assert is_v2_folder(checkout / "studies" / "caffeine" / "Smith2020")


def test_new_command_names_moved_and_left_files(
    checkout, resolver, monkeypatch, capsys
):
    papers(checkout, "Smith2020.PDF", "Smith2020_Tab1.png", "Smith2020.xlsx")
    monkeypatch.chdir(checkout)
    assert main([*NEW, *OPTIONS, "--format", "human"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "Created studies/caffeine/Smith2020",
        "Moved from papers/caffeine/Smith2020: Smith2020_Tab1.png",
        "Left in papers/caffeine/Smith2020: Smith2020.PDF (differs only in case "
        "from Smith2020.pdf), Smith2020.xlsx",
        "Created reference.json from PubMed 123",
        "Paper: Smith (2020) Caffeine in healthy volunteers",
    ]


def test_new_command_warns_about_files_left_in_papers(
    checkout, resolver, monkeypatch, capsys
):
    paper = papers(checkout, "Smith2020.pdf")
    unlink = Path.unlink

    def refuse(path, missing_ok=False):
        if path.parent == paper:
            raise PermissionError(13, "Permission denied")
        unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", refuse)
    monkeypatch.chdir(checkout)
    assert main([*NEW, *OPTIONS, "--format", "human"]) == 0
    output = capsys.readouterr()
    assert output.out.splitlines()[0] == "Created studies/caffeine/Smith2020"
    assert output.err == (
        "Warning: Smith2020.pdf is in the study but stays in papers/caffeine/Smith2020: "
        "Permission denied. Remove it by hand.\n"
    )


def test_new_command_with_an_agent(checkout, resolver, monkeypatch, tmp_path):
    asset = tmp_path / "paper.pdf"
    asset.write_bytes(b"%PDF")
    agent = ["--agent", "claude", "--agent-version", "5.5", "--run-id", "run-1"]
    assets = ["--asset", str(asset)]
    arguments = [*NEW, *OPTIONS, *agent, *assets, "--root", str(checkout)]
    assert main([*arguments, "--format", "json"]) == 0
    folder = checkout / "studies" / "caffeine" / "Smith2020"
    provenance = read_metadata(folder).metadata.provenance
    assert isinstance(provenance, AutomaticCuration)
    assert (provenance.method, provenance.run_id) == ("claude", "run-1")


def test_new_command_refusals_exit_1(checkout, resolver, monkeypatch, capsys):
    monkeypatch.chdir(checkout)
    assert main([*NEW, *OPTIONS, "--format", "json"]) == 0
    capsys.readouterr()
    assert main([*NEW, *OPTIONS, "--format", "json"]) == 1
    assert json.loads(capsys.readouterr().out) == {
        "location": "caffeine/Smith2020",
        "error": "studies/caffeine/Smith2020 exists already",
    }
    assert main([*NEW, *OPTIONS, "--format", "human"]) == 1
    assert capsys.readouterr().err == "studies/caffeine/Smith2020 exists already\n"
    public = [NEW[0], "caffeine/Jones2021", *NEW[2:]]
    public += ["--licence", "open", "--access", "public", "--offline"]
    assert main([*public, "--format", "human"]) == 1
    assert "private until its release" in capsys.readouterr().err
    assert not (checkout / "studies" / "caffeine" / "Jones2021").exists()


def test_new_command_usage_errors_exit_2(checkout, resolver, monkeypatch, capsys):
    monkeypatch.chdir(checkout)
    with pytest.raises(SystemExit) as exit:
        main([*NEW, "--access", "private", "--offline"])
    assert exit.value.code == 2
    with pytest.raises(SystemExit) as exit:
        main([*NEW, *OPTIONS, "--doi", "10.1234/example"])
    assert exit.value.code == 2
    capsys.readouterr()
    no_user = [arg for arg in NEW if arg not in ("--user", "ana")]
    assert main([*no_user, *OPTIONS]) == 2
    assert "PK-DB user name is required" in capsys.readouterr().err
    monkeypatch.chdir(checkout.parent)
    assert main([*NEW, *OPTIONS]) == 2
    assert "studies folder" in capsys.readouterr().err
    assert not (checkout / "studies" / "caffeine").exists()


WITH_ISSUE = [arg for arg in NEW if arg != "--no-issue"]


@pytest.fixture
def github(monkeypatch):
    from fake_github import FakeGitHub

    fake = FakeGitHub()
    monkeypatch.setattr(
        "pkdb.lifecycle_cli.github_client", lambda repository, token: fake.client()
    )
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    return fake


def test_new_records_the_issue(checkout, resolver, github, monkeypatch, capsys):
    monkeypatch.chdir(checkout)
    assert main([*WITH_ISSUE, *OPTIONS, "--format", "human"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "Issue #1 (created)"
    folder = checkout / "studies" / "caffeine" / "Smith2020"
    assert read_metadata(folder).metadata.issue == 1
    assert github.issues[1]["title"] == "caffeine/Smith2020"


def test_new_adopts_an_existing_issue(checkout, resolver, github, monkeypatch, capsys):
    github.issues[7] = {
        "number": 7,
        "title": "caffeine/Smith2020",
        "state": "open",
        "state_reason": None,
        "labels": [],
        "assignees": [],
    }
    monkeypatch.chdir(checkout)
    assert main([*WITH_ISSUE, *OPTIONS, "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["issue"] == 7
    assert github.writes == []


def test_new_needs_a_token_unless_no_issue(checkout, resolver, monkeypatch, capsys):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.chdir(checkout)
    assert main([*WITH_ISSUE, *OPTIONS]) == 2
    assert "Set GH_TOKEN or GITHUB_TOKEN, or pass --no-issue" in capsys.readouterr().err
    assert not (checkout / "studies" / "caffeine").exists()
    assert main([*NEW, *OPTIONS]) == 0


def test_a_github_failure_after_writing_keeps_the_folder(
    checkout, resolver, github, monkeypatch, capsys
):
    github.fail[("POST", None)] = 500
    monkeypatch.chdir(checkout)
    assert main([*WITH_ISSUE, *OPTIONS, "--format", "human"]) == 1
    assert "pkdb issues sync --adopt" in capsys.readouterr().err
    folder = checkout / "studies" / "caffeine" / "Smith2020"
    assert is_v2_folder(folder)
    assert read_metadata(folder).metadata.issue is None
    assert main([*WITH_ISSUE, *OPTIONS, "--format", "human"]) == 1
    assert "exists" in capsys.readouterr().err


def test_new_does_not_adopt_an_issue_of_another_study(
    checkout, resolver, github, monkeypatch, capsys
):
    monkeypatch.chdir(checkout)
    assert main([*WITH_ISSUE, *OPTIONS]) == 0
    github.issues[1]["title"] = "caffeine/Brown2022"
    brown = ["new", "caffeine/Brown2022", *WITH_ISSUE[2:]]
    capsys.readouterr()
    assert main([*brown, *OPTIONS, "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["issue"] == 2
    smith = checkout / "studies" / "caffeine" / "Smith2020"
    assert read_metadata(smith).metadata.issue == 1


def test_a_closed_adopted_issue_is_named(
    checkout, resolver, github, monkeypatch, capsys
):
    github.issues[7] = {
        "number": 7,
        "title": "caffeine/Smith2020",
        "state": "closed",
        "state_reason": "completed",
        "labels": [],
        "assignees": [],
    }
    monkeypatch.chdir(checkout)
    assert main([*WITH_ISSUE, *OPTIONS, "--format", "human"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "Issue #7 (adopted, closed)"


def test_a_bad_token_writes_nothing(checkout, resolver, monkeypatch, capsys):
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "bad token")
    monkeypatch.chdir(checkout)
    assert main([*WITH_ISSUE, *OPTIONS]) == 2
    assert "whitespace" in capsys.readouterr().err
    assert not (checkout / "studies" / "caffeine").exists()
