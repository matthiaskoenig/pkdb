"""Resolving reference.json of study format 2 folders from study.json."""

import json

import httpx2
import pytest

from pkdb.cli import main
from pkdb.references import ReferenceError, ReferenceResolver, sync_reference
from pkdb.studyformat import validate_folder
from pkdb.studyformat.jsonio import dump_json

XML = """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>{pmid}</PMID>
<Article><Journal><Title>Test journal</Title><JournalIssue><PubDate><Year>2020</Year></PubDate></JournalIssue></Journal>
<ArticleTitle>Publication {pmid}</ArticleTitle>
<AuthorList><Author><ForeName>Ada</ForeName><LastName>Smith</LastName></Author></AuthorList></Article>
</MedlineCitation></PubmedArticle></PubmedArticleSet>"""
CSL = {
    "DOI": "10.1234/example",
    "title": "DOI title",
    "container-title": "Journal",
    "issued": {"date-parts": [[2020]]},
    "author": [{"literal": "Study Consortium"}],
}


@pytest.fixture(autouse=True)
def fast_requests(monkeypatch):
    monkeypatch.setattr("pkdb.references.time.sleep", lambda _: None)


def providers(calls):
    def respond(request):
        if request.url.host == "doi.org":
            calls.append(request.url.path)
            return httpx2.Response(200, json=CSL)
        if request.url.path.endswith("esearch.fcgi"):
            calls.append("esearch")
            return httpx2.Response(200, json={"esearchresult": {"idlist": []}})
        pmid = request.url.params["id"]
        calls.append(pmid)
        return httpx2.Response(200, text=XML.format(pmid=pmid))

    return respond


def client(calls):
    return httpx2.Client(transport=httpx2.MockTransport(providers(calls)))


def set_reference(folder, reference):
    path = folder / "study.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["reference"] = reference
    path.write_text(dump_json(data), encoding="utf-8", newline="")
    return path.read_bytes()


def reference_json(folder):
    return json.loads((folder / "reference.json").read_text(encoding="utf-8"))


def test_reference_mismatch_names_the_command_that_fixes_it(
    valid_study, sf_vocabulary, tmp_path, monkeypatch, capsys
):
    study_json = set_reference(valid_study, {"pmid": "456"})
    monkeypatch.chdir(tmp_path)
    issues = validate_folder(valid_study, sf_vocabulary).issues
    [issue] = [issue for issue in issues if issue.code == "reference_mismatch"]
    command = "pkdb reference resolve caffeine/Example --write"
    assert command in issue.message
    calls = []
    with client(calls) as http:
        args = [*command.split()[1:], "--cache-dir", str(tmp_path / "cache")]
        assert main(args, client=http) == 0
    assert json.loads(capsys.readouterr().out)["saved"]
    assert calls == ["456"]
    reference = reference_json(valid_study)
    assert (reference["sid"], reference["pmid"]) == ("456", "456")
    assert (reference["name"], reference["title"]) == ("Example", "Publication 456")
    assert (valid_study / "study.json").read_bytes() == study_json
    assert validate_folder(valid_study, sf_vocabulary).issues == []


def test_resolve_creates_reference_json_from_study_json(valid_study, tmp_path):
    (valid_study / "reference.json").unlink()
    study_json = (valid_study / "study.json").read_bytes()
    calls = []
    args = [
        "reference",
        "resolve",
        str(valid_study),
        "--write",
        "--cache-dir",
        str(tmp_path / "cache"),
    ]
    with client(calls) as http:
        assert main(args, client=http) == 0
    reference = reference_json(valid_study)
    assert (reference["sid"], reference["pmid"]) == ("123", "123")
    assert reference["name"] == "Example"
    assert (valid_study / "study.json").read_bytes() == study_json


def test_resolve_keeps_curator_corrections_of_the_same_publication(
    valid_study, tmp_path
):
    args = ["reference", "resolve", str(valid_study), "--cache-dir", str(tmp_path)]
    with client([]) as http:
        assert main([*args, "--title", "Corrected title", "--write"], client=http) == 0
        assert main([*args, "--write"], client=http) == 0
    assert reference_json(valid_study)["title"] == "Corrected title"


def test_doi_names_the_reference_of_a_study_without_pmid(valid_study, tmp_path):
    set_reference(valid_study, {"doi": "10.1234/Example"})
    calls = []
    args = ["reference", "resolve", str(valid_study), "--write"]
    with client(calls) as http:
        assert main([*args, "--cache-dir", str(tmp_path)], client=http) == 0
    assert calls == ["/10.1234/example", "esearch"]
    reference = reference_json(valid_study)
    assert (reference["sid"], reference["doi"]) == (
        "10.1234/example",
        "10.1234/example",
    )


def test_identifiers_other_than_those_of_study_json_are_rejected(
    valid_study, tmp_path, capsys
):
    before = (valid_study / "reference.json").read_bytes()
    args = ["reference", "resolve", str(valid_study), "--cache-dir", str(tmp_path)]
    for extra in (["--pmid", "456"], ["--doi", "10.1234/example"]):
        with client([]) as http:
            assert main([*args, *extra, "--write"], client=http) == 1
        assert "study.json" in json.loads(capsys.readouterr().err)["error"]
    with client([]) as http:
        assert main([*args, "--pmid", "123", "--write"], client=http) == 0
    assert reference_json(valid_study)["provenance"]["input"] == {"pmid": "123"}
    assert (valid_study / "reference.json").read_bytes() != before


def test_sync_reference_follows_study_json(valid_study, tmp_path):
    calls = []
    with client(calls) as http:
        resolver = ReferenceResolver(tmp_path, client=http)
        assert sync_reference(valid_study, resolver) is None
        set_reference(valid_study, {"pmid": "456"})
        change = sync_reference(valid_study, resolver)
        assert change is not None and "456" in change
        assert (reference_json(valid_study)["sid"]) == "456"
        assert sync_reference(valid_study, resolver) is None
        (valid_study / "reference.json").unlink()
        assert sync_reference(valid_study, resolver) == (
            "Created reference.json from PubMed 456"
        )
        set_reference(valid_study, None)
        assert sync_reference(valid_study, resolver) is None
    assert calls == ["456"]
    set_reference(valid_study, {"pmid": "789"})
    offline = ReferenceResolver(tmp_path, offline=True)
    with pytest.raises(ReferenceError, match="Cannot create reference.json"):
        sync_reference(valid_study, offline)


def test_reference_must_be_an_object_in_format_2(valid_study, tmp_path):
    set_reference(valid_study, "123")
    resolver = ReferenceResolver(tmp_path, offline=True)
    with pytest.raises(ReferenceError, match="pmid"):
        from pkdb.references import preview_reference

        preview_reference(valid_study, {}, resolver)
    assert sync_reference(valid_study, resolver) is None
