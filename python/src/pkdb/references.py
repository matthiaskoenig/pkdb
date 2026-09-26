"""Explicit literature lookup and reviewable reference snapshots.

Scientific preparation never calls this module. Provider responses are cached;
accepted metadata and curator overrides travel with the source reference.
"""

import hashlib
import html
import json
import re
import threading
import time
import xml.etree.ElementTree as ET
from calendar import month_abbr
from copy import deepcopy
from datetime import UTC, date, datetime
from pathlib import Path
from urllib.parse import quote, unquote

import httpx2

from pkdb.cache import atomic_json, cache_directory
from pkdb.schemas.study import Reference

_LOCK = threading.RLock()
_LAST_REQUEST = 0.0
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
FIELDS = {
    "pmid",
    "url",
    "doi",
    "title",
    "abstract",
    "journal",
    "date",
    "publication_date",
    "authors",
}


class ReferenceError(ValueError):
    """A lookup or review could not be completed safely."""


class NotFound(ReferenceError):
    pass


def normalize_pmid(value):
    value = str(value).strip()
    value = re.sub(r"^https?://pubmed\.ncbi\.nlm\.nih\.gov/", "", value).strip("/")
    if not re.fullmatch(r"[0-9]+", value) or int(value) <= 0:
        raise ReferenceError("PMID must be a positive integer or PubMed URL")
    return str(int(value))


def normalize_doi(value):
    value = re.sub(
        r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", str(value).strip(), flags=re.I
    )
    value = unquote(value).lower()
    if not re.fullmatch(r"10\.[0-9]{4,9}/\S+", value) or any(
        ord(c) < 32 for c in value
    ):
        raise ReferenceError("Expected a DOI or doi.org URL")
    return value


def partial_date(value):
    if value is None or value == "":
        return None
    value = str(value)
    if not re.fullmatch(r"[0-9]{4}(?:-[0-9]{2})?(?:-[0-9]{2})?", value):
        raise ReferenceError("Publication date must be YYYY, YYYY-MM, or YYYY-MM-DD")
    date.fromisoformat(value + {4: "-01-01", 7: "-01", 10: ""}[len(value)])
    return value


def _text(node):
    return "" if node is None else "".join(node.itertext()).strip()


def _xml_date(node):
    if node is None:
        return None
    year, month, day = (_text(node.find(key)) for key in ("Year", "Month", "Day"))
    if not year:
        match = re.search(r"\b([0-9]{4})\b", _text(node.find("MedlineDate")))
        return partial_date(match[1]) if match else None
    result = year
    if month:
        if not month.isdigit():
            month = str(
                next(
                    (
                        i
                        for i, name in enumerate(month_abbr)
                        if name.lower() == month[:3].lower()
                    ),
                    0,
                )
            )
        if int(month) == 0:
            return partial_date(year)
        result += f"-{int(month):02}"
        if day:
            result += f"-{int(day):02}"
    return partial_date(result)


