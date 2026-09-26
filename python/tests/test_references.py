"""Reference creation from provider fixtures through the real CLI and saved source."""

import json
from concurrent.futures import ThreadPoolExecutor

import httpx2
import pytest

from pkdb.cli import main
from pkdb.references import (
    ReferenceError,
    ReferenceResolver,
    normalize_doi,
    parse_pubmed,
    preview_reference,
    save_reference,
)

XML = """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID>
<DateCompleted><Year>2025</Year><Month>02</Month><Day>03</Day></DateCompleted>
<Article><Journal><Title>Test journal</Title><JournalIssue><PubDate><Year>2020</Year><Month>Mar</Month></PubDate></JournalIssue></Journal>
<ArticleTitle>A <i>nested</i> title</ArticleTitle><Abstract>
<AbstractText Label="METHODS">Some <b>important</b> text.</AbstractText>
<AbstractText Label="RESULTS">Second section.</AbstractText></Abstract>
<AuthorList><Author><ForeName>Ada</ForeName><LastName>Smith</LastName></Author>
<Author><CollectiveName>Study Consortium</CollectiveName></Author></AuthorList></Article>
</MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType="doi">10.1234/Example</ArticleId></ArticleIdList></PubmedData>
</PubmedArticle></PubmedArticleSet>"""
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


def transport(handler):
    return httpx2.Client(transport=httpx2.MockTransport(handler))


def test_cli_pmid_preview_save_and_offline_preparation(
    study_folder, vocabulary, tmp_path, capsys
):
    calls = []

    def respond(request):
        calls.append(request)
        assert request.url.params["id"] == "123"
        return httpx2.Response(200, text=XML)

    before = (study_folder / "reference.json").read_bytes()
    args = [
        "reference",
        "resolve",
        str(study_folder),
        "--pmid",
        "123",
        "--cache-dir",
        str(tmp_path / "cache"),
    ]
    with transport(respond) as client:
        assert main(args, client=client) == 0
    preview = json.loads(capsys.readouterr().out)
    assert not preview["saved"]
    assert (study_folder / "reference.json").read_bytes() == before
    reference = preview["reference"]
    assert reference["title"] == "A nested title"
    assert reference["publication_date"] == "2020-03"
    assert reference["date"] is None
    assert reference["doi"] == "10.1234/example"
    assert (
        reference["abstract"]
        == "METHODS: Some important text.\n\nRESULTS: Second section."
    )
    assert reference["authors"][1]["organization"] == "Study Consortium"
    assert main([*args, "--offline", "--write"]) == 0
    capsys.readouterr()
    from pkdb.preparation import prepare

    prepared = prepare(study_folder, vocabulary=vocabulary)
    assert prepared.study.reference.publication_date == "2020-03"
    assert len(calls) == 1


def test_doi_normalization_and_year_precision(tmp_path):
    assert normalize_doi("https://doi.org/10.1234/Example") == "10.1234/example"
    with transport(lambda request: httpx2.Response(200, json=CSL)) as client:
        result = ReferenceResolver(tmp_path, client=client).resolve(
            {"doi": "10.1234/example"}, sid="stable", name="Example"
        )
    assert result["sid"] == "stable"
    assert result["publication_date"] == "2020"
    assert result["date"] is None


def test_manual_reference_and_search_never_auto_select(study_folder, tmp_path, capsys):
    args = [
        "reference",
        "resolve",
        str(study_folder),
        "--title",
        "Unpublished report",
        "--organization",
        "Research team",
        "--offline",
        "--write",
    ]
    assert main(args) == 0
    capsys.readouterr()
    reference = json.loads((study_folder / "reference.json").read_text())
    assert reference["pmid"] is None and reference["doi"] is None
    assert reference["date"] is None
    before = (study_folder / "reference.json").read_bytes()
    with transport(
        lambda _: httpx2.Response(200, json={"message": {"items": [CSL]}})
    ) as client:
        assert (
            main(
                ["reference", "search", "A citation", "--cache-dir", str(tmp_path)],
                client=client,
            )
            == 0
        )
    assert json.loads(capsys.readouterr().out)["candidates"][0]["doi"] == CSL["DOI"]
    assert (study_folder / "reference.json").read_bytes() == before


