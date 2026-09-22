"""Legacy upload transport over owned staging and atomic publication."""

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from pkdb.db.models.drafts import LegacyFileHandle
from pkdb.schemas.legacy import FinalizeRequest
from pkdb.schemas.validation import fail
from pkdb.services.drafts import DraftConflict


def require_upload_account(request: Request):
    request.app.state.principal(request)


router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_upload_account)])


async def payload(request):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                fail("duplicate_json_key", "Duplicate JSON key")
            result[key] = value
        return result

    def nonfinite(value):
        fail("invalid_number", "JSON numbers must be finite")

    try:
        value = json.loads(
            await request.body(), object_pairs_hook=unique, parse_constant=nonfinite
        )
    except ValueError, RecursionError:
        fail("invalid_json", "Malformed JSON payload")
    if not isinstance(value, dict):
        fail("invalid_json", "Expected a JSON object")
    return value


async def invoke(request, method, *args):
    actor = await run_in_threadpool(request.app.state.principal, request)
    service = request.app.state.drafts
    try:
        return await run_in_threadpool(getattr(service, method), *args, principal=actor)
    except DraftConflict as error:
        raise HTTPException(409, str(error)) from None
    except LookupError:
        raise HTTPException(404, "Draft or study unavailable") from None


@router.post("/_references/", status_code=201)
async def stage_reference(request: Request):
    reference = await invoke(request, "stage_reference", await payload(request))
    return reference_response(reference)


def reference_response(reference):
    keys = (
        "pmid",
        "sid",
        "name",
        "doi",
        "title",
        "abstract",
        "journal",
        "date",
        "authors",
    )
    return {
        key: str(reference[key]) if key in {"pmid", "sid"} else reference[key]
        for key in keys
        if reference.get(key) is not None
    }


@router.get("/_references/{sid}/")
async def read_reference(sid: str, request: Request):
    return reference_response(await invoke(request, "read_reference", sid))


@router.patch("/_references/{sid}/")
async def patch_reference(sid: str, request: Request):
    return reference_response(
        await invoke(request, "patch_reference", sid, await payload(request))
    )


@router.get("/_studies/{sid}/")
async def read_draft(sid: str, request: Request):
    return await invoke(request, "read", sid)


@router.post("/_studies/", status_code=201)
async def begin_study(request: Request):
    core = await payload(request)
    actor = await run_in_threadpool(request.app.state.principal, request)
    try:
        return await run_in_threadpool(
            request.app.state.drafts.begin, core.get("sid"), actor, core
        )
    except DraftConflict as error:
        raise HTTPException(409, str(error)) from None


@router.patch("/_studies/{sid}/")
async def patch_study(sid: str, request: Request):
    values = await payload(request)
    actor = await run_in_threadpool(request.app.state.principal, request)
    try:
        return await run_in_threadpool(
            request.app.state.drafts.patch, sid, actor, values
        )
    except DraftConflict as error:
        raise HTTPException(409, str(error)) from None
    except LookupError:
        raise HTTPException(404, "Draft unavailable") from None


@router.post("/update_index/")
async def finalize_study(body: FinalizeRequest, request: Request):
    await invoke(request, "finalize", body.sid)
    return {"success": "True"}


@router.post("/_datafiles/", status_code=201)
async def stage_file(request: Request):
    actor = await run_in_threadpool(request.app.state.principal, request)
    async with request.form(max_files=1, max_fields=0) as form:
        if set(form) != {"file"} or len(form.getlist("file")) != 1:
            fail("invalid_file", "Exactly one file is required")
        upload = form["file"]
        if not isinstance(upload, UploadFile) or not upload.filename:
            fail("invalid_file", "A named attachment is required")

        def stage():
            store = request.app.state.file_store
            staged = store.stage(actor, upload.filename, upload.file)
            with store.session_factory.begin() as session:
                alias = LegacyFileHandle(file_id=staged.id)
                session.add(alias)
                session.flush()
                return {
                    "file": str(
                        request.url_for(
                            "download",
                            attachment_id=staged.id,
                            filename=staged.original_name,
                        )
                    ),
                    "id": alias.id,
                }

        return await run_in_threadpool(stage)


@router.get("/_datafiles/{identifier}/", name="legacy_file")
def legacy_file(identifier: int, request: Request):
    from sqlalchemy import select

    from pkdb.db.models.files import StoredFile
    from pkdb.services.authorization import AuthorizationDenied

    actor = request.app.state.principal(request)
    store = request.app.state.file_store
    with store.session_factory() as session:
        row = session.scalar(
            select(StoredFile)
            .join(LegacyFileHandle, LegacyFileHandle.file_id == StoredFile.id)
            .where(LegacyFileHandle.id == identifier)
        )
        if row is None:
            raise HTTPException(404, "File unavailable")
        if row.owner_id != actor.user_id:
            raise AuthorizationDenied("Attachment handle unavailable")
        return {
            "file": str(
                request.url_for(
                    "download", attachment_id=row.id, filename=row.original_name
                )
            ),
            "id": identifier,
        }


@router.delete("/_studies/{sid}/", status_code=204)
async def delete_study(sid: str, request: Request):
    await invoke(request, "delete", sid)