def parse_pubmed(raw, pmid):
    if "<!ENTITY" in raw.upper():
        raise ReferenceError("Unexpected XML entity declaration")
    try:
        root = ET.fromstring(raw)
        records = root.findall(".//PubmedArticle")
        record = next(
            (r for r in records if _text(r.find("MedlineCitation/PMID")) == pmid), None
        )
        if record is None:
            raise NotFound(f"PubMed record {pmid} was not returned")
        article = record.find("MedlineCitation/Article")
        if article is None:
            raise ReferenceError("PubMed record has no article metadata")
        published = _xml_date(article.find("Journal/JournalIssue/PubDate"))
        if published is None:
            published = _xml_date(article.find("ArticleDate"))
        authors = []
        for author in article.findall("AuthorList/Author"):
            organization = _text(author.find("CollectiveName"))
            if organization:
                authors.append(
                    {"organization": organization, "last_name": "", "first_name": ""}
                )
            else:
                last = _text(author.find("LastName"))
                if last:
                    authors.append(
                        {
                            "last_name": last,
                            "first_name": _text(author.find("ForeName"))
                            or _text(author.find("Initials")),
                        }
                    )
        abstracts = []
        for section in article.findall("Abstract/AbstractText"):
            label = section.get("Label")
            abstracts.append((f"{label}: " if label else "") + _text(section))
        doi = next(
            (
                _text(item)
                for item in record.findall("PubmedData/ArticleIdList/ArticleId")
                if item.get("IdType") == "doi"
            ),
            None,
        )
        if not doi:
            doi = next(
                (
                    _text(item)
                    for item in article.findall("ELocationID")
                    if item.get("EIdType") == "doi"
                ),
                None,
            )
        return {
            "pmid": pmid,
            "doi": normalize_doi(doi) if doi else None,
            "title": _text(article.find("ArticleTitle")) or None,
            "journal": _text(article.find("Journal/Title")) or None,
            "abstract": "\n\n".join(abstracts) or None,
            "authors": authors,
            "publication_date": published,
            "date": published if published and len(published) == 10 else None,
        }
    except (ET.ParseError, TypeError, AttributeError) as error:
        raise ReferenceError("Invalid PubMed metadata response") from error


def parse_csl(value, doi=None):
    if not isinstance(value, dict):
        raise ReferenceError("Invalid DOI metadata response")
    actual = normalize_doi(value.get("DOI", ""))
    if doi and actual != doi:
        raise ReferenceError("Returned DOI does not match the requested DOI")
    parts = value.get("issued", {}).get("date-parts", [[]])[0]
    published = (
        partial_date(
            "-".join(
                f"{int(p):04}" if i == 0 else f"{int(p):02}"
                for i, p in enumerate(parts[:3])
            )
        )
        if parts
        else None
    )
    authors = []
    for author in value.get("author", []):
        if author.get("literal") or author.get("name"):
            authors.append(
                {
                    "organization": author.get("literal") or author["name"],
                    "last_name": "",
                    "first_name": "",
                }
            )
        elif author.get("family"):
            authors.append(
                {"last_name": author["family"], "first_name": author.get("given", "")}
            )
    title = value.get("title")
    journal = value.get("container-title")
    return {
        "doi": actual,
        "pmid": None,
        "title": title[0] if isinstance(title, list) and title else title,
        "journal": journal[0] if isinstance(journal, list) and journal else journal,
        "abstract": html.unescape(re.sub(r"<[^>]+>", "", value.get("abstract") or ""))
        or None,
        "authors": authors,
        "publication_date": published,
        "date": published if published and len(published) == 10 else None,
    }


def merge_metadata(primary, secondary):
    merged = {k: primary.get(k) or secondary.get(k) for k in FIELDS}
    dates = primary if primary.get("publication_date") else secondary
    merged.update({k: dates.get(k) for k in ("date", "publication_date")})
    return merged


