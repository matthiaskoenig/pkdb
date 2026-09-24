"""Synchronous, typed HTTP API with explicit offline preparation."""

import json
import math
import os
from contextlib import ExitStack
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import BinaryIO
from urllib.parse import quote

import httpx2
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from pkdb import __version__
from pkdb.cache import (
    VocabularyCache,
    bundled_vocabulary,
    endpoint_root,
    parse_vocabulary,
)
from pkdb.domain.validation import PROCESSING_VERSION, prepare_study
from pkdb.domain.vocabulary import Vocabulary
from pkdb.errors import ClientError, CompatibilityError
from pkdb.importers.folder import parse_bundle
from pkdb.preparation import PreparedBundle, prepare
from pkdb.progress import ProgressCallback, emit
from pkdb.querying import export_from_filters, query_from_filters
from pkdb.schemas.data import DataPage
from pkdb.schemas.replacement import ReplacementResult
from pkdb.schemas.responses import (
    GroupResponse,
    IndividualResponse,
    InterventionResponse,
    OutputResponse,
    ReferenceResponse,
    StudyResponse,
)
from pkdb.schemas.study import CanonicalStudy
from pkdb.schemas.validation import ValidationReport, fail


def _known_report(value: dict) -> dict:
    """Accept future optional wire fields without weakening domain validation."""
    from pkdb.schemas.source import SourceLocation
    from pkdb.schemas.validation import RelatedSource, Suggestion, ValidationIssue

    report = {
        key: item for key, item in value.items() if key in ValidationReport.model_fields
    }
    issues = []
    for item in report.get("issues", []):
        issue = {
            key: val for key, val in item.items() if key in ValidationIssue.model_fields
        }
        if isinstance(issue.get("source"), dict):
            issue["source"] = {
                key: val
                for key, val in issue["source"].items()
                if key in SourceLocation.model_fields
            }
        for name, model in (
            ("suggestions", Suggestion),
            ("related_sources", RelatedSource),
        ):
            if isinstance(issue.get(name), list):
                issue[name] = [
                    {key: val for key, val in item.items() if key in model.model_fields}
                    for item in issue[name]
                    if isinstance(item, dict)
                ]
                if name == "related_sources":
                    for related in issue[name]:
                        if isinstance(related.get("source"), dict):
                            related["source"] = {
                                key: val
                                for key, val in related["source"].items()
                                if key in SourceLocation.model_fields
                            }
        issues.append(issue)
    report["issues"] = issues
    return report


class ResultPage[T: BaseModel](BaseModel):
    items: list[T]
    count: int = Field(ge=0)
    page: int = Field(ge=1)
    pages: int = Field(ge=1)


class UploadLimits(BaseModel):
    max_rows: int = Field(gt=0)
    max_files: int = Field(gt=0)
    max_upload_bytes: int = Field(gt=0)
    max_attachment_bytes: int = Field(gt=0)


class Capabilities(BaseModel):
    model_config = ConfigDict(extra="ignore")
    schema_version: int
    server_version: str
    processing_version: str
    vocabulary_version: str
    vocabulary_hash: str
    upload_limits: UploadLimits
    upload_report_versions: list[int] = Field(default_factory=lambda: [1])


class Studies:
    def __init__(self, client: Client):
        self.client = client

    def get(self, sid: str) -> CanonicalStudy:
        return self.client._model(
            CanonicalStudy,
            self.client._request("GET", f"/api/v2/studies/{quote(str(sid), safe='')}"),
        )

    def list(self, **filters) -> ResultPage[StudyResponse]:
        return self.client._page("studies", StudyResponse, filters)


