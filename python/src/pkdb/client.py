"""Synchronous, typed HTTP API with explicit offline preparation."""

import json
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
    ):
        endpoint = endpoint or os.environ.get("PKDB_ENDPOINT")
        if not endpoint:
            raise ValueError("Set PKDB_ENDPOINT or pass endpoint")
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
            if isinstance(body, dict) and isinstance(body.get("issues"), list):
                report = ValidationReport.model_validate(
                    {key: value for key, value in body.items() if key != "valid"}
                )
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
        raise error(
            message,
            status_code=response.status_code,
            report=report,
        )

    def _request(self, method, path, *, headers=None, **kwargs):
        request_headers = {**self._headers(), **(headers or {})}
        try:
            response = self._transport.request(
                method,
                self.endpoint + path,
                headers=request_headers,
                follow_redirects=False,
                **kwargs,
            )
        except httpx2.RequestError:
            message = "PK-DB request failed"
            if method != "GET":
                message += (
                    "; upload outcome may be unknown. Inspect the study before retrying"
                )
            raise ClientError(message) from None
        self._check(response)
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
        prepared = (
            study
            if isinstance(study, PreparedBundle)
            else prepare(study, vocabulary=self._local_vocabulary())
        )
        headers = self._headers(required=True)
        # Detect file changes and validate again against the captured vocabulary
        # before contacting the server. Never trust mutated Pydantic objects.
        with prepared.source() as source:
            canonical = parse_bundle(source, max_rows=prepared.max_rows)
            checked = prepare_study(canonical, prepared.vocabulary)
            capabilities = self.capabilities()
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
            result = self._model(ReplacementResult, response)
            if result.sid != checked.study.sid:
                raise ClientError(
                    "Server did not confirm the uploaded study identifier"
                )
            return result

    @staticmethod
    def _params(filters: dict) -> dict:
        params = {}
        for key, value in filters.items():
            if isinstance(value, (list, tuple)):
                value = ",".join(str(item) for item in value)
            elif isinstance(value, bool):
                value = str(value).lower()
            if value is not None:
                params[key] = value
        return params

    def _page[T: BaseModel](
        self, entity: str, model: type[T], filters: dict
    ) -> ResultPage[T]:
        params = self._params(filters)
        response = self._request("GET", f"/api/v1/{entity}/", params=params)
        try:
            body = response.json()
            return ResultPage(
                items=[model.model_validate(item) for item in body["data"]["data"]],
                count=body["data"]["count"],
                page=body["current_page"],
                pages=body["last_page"],
            )
        except ValueError, KeyError, TypeError, ValidationError:
            raise ClientError("Server returned an invalid result page") from None

    def query(self, entity: str, **filters) -> ResultPage:
        models = {
            "studies": StudyResponse,
            "outputs": OutputResponse,
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
                "GET",
                self.endpoint + "/api/v1/filter/",
                params={**self._params(filters), "download": "true"},
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