class ReferenceResolver:
    def __init__(self, cache_dir=None, *, client=None, offline=False, refresh=False):
        if offline and refresh:
            raise ReferenceError("Refresh requires network access")
        self.cache_dir = Path(cache_dir or cache_directory()) / "references"
        self.client = client
        self.offline = offline
        self.refresh = refresh
        self.sources = []
        self.warnings = []

    def _get(self, provider, identifier, url, *, params=None, headers=None, parse=None):
        global _LAST_REQUEST
        key = hashlib.sha256(json.dumps([provider, identifier, 1]).encode()).hexdigest()
        path = self.cache_dir / f"{key}.json"
        with _LOCK:
            cached = None
            try:
                cached = json.loads(path.read_text())
                if not isinstance(cached, dict) or cached.get("version") != 1:
                    cached = None
            except OSError, ValueError:
                pass
            if cached and not self.refresh:
                try:
                    if cached.get("status") == 404:
                        if time.time() - cached["timestamp"] < 3600:
                            raise NotFound(
                                f"No {provider} record found for {identifier}"
                            )
                    else:
                        source = {
                            k: cached[k]
                            for k in ("provider", "identifier", "retrieved_at")
                        }
                        result = parse(cached["data"]) if parse else cached["data"]
                        self.sources.append(source)
                        return result
                except NotFound:
                    raise
                except ValueError, KeyError, IndexError, TypeError, AttributeError:
                    cached = None
            if self.offline:
                raise ReferenceError(
                    f"No cached {provider} metadata for {identifier}; resolve online first"
                )
            own_client = self.client is None
            client = self.client or httpx2.Client(timeout=15, follow_redirects=True)
            try:
                for attempt in range(3):
                    time.sleep(max(0, 0.36 - (time.monotonic() - _LAST_REQUEST)))
                    _LAST_REQUEST = time.monotonic()
                    try:
                        response = client.get(
                            url, params=params, headers=headers or {}, timeout=15
                        )
                    except httpx2.TransportError as error:
                        if attempt == 2:
                            raise ReferenceError(
                                f"{provider} unavailable; saved references and cache are unchanged"
                            ) from error
                        time.sleep(2**attempt)
                        continue
                    if response.status_code == 429 or response.status_code >= 500:
                        if attempt == 2:
                            raise ReferenceError(
                                f"{provider} unavailable (HTTP {response.status_code}); retry later"
                            )
                        delay = response.headers.get("Retry-After", "")
                        time.sleep(
                            min(5, float(delay)) if delay.isdigit() else 2**attempt
                        )
                        continue
                    stamp = datetime.now(UTC).isoformat()
                    envelope = {
                        "version": 1,
                        "provider": provider,
                        "identifier": identifier,
                        "retrieved_at": stamp,
                        "timestamp": time.time(),
                        "status": response.status_code,
                    }
                    if response.status_code == 404:
                        if cached is None or cached.get("status") == 404:
                            atomic_json(path, envelope)
                        raise NotFound(f"No {provider} record found for {identifier}")
                    if response.status_code != 200:
                        raise ReferenceError(
                            f"{provider} request failed (HTTP {response.status_code})"
                        )
                    if len(response.content) > 4_000_000:
                        raise ReferenceError("Metadata response is too large")
                    try:
                        raw = response.text if provider == "pubmed" else response.json()
                        result = parse(raw) if parse else raw
                    except NotFound:
                        if cached is None or cached.get("status") == 404:
                            atomic_json(path, {**envelope, "status": 404})
                        raise
                    except (
                        ValueError,
                        KeyError,
                        IndexError,
                        TypeError,
                        AttributeError,
                    ) as error:
                        raise ReferenceError(
                            f"Invalid {provider} metadata: {error}"
                        ) from error
                    envelope["data"] = raw
                    atomic_json(path, envelope)
                    self.sources.append(
                        {
                            k: envelope[k]
                            for k in ("provider", "identifier", "retrieved_at")
                        }
                    )
                    return result
            finally:
                if own_client:
                    client.close()

    def pubmed(self, pmid):
        pmid = normalize_pmid(pmid)
        return self._get(
            "pubmed",
            pmid,
            EUTILS + "efetch.fcgi",
            params={"db": "pubmed", "id": pmid, "retmode": "xml", "tool": "pkdb"},
            parse=lambda raw: parse_pubmed(raw, pmid),
        )

    def doi(self, doi):
        doi = normalize_doi(doi)
        return self._get(
            "doi",
            doi,
            "https://doi.org/" + quote(doi, safe="/"),
            headers={
                "Accept": "application/vnd.citationstyles.csl+json",
                "User-Agent": "pkdb-reference/1",
            },
            parse=lambda raw: parse_csl(raw, doi),
        )

    def pubmed_for_doi(self, doi):
        value = self._get(
            "pubmed-search",
            doi,
            EUTILS + "esearch.fcgi",
            params={
                "db": "pubmed",
                "term": f'"{doi}"[AID]',
                "retmode": "json",
                "retmax": 5,
                "tool": "pkdb",
            },
            parse=lambda value: value["esearchresult"]["idlist"],
        )
        matches = []
        for pmid in value:
            record = self.pubmed(pmid)
            if record.get("doi") == doi:
                matches.append(record)
        if len(matches) > 1:
            self.warnings.append(
                "Several PubMed records match this DOI; PMID was not selected"
            )
        return matches[0] if len(matches) == 1 else None

    def search(self, citation):
        citation = str(citation).strip()
        if not citation or len(citation) > 2000:
            raise ReferenceError("Supply a citation of 1 to 2000 characters")

        def parse(value):
            return [parse_csl(item) for item in value["message"]["items"]]

        return self._get(
            "crossref-search",
            citation,
            "https://api.crossref.org/works",
            params={"query.bibliographic": citation, "rows": 5},
            headers={"User-Agent": "pkdb-reference/1"},
            parse=parse,
        )

    def resolve(self, seed, *, sid, name, existing=None, reset_overrides=False):
        if not isinstance(seed, dict) or set(seed) - FIELDS:
            raise ReferenceError("Reference input contains unsupported fields")
        self.sources = []
        self.warnings = []
        seed = deepcopy(seed)
        explicit = deepcopy(seed)
        existing = existing or {}
        provenance = existing.get("provenance") or {}
        if not isinstance(provenance, dict) or any(
            not isinstance(provenance.get(key, {}), dict)
            for key in ("input", "overrides", "resolved")
        ):
            raise ReferenceError("Invalid saved reference provenance")
        original = provenance.get("input", {})
        if reset_overrides:
            identifiers = {k: existing[k] for k in ("pmid", "doi") if existing.get(k)}
            original = {
                **identifiers,
                **{k: v for k, v in original.items() if k in {"pmid", "doi"}},
            }
            if not any(seed.get(k, original.get(k)) for k in ("pmid", "doi")):
                raise ReferenceError("Resetting overrides requires a PMID or DOI")
            provenance, existing = {}, {}
        changed_identity = any(
            seed.get(field)
            and existing.get(field)
            and normalizer(seed[field]) != normalizer(existing[field])
            for field, normalizer in (("pmid", normalize_pmid), ("doi", normalize_doi))
        )
        if changed_identity:
            original, provenance, existing = {}, {}, {}
        seed = {**original, **seed}
        if explicit.get("doi") and "pmid" not in explicit:
            seed.pop("pmid", None)
        if explicit.get("pmid") and "doi" not in explicit:
            seed.pop("doi", None)
        for field, normalizer in (("pmid", normalize_pmid), ("doi", normalize_doi)):
            if seed.get(field):
                seed[field] = normalizer(seed[field])
        if not seed.get("pmid") and not seed.get("doi"):
            if not seed.get("title") or not seed.get("authors"):
                raise ReferenceError(
                    "Manual references require a title and at least one author or organization"
                )
            resolved = {**seed}
            if resolved.get("publication_date"):
                published = partial_date(resolved["publication_date"])
                resolved["date"] = published if len(published) == 10 else None
        else:
            resolved = (
                self.pubmed(seed["pmid"]) if seed.get("pmid") else self.doi(seed["doi"])
            )
            if seed.get("pmid") and seed.get("doi"):
                if resolved.get("doi") and resolved["doi"] != seed["doi"]:
                    raise ReferenceError("PMID and DOI identify different publications")
                if not resolved.get("doi"):
                    raise ReferenceError(
                        "PubMed does not report a DOI for this record; resolve with one identifier until the association can be verified"
                    )
                doi_metadata = self.doi(seed["doi"])
                resolved = merge_metadata(resolved, doi_metadata)
                resolved["pmid"] = seed["pmid"]
        if seed.get("doi") and not seed.get("pmid"):
            try:
                pubmed = self.pubmed_for_doi(seed["doi"])
            except ReferenceError as error:
                self.warnings.append(
                    f"DOI metadata resolved; optional PubMed enrichment unavailable: {error}"
                )
            else:
                if pubmed:
                    resolved = merge_metadata(pubmed, resolved)
        normalized = Reference.model_validate(
            {"sid": str(sid), "name": name, **resolved}
        ).model_dump(mode="json")
        resolved = {k: normalized[k] for k in FIELDS}
        if any(
            resolved.get(field)
            and existing.get(field)
            and normalizer(resolved[field]) != normalizer(existing[field])
            for field, normalizer in (("pmid", normalize_pmid), ("doi", normalize_doi))
        ):
            # A newly selected publication must not inherit the previous one's edits.
            provenance, existing = {}, {}
            seed = explicit
        overrides = dict(provenance.get("overrides", {}))
        previous = provenance.get("resolved", {})
        for field in FIELDS - {"pmid", "doi"}:
            if field in existing and (
                previous
                and existing[field] != previous.get(field)
                or not previous
                and existing[field] not in (None, "", [])
            ):
                overrides[field] = existing[field]
            elif previous and field in existing:
                overrides.pop(field, None)
        overrides.update(
            {k: v for k, v in explicit.items() if k not in {"pmid", "doi"}}
        )
        values = {**resolved, **overrides}
        if "publication_date" in overrides:
            published = partial_date(overrides["publication_date"])
            values["date"] = published if published and len(published) == 10 else None
        if "date" in overrides and "publication_date" not in overrides:
            values["publication_date"] = overrides["date"]
        reference = Reference.model_validate({"sid": str(sid), "name": name, **values})
        result = reference.model_dump(mode="json")
        result["provenance"] = {
            "version": 1,
            "input": seed,
            "overrides": overrides,
            "resolved": resolved,
            "sources": self.sources,
            "warnings": self.warnings,
        }
        return result