def test_refresh_preserves_manual_edits_and_can_update_other_fields(
    study_folder, tmp_path
):
    with transport(lambda _: httpx2.Response(200, text=XML)) as client:
        preview = preview_reference(
            study_folder, {"pmid": "123"}, ReferenceResolver(tmp_path, client=client)
        )
        save_reference(study_folder, preview)
    path = study_folder / "reference.json"
    value = json.loads(path.read_text())
    value["title"] = "Curator title"
    path.write_text(json.dumps(value))
    changed_xml = XML.replace("Test journal", "New journal")
    with transport(lambda _: httpx2.Response(200, text=changed_xml)) as client:
        refreshed = preview_reference(
            study_folder, {}, ReferenceResolver(tmp_path, client=client, refresh=True)
        )
    assert refreshed["reference"]["title"] == "Curator title"
    assert refreshed["reference"]["journal"] == "New journal"
    assert refreshed["reference"]["provenance"]["overrides"]["title"] == "Curator title"


def test_conflicting_identifiers_and_changed_source_rejected(study_folder, tmp_path):
    with transport(lambda _: httpx2.Response(200, text=XML)) as client:
        resolver = ReferenceResolver(tmp_path, client=client)
        with pytest.raises(ReferenceError, match="different publications"):
            resolver.resolve({"pmid": "123", "doi": "10.1234/other"}, sid="r", name="n")
        preview = preview_reference(study_folder, {"pmid": "123"}, resolver)
    path = study_folder / "reference.json"
    path.write_text('{"sid":123,"name":"Changed"}')
    with pytest.raises(ReferenceError, match="changed since preview"):
        save_reference(study_folder, preview)
    assert json.loads(path.read_text())["name"] == "Changed"


def test_refresh_failure_preserves_good_cache(tmp_path):
    with transport(lambda _: httpx2.Response(200, text=XML)) as client:
        ReferenceResolver(tmp_path, client=client).pubmed("123")
    with transport(lambda _: httpx2.Response(503)) as client:
        with pytest.raises(ReferenceError, match="unavailable"):
            ReferenceResolver(tmp_path, client=client, refresh=True).pubmed("123")
    assert (
        ReferenceResolver(tmp_path, offline=True).pubmed("123")["title"]
        == "A nested title"
    )


def test_concurrent_requests_share_cache(tmp_path):
    calls = []

    def respond(request):
        calls.append(request)
        return httpx2.Response(200, text=XML)

    with transport(respond) as client, ThreadPoolExecutor(3) as pool:
        results = list(
            pool.map(
                lambda _: ReferenceResolver(tmp_path, client=client).pubmed("123"),
                range(3),
            )
        )
    assert len(calls) == 1
    assert all(r["pmid"] == "123" for r in results)


def test_not_found_cache_and_offline_miss(tmp_path):
    calls = []
    with transport(lambda r: calls.append(r) or httpx2.Response(404)) as client:
        for _ in range(2):
            with pytest.raises(ReferenceError, match="No pubmed record"):
                ReferenceResolver(tmp_path, client=client).pubmed("999")
    assert len(calls) == 1
    with pytest.raises(ReferenceError, match="No cached"):
        ReferenceResolver(tmp_path, offline=True).pubmed("123")


def test_wrong_pubmed_response_and_invalid_date():
    with pytest.raises(ReferenceError):
        parse_pubmed(XML, "999")
    from pkdb.schemas.study import Reference

    with pytest.raises(ValueError):
        Reference(sid="r", name="n", publication_date="2020-13")


def test_doi_enrichment_checks_exact_identifier(tmp_path):
    def respond(request):
        if request.url.host == "doi.org":
            return httpx2.Response(200, json=CSL)
        if request.url.path.endswith("esearch.fcgi"):
            return httpx2.Response(200, json={"esearchresult": {"idlist": ["123"]}})
        return httpx2.Response(200, text=XML)

    with transport(respond) as client:
        result = ReferenceResolver(tmp_path, client=client).resolve(
            {"doi": CSL["DOI"]}, sid="r", name="n"
        )
    assert result["pmid"] == "123"
    assert result["title"] == "A nested title"
    assert not result["provenance"]["warnings"]
    assert (
        ReferenceResolver(tmp_path, offline=True).resolve(
            {"doi": CSL["DOI"]}, sid="r", name="n"
        )["pmid"]
        == "123"
    )


def test_changed_explicit_override_survives_refresh(tmp_path):
    with transport(lambda _: httpx2.Response(200, text=XML)) as client:
        first = ReferenceResolver(tmp_path, client=client).resolve(
            {"pmid": "123", "title": "Original override"}, sid="r", name="n"
        )
    first["title"] = "Edited override"
    refreshed = ReferenceResolver(tmp_path, offline=True).resolve(
        {}, sid="r", name="n", existing=first
    )
    assert refreshed["title"] == "Edited override"
    refreshed["title"] = "A nested title"
    reset = ReferenceResolver(tmp_path, offline=True).resolve(
        {}, sid="r", name="n", existing=refreshed
    )
    assert reset["title"] == "A nested title"
    assert "title" not in reset["provenance"]["overrides"]


