"""Retain attachment security coverage independently of removed MCP write tools."""

import io
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from pkdb.schemas.bundle import StagedBundle
from pkdb.schemas.validation import StudyValidationError
from pkdb_server.db.models.files import StoredFile
from pkdb_server.services.authorization import AuthorizationDenied
from pkdb_server.services.bundles import materialize_bundle


@pytest.mark.parametrize(
    "case", ["owner", "duplicate", "size", "expired", "corrupt", "path"]
)
def test_invalid_staged_handles(ingestion_context, valid_bundle, session_factory, case):
    ingestion, principal = ingestion_context
    store = ingestion.file_store
    staged = store.stage(principal, "figure.png", io.BytesIO(b"original"))
    handles = [staged.id]
    if case == "owner":
        principal = principal.model_copy(update={"user_id": -1})
    elif case == "duplicate":
        handles *= 2
    elif case == "size":
        ingestion.settings.upload_max_bytes = 4
    elif case == "expired":
        with session_factory.begin() as session:
            session.get(StoredFile, staged.id).expires_at = datetime.now(
                UTC
            ) - timedelta(seconds=1)
    elif case == "corrupt":
        store.path(staged.storage_key).write_bytes(b"corrupt!")
    else:
        handles = ["/etc/passwd"]
    expected = {
        "duplicate": "invalid_handles",
        "size": "file_limit",
        "corrupt": "source_changed",
    }.get(case)
    error_type = (
        StudyValidationError
        if expected
        else (ValidationError if case == "path" else AuthorizationDenied)
    )
    with pytest.raises(error_type) as caught:
        bundle = StagedBundle(
            study=valid_bundle.study, reference=valid_bundle.reference, handles=handles
        )
        with materialize_bundle(bundle, principal, store, ingestion.settings):
            pytest.fail("Invalid attachment was accepted")
    if expected:
        assert isinstance(caught.value, StudyValidationError)
        assert caught.value.report.issues[0].code == expected