def _file_digest(folder):
    digest = hashlib.sha256()
    for name in ("study.json", "reference.json"):
        path = folder / name
        if path.is_symlink():
            raise ReferenceError("Reference source files must not be symlinks")
        digest.update(name.encode())
        digest.update(path.read_bytes() if path.exists() else b"<missing>")
    return digest.hexdigest()


def preview_reference(folder, seed, resolver, *, reset_overrides=False):
    folder = Path(folder)
    revision = _file_digest(folder)
    study = json.loads((folder / "study.json").read_text())
    path = folder / "reference.json"
    existing = json.loads(path.read_text()) if path.exists() else {}
    sid = study.get("reference")
    if not isinstance(sid, (str, int)) or isinstance(sid, bool) or not str(sid):
        raise ReferenceError("study.json must define a stable reference identifier")
    if existing and str(existing.get("sid")) != str(sid):
        raise ReferenceError("Existing reference SID does not match study.json")
    if seed and not ({"pmid", "doi"} & seed.keys()):
        seed = {**{k: existing[k] for k in ("pmid", "doi") if existing.get(k)}, **seed}
    if not seed and not existing.get("provenance") and not reset_overrides:
        seed = {
            k: v for k, v in existing.items() if k in FIELDS and v not in (None, "", [])
        }
    result = resolver.resolve(
        seed,
        sid=sid,
        name=existing.get("name") or study.get("name") or folder.name,
        existing=existing,
        reset_overrides=reset_overrides,
    )
    if _file_digest(folder) != revision:
        raise ReferenceError("Reference sources changed during lookup; preview again")
    changes = {
        k: {"before": existing.get(k), "after": v}
        for k, v in result.items()
        if existing.get(k) != v
    }
    return {"reference": result, "changes": changes, "revision": revision}


def save_reference(folder, preview):
    folder = Path(folder)
    with _LOCK:
        if _file_digest(folder) != preview["revision"]:
            raise ReferenceError(
                "Reference sources changed since preview; preview again"
            )
        reference = Reference.model_validate(preview["reference"])
        atomic_json(folder / "reference.json", reference.model_dump(mode="json"))