def test_corrupt_cache_recovers_online_and_fails_cleanly_offline(tmp_path):
    with transport(lambda _: httpx2.Response(200, text=XML)) as client:
        ReferenceResolver(tmp_path, client=client).pubmed("123")
        path = next((tmp_path / "references").glob("*.json"))
        path.write_text('{"version":1,"status":200}')
        with pytest.raises(ReferenceError, match="No cached"):
            ReferenceResolver(tmp_path, offline=True).pubmed("123")
        assert ReferenceResolver(tmp_path, client=client).pubmed("123")["pmid"] == "123"


def test_empty_pubmed_result_is_negative_cached(tmp_path):
    calls = []
    with transport(
        lambda r: calls.append(r) or httpx2.Response(200, text="<PubmedArticleSet/>")
    ) as client:
        for _ in range(2):
            with pytest.raises(ReferenceError):
                ReferenceResolver(tmp_path, client=client).pubmed("999")
    assert len(calls) == 1


def test_manual_minimum_rejects_empty_author(tmp_path):
    with pytest.raises(ValueError, match="last name or organization"):
        ReferenceResolver(tmp_path, offline=True).resolve(
            {"title": "A report", "authors": [{}]}, sid="r", name="n"
        )


def test_selecting_new_publication_keeps_sid_not_old_overrides(tmp_path):
    with transport(lambda _: httpx2.Response(200, text=XML)) as client:
        previous = ReferenceResolver(tmp_path, client=client).resolve(
            {"pmid": "123", "title": "Old correction"}, sid="stable", name="study"
        )

    def respond(request):
        if request.url.host == "doi.org":
            return httpx2.Response(
                200, json={**CSL, "DOI": "10.1234/new", "title": "New publication"}
            )
        return httpx2.Response(200, json={"esearchresult": {"idlist": []}})

    with transport(respond) as client:
        result = ReferenceResolver(tmp_path, client=client).resolve(
            {"doi": "10.1234/new"}, sid="stable", name="study", existing=previous
        )
    assert result["sid"] == "stable"
    assert result["title"] == "New publication"
    assert result["pmid"] is None
    assert not result["provenance"]["overrides"]


def test_exact_date_must_agree_with_partial_date():
    from pkdb.schemas.study import Reference

    with pytest.raises(ValueError, match="agree"):
        Reference(sid="r", name="n", date="2020-01-01", publication_date="2021")


def test_pubmed_doi_fallback_and_unverifiable_pair(tmp_path):
    no_ids = XML.replace('<ArticleId IdType="doi">10.1234/Example</ArticleId>', "")
    with transport(lambda _: httpx2.Response(200, text=no_ids)) as client:
        with pytest.raises(ReferenceError, match="association can be verified"):
            ReferenceResolver(tmp_path, client=client).resolve(
                {"pmid": "123", "doi": "10.1234/example"}, sid="r", name="n"
            )
    fallback = no_ids.replace(
        "</ArticleTitle>",
        '</ArticleTitle><ELocationID EIdType="doi">10.1234/Example</ELocationID>',
    )
    assert parse_pubmed(fallback, "123")["doi"] == "10.1234/example"


def test_explicit_reset_replaces_legacy_fields(study_folder, tmp_path):
    path = study_folder / "reference.json"
    legacy = json.loads(path.read_text()) | {
        "pmid": "123",
        "title": "Old title",
        "date": "2025-02-03",
    }
    path.write_text(json.dumps(legacy))
    with transport(lambda _: httpx2.Response(200, text=XML)) as client:
        resolver = ReferenceResolver(tmp_path, client=client)
        kept = preview_reference(study_folder, {}, resolver)
        assert kept["reference"]["title"] == "Old title"
        assert kept["reference"]["date"] == "2025-02-03"
        reset = preview_reference(study_folder, {}, resolver, reset_overrides=True)
    assert reset["reference"]["title"] == "A nested title"
    assert reset["reference"]["publication_date"] == "2020-03"
    assert reset["reference"]["date"] is None
    assert not reset["reference"]["provenance"]["overrides"]
    assert json.loads(path.read_text()) == legacy