class Client:
    """An endpoint-scoped client. Construction performs no network requests.

    A caller-supplied HTTP transport remains owned by the caller. Requests never
    follow redirects and writes are never retried automatically.
    """

    def __init__(
        self,
        endpoint: str | None = None,
        api_key: str | None = None,
        *,
        transport=None,
        cache: VocabularyCache | None = None,
        progress: ProgressCallback | None = None,
    ):
        endpoint = endpoint or os.environ.get("PKDB_ENDPOINT")
        if not endpoint:
            raise ValueError("Set PKDB_ENDPOINT or pass endpoint")
        self.progress = progress
        self.last_upload_report: dict | None = None
        self.endpoint = endpoint_root(endpoint)
        self._api_key = (
            api_key if api_key is not None else os.environ.get("PKDB_API_KEY")
        )
        self._owns_transport = transport is None
        self._transport = (
            transport
            if transport is not None
            else httpx2.Client(
                timeout=httpx2.Timeout(600, connect=10), follow_redirects=False
            )
        )
        self.cache = cache if cache is not None else VocabularyCache()
        self._vocabulary: Vocabulary | None = None
        self.studies = Studies(self)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        if self._owns_transport:
            self._transport.close()

    def _headers(self, *, required=False) -> dict[str, str]:
        if required and not self._api_key:
            raise ClientError(
                "Set PKDB_API_KEY or pass api_key for uploads and downloads"
            )
        headers = {"User-Agent": f"pkdb/{__version__}"}
        if self._api_key:
            kind = "Bearer" if self._api_key.startswith("pkdb_live_") else "Token"
            headers["Authorization"] = f"{kind} {self._api_key}"
        return headers

    def _check(self, response):
        if 200 <= response.status_code < 300:
            return
        report = None
        body = None
        try:
            body = response.json()
            report_body = body.get("report", body) if isinstance(body, dict) else None
            if isinstance(report_body, dict) and isinstance(
                report_body.get("issues"), list
            ):
                report = ValidationReport.model_validate(_known_report(report_body))
        except ValueError, ValidationError:
            pass
        compatibility_messages = {
            "vocabulary_mismatch": "Server vocabulary changed; synchronize vocabulary and prepare again",
            "vocabulary_changed": "Server vocabulary changed during upload; synchronize vocabulary and prepare again",
            "processing_version_mismatch": "Server processing rules differ; install the matching pkdb release and prepare again",
        }
        detail = body.get("detail") if isinstance(body, dict) else None
        message = f"PK-DB request rejected (HTTP {response.status_code})"
        if report and report.issues:
            issues = [issue for issue in report.issues if issue.severity == "error"]
            summary = "; ".join(
                f"{issue.code}: {issue.message}" for issue in issues[:3]
            )
            if summary:
                message += f": {summary}"
                if len(issues) > 3 or report.truncated:
                    message += "; see validation report for further issues"
        error = ClientError
        if (
            response.status_code == 409
            and isinstance(detail, str)
            and detail in compatibility_messages
        ):
            error = CompatibilityError
            message = compatibility_messages[detail]
        if report and any(issue.category == "compatibility" for issue in report.issues):
            error = CompatibilityError
        raise error(
            message,
            status_code=response.status_code,
            report=report,
            request_id=body.get("request_id") if isinstance(body, dict) else None,
            stage=body.get("stage") if isinstance(body, dict) else None,
            persistence=body.get(
                "persistence", "unknown" if response.status_code >= 500 else "not_saved"
            )
            if isinstance(body, dict)
            else "unknown",
            envelope=body
            if isinstance(body, dict) and "report_version" in body
            else None,
        )

    def _request(self, method, path, *, headers=None, **kwargs):
        read_only = method == "GET" or path == "/api/v2/query"
        request_headers = {**self._headers(), **(headers or {})}
        try:
            if self.progress and method == "PUT" and "files" in kwargs:
                request = self._transport.build_request(
                    method, self.endpoint + path, headers=request_headers, **kwargs
                )
                original = request.stream
                assert isinstance(original, httpx2.SyncByteStream)
                total = (
                    int(request.headers["content-length"])
                    if "content-length" in request.headers
                    else None
                )
                callback = self.progress

                class CountingStream(httpx2.SyncByteStream):
                    def __iter__(self):
                        completed = 0
                        emit(callback, "transfer", completed=0, total=total)
                        for chunk in original:
                            yield chunk
                            completed += len(chunk)
                            emit(callback, "transfer", completed=completed, total=total)
                        emit(callback, "server_validation")

                    def close(self):
                        original.close()

                request.stream = CountingStream()
                response = self._transport.send(request, follow_redirects=False)
            else:
                response = self._transport.request(
                    method,
                    self.endpoint + path,
                    headers=request_headers,
                    follow_redirects=False,
                    **kwargs,
                )
        except httpx2.RequestError:
            message = "PK-DB request failed"
            if not read_only:
                message += (
                    "; upload outcome may be unknown. Inspect the study before retrying"
                )
            raise ClientError(
                message,
                persistence="unknown" if not read_only else "not_attempted",
                stage="transfer" if not read_only else "compatibility",
            ) from None
        try:
            self._check(response)
        except ClientError as error:
            if read_only:
                error.persistence = "not_attempted"
            raise
        return response

    @staticmethod
    def _model[T: BaseModel](model: type[T], response: httpx2.Response) -> T:
        try:
            return model.model_validate(response.json())
        except ValueError, ValidationError:
            raise ClientError("Server returned an invalid response contract") from None

    def capabilities(self) -> Capabilities:
        value = self._model(Capabilities, self._request("GET", "/api/v2/capabilities"))
        if value.schema_version != 1:
            raise CompatibilityError(
                "Unsupported server client-protocol version; update pkdb"
            )
        return value

    def vocabulary(self, *, refresh: bool = True) -> Vocabulary:
        if refresh:
            try:
                value = parse_vocabulary(
                    self._request("GET", "/api/v2/vocabulary").json()
                )
            except ValueError, ValidationError, AttributeError:
                raise ClientError(
                    "Server returned an invalid vocabulary snapshot"
                ) from None
            self.cache.store(self.endpoint, value)
        else:
            value = self.cache.load(self.endpoint)
        self._vocabulary = value
        return value

    def _local_vocabulary(self) -> Vocabulary:
        if self._vocabulary is not None:
            return self._vocabulary
        try:
            return self.cache.load(self.endpoint)
        except FileNotFoundError:
            return bundled_vocabulary()

    def upload(self, study: PreparedBundle | str | Path) -> ReplacementResult:
        self.last_upload_report = None
        emit(self.progress, "validate")
        prepared = (
            study
            if isinstance(study, PreparedBundle)
            else prepare(
                study, vocabulary=self._local_vocabulary(), progress=self.progress
            )
        )
        headers = self._headers(required=True)
        # Detect file changes and validate again against the captured vocabulary
        # before contacting the server. Never trust mutated Pydantic objects.
        with prepared.source() as source:
            canonical = parse_bundle(source, max_rows=prepared.max_rows)
            checked = prepare_study(canonical, prepared.vocabulary)
            emit(self.progress, "compatibility")
            capabilities = self.capabilities()
            if 2 in capabilities.upload_report_versions:
                headers["X-PKDB-Report-Version"] = "2"
            if capabilities.processing_version != PROCESSING_VERSION:
                raise CompatibilityError(
                    "Server processing rules differ; install the matching pkdb release and prepare again"
                )
            if capabilities.vocabulary_hash != prepared.vocabulary_hash:
                raise CompatibilityError(
                    "Server vocabulary differs; run pkdb vocabulary sync and prepare again"
                )
            limits = capabilities.upload_limits
            if len(source.files) > limits.max_files:
                fail("file_limit", "Too many source files for this server")
            if limits.max_rows < prepared.max_rows:
                parse_bundle(source, max_rows=limits.max_rows)
            sizes = [path.stat().st_size for path in source.files.values()]
            if any(size > limits.max_attachment_bytes for size in sizes):
                fail("file_limit", "Attachment exceeds the server's byte limit")
            payloads = {
                "study": json.dumps(source.study),
                "reference": json.dumps(source.reference),
            }
            if (
                sum(sizes) + sum(len(value.encode()) for value in payloads.values())
                > limits.max_upload_bytes
            ):
                fail(
                    "file_limit", "Study bundle exceeds the server's upload byte limit"
                )
            headers.update(
                {
                    "X-PKDB-Vocabulary-Hash": prepared.vocabulary_hash,
                    "X-PKDB-Processing-Version": PROCESSING_VERSION,
                }
            )
            with ExitStack() as stack:
                parts: list[
                    tuple[str, tuple[None, str] | tuple[str, BinaryIO, str]]
                ] = [(name, (None, value)) for name, value in payloads.items()]
                parts.extend(
                    (
                        "files",
                        (
                            name,
                            stack.enter_context(path.open("rb")),
                            "application/octet-stream",
                        ),
                    )
                    for name, path in source.files.items()
                )
                response = self._request(
                    "PUT",
                    f"/api/v2/studies/{quote(checked.study.sid, safe='')}",
                    headers=headers,
                    files=parts,
                )
            try:
                body = response.json()
                if isinstance(body, dict) and body.get("report_version") == 2:
                    self.last_upload_report = body
                    payload = body["result"]
                    if isinstance(payload, dict):
                        payload = {
                            key: value
                            for key, value in payload.items()
                            if key in ReplacementResult.model_fields
                        }
                        if "warnings" in payload:
                            payload["warnings"] = _known_report(
                                {"issues": payload["warnings"]}
                            )["issues"]
                    result = ReplacementResult.model_validate(payload)
                else:
                    result = self._model(ReplacementResult, response)
            except ValueError, KeyError, ValidationError, ClientError:
                raise ClientError(
                    "Server returned an invalid upload confirmation",
                    persistence="unknown",
                    stage="save",
                ) from None
            if result.sid != checked.study.sid:
                raise ClientError(
                    "Server did not confirm the uploaded study identifier",
                    persistence="unknown",
                    stage="save",
                )
            emit(self.progress, "complete")
            return result

    def _page[T: BaseModel](
        self, entity: str, model: type[T], filters: dict
    ) -> ResultPage[T]:
        query = query_from_filters(entity, filters)
        response = self._request(
            "POST", "/api/v2/query", json=query.model_dump(mode="json")
        )
        try:
            body = DataPage[dict].model_validate(response.json())
            return ResultPage(
                items=[model.model_validate(item) for item in body.items],
                count=body.total,
                page=body.page,
                pages=max(1, math.ceil(body.total / body.page_size)),
            )
        except ValueError, KeyError, TypeError, ValidationError:
            raise ClientError("Server returned an invalid result page") from None

    def query(self, entity: str, **filters) -> ResultPage:
        models = {
            "studies": StudyResponse,
            "outputs": OutputResponse,
            "measurements": OutputResponse,
            "groups": GroupResponse,
            "individuals": IndividualResponse,
            "interventions": InterventionResponse,
            "references": ReferenceResponse,
        }
        if entity not in models:
            raise ValueError(f"Unsupported query entity: {entity}")
        return self._page(entity, models[entity], filters)

    def download(self, destination: str | Path, **filters) -> Path:
        """Stream an authenticated dataset ZIP to an atomic destination file."""
        headers = self._headers(required=True)
        path = Path(destination)
        temporary = None
        try:
            with self._transport.stream(
                "POST",
                self.endpoint + "/api/v2/exports",
                json=export_from_filters(filters).model_dump(mode="json"),
                headers=headers,
                follow_redirects=False,
            ) as response:
                if not 200 <= response.status_code < 300:
                    response.read()
                    self._check(response)
                if "zip" not in response.headers.get("content-type", ""):
                    raise ClientError("Server did not return a dataset ZIP")
                path.parent.mkdir(parents=True, exist_ok=True)
                with NamedTemporaryFile(dir=path.parent, delete=False) as handle:
                    temporary = Path(handle.name)
                    for chunk in response.iter_bytes():
                        handle.write(chunk)
                temporary.replace(path)
        except httpx2.RequestError:
            raise ClientError(
                "Dataset download failed; destination was not replaced"
            ) from None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return path
