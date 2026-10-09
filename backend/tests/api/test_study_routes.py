"""Study routes by `<substance>/<name>`, and redirects from PKDB identifiers."""

import json
import threading
import time
from contextlib import contextmanager
from copy import deepcopy
from datetime import date

import pytest
from sqlalchemy import select, text, update

from pkdb import Client
from pkdb.studyformat.jsonio import dump_json
from pkdb_server.db.models.studies import Study
from pkdb_server.db.models.users import User
from pkdb_server.services.ingestion import issue_lock, sid_lock
from tests.fixtures.study_folders import multipart, write_study

SID = "caffeine/Example"
PKDB_ID = "PKDB00198"


def format_1(bundle, sid):
    bundle.study["sid"] = sid
    return {
        "files": {
            "study": (None, json.dumps(bundle.study), "application/json"),
            "reference": (None, json.dumps(bundle.reference), "application/json"),
        }
    }


@pytest.fixture
def released(client, creator_headers, tmp_path):
    """A released study format 2 study, private to its curator."""
    folder = write_study(tmp_path / "sources", release=PKDB_ID)
    response = client.put(
        f"/api/v2/studies/{SID}", headers=creator_headers, **multipart(folder)
    )
    assert response.status_code == 201, response.text
    return folder


def test_study_is_served_by_substance_and_name(
    client, creator_headers, admin_headers, released
):
    detail = client.get(f"/api/v1/studies/{SID}/", headers=creator_headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["sid"] == SID
    # Legacy suffix aliases and percent-encoded separators reach the same study.
    for url in (
        f"/api/v1/studies/{SID}.json",
        f"/api/v1/studies/{SID}.json/",
        "/api/v1/studies/caffeine%2FExample/",
    ):
        assert client.get(url, headers=creator_headers).json() == detail.json()
    assert client.get(f"/api/v1/studies/{SID}/").status_code == 404
    study = client.get(f"/api/v2/studies/{SID}", headers=creator_headers)
    assert study.status_code == 200 and study.json()["sid"] == SID
    [row] = client.get("/api/v1/pkdata/studies/", headers=creator_headers).json()[
        "data"
    ]["data"]
    assert row["sid"] == SID
    for suffix in ("/", ".json", ".json/"):
        export = client.get(
            f"/api/v1/pkdata/studies/{SID}{suffix}", headers=creator_headers
        )
        assert export.status_code == 200, export.text
        assert export.json() == row
    assert client.get(f"/api/v1/pkdata/studies/{SID}/").status_code == 404
    access = f"/api/v1/admin/studies/{SID}/access"
    grants = client.get(access, headers=admin_headers)
    assert grants.status_code == 200, grants.text
    changed = {**grants.json(), "access": "public"}
    response = client.put(access, headers=admin_headers, json=changed)
    assert response.status_code == 200, response.text
    assert client.get(access, headers=admin_headers).json() == changed
    assert client.get(f"/api/v1/studies/{SID}/").status_code == 200
    assert client.get(access, headers=creator_headers).status_code == 403


def test_study_response_carries_identity_release_issue_and_review(
    client, creator_headers, tmp_path, valid_bundle
):
    folder = write_study(tmp_path / "sources", release=PKDB_ID, issue=2158)
    review = json.loads((folder / "review.json").read_text())
    [item] = review["items"]
    review["items"].append(
        {
            **item,
            "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2AC",
            "state": "resolved",
            "resolved_by": "curator",
            "resolved": "2026-10-05T11:00:00Z",
        }
    )
    review["items"].append(
        {**item, "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2AD", "kind": "issue"}
    )
    (folder / "review.json").write_text(dump_json(review), encoding="utf-8")
    response = client.put(
        f"/api/v2/studies/{SID}", headers=creator_headers, **multipart(folder)
    )
    assert response.status_code == 201, response.text
    assert (
        client.put(
            "/api/v2/studies/TEST1",
            headers=creator_headers,
            **format_1(valid_bundle, "TEST1"),
        ).status_code
        == 201
    )
    expected = {
        SID: {
            "pkdb_id": PKDB_ID,
            "release_date": "2026-09-28",
            "issue": 2158,
            "review_status": "in_review",
            "open_review_items": 2,
        },
        "TEST1": {
            "pkdb_id": None,
            "release_date": None,
            "issue": None,
            "review_status": None,
            "open_review_items": 0,
        },
    }
    for sid, fields in expected.items():
        detail = client.get(f"/api/v1/studies/{sid}/", headers=creator_headers).json()
        assert {key: detail[key] for key in fields} == fields
        assert detail["sid"] == sid
    rows = client.get("/api/v2/studies", headers=creator_headers).json()["items"]
    assert {row["sid"]: {key: row[key] for key in fields} for row in rows} == expected
    listed = client.get(
        "/api/v1/studies/", headers=creator_headers, params={"pkdb_id": PKDB_ID}
    ).json()["data"]["data"]
    assert [row["sid"] for row in listed] == [SID]


def test_pkdb_identifier_redirects_to_the_study(
    client, creator_headers, admin_headers, released
):
    redirects = {
        f"/api/v1/studies/{PKDB_ID}/": f"/api/v1/studies/{SID}/",
        f"/api/v1/studies/{PKDB_ID}.json": f"/api/v1/studies/{SID}.json",
        f"/api/v1/studies/{PKDB_ID}/?format=json": f"/api/v1/studies/{SID}/?format=json",
        f"/api/v2/studies/{PKDB_ID}": f"/api/v2/studies/{SID}",
        f"/api/v2/studies/{PKDB_ID}/publication": f"/api/v2/studies/{SID}/publication",
        f"/api/v1/pkdata/studies/{PKDB_ID}/": f"/api/v1/pkdata/studies/{SID}/",
    }
    for url, location in redirects.items():
        response = client.get(url, headers=creator_headers, follow_redirects=False)
        assert response.status_code == 308, url
        assert response.headers["location"] == location
        assert response.json()["sid"] == SID
        followed = client.get(url, headers=creator_headers)
        assert followed.status_code == 200, url
        assert followed.json() == client.get(location, headers=creator_headers).json()
        # Only readers of the study learn where it is.
        assert client.get(url, follow_redirects=False).status_code == 404
    access = f"/api/v1/admin/studies/{PKDB_ID}/access"
    for method, arguments in (
        ("get", {}),
        ("put", {"json": {"access": "private", "licence": "closed"}}),
    ):
        response = getattr(client, method)(
            access, headers=admin_headers, follow_redirects=False, **arguments
        )
        assert response.status_code == 308, response.text
        assert response.headers["location"] == f"/api/v1/admin/studies/{SID}/access"
    # Only the administrator learns where the study is.
    response = client.get(access, headers=creator_headers, follow_redirects=False)
    assert response.status_code == 403
    for url in ("/api/v1/studies/PKDB00199/", "/api/v2/studies/PKDB00199"):
        assert client.get(url, headers=creator_headers).status_code == 404


def test_legacy_sid_of_a_renamed_study_redirects(
    client, creator_headers, tmp_path, valid_bundle
):
    response = client.put(
        f"/api/v2/studies/{PKDB_ID}",
        headers=creator_headers,
        **format_1(valid_bundle, PKDB_ID),
    )
    assert response.status_code == 201, response.text
    # Single-segment routes serve study format 1 sids.
    for url in (f"/api/v1/studies/{PKDB_ID}/", f"/api/v2/studies/{PKDB_ID}"):
        response = client.get(url, headers=creator_headers, follow_redirects=False)
        assert response.status_code == 200 and response.json()["sid"] == PKDB_ID
    folder = write_study(tmp_path / "sources", release=PKDB_ID)
    response = client.put(
        f"/api/v2/studies/{SID}", headers=creator_headers, **multipart(folder)
    )
    assert response.json()["renamed_from"] == PKDB_ID
    response = client.get(
        f"/api/v1/studies/{PKDB_ID}/", headers=creator_headers, follow_redirects=False
    )
    assert response.status_code == 308
    assert response.headers["location"] == f"/api/v1/studies/{SID}/"


def test_former_sid_of_a_taken_over_study_redirects(
    client, creator_headers, admin_headers, tmp_path, valid_bundle, session_factory
):
    legacy = "Vilsboll2008"
    valid_bundle.reference["pmid"] = "123"
    response = client.put(
        f"/api/v2/studies/{legacy}",
        headers=creator_headers,
        **format_1(valid_bundle, legacy),
    )
    assert response.status_code == 201, response.text
    folder = write_study(tmp_path / "sources")
    response = client.put(
        f"/api/v2/studies/{SID}", headers=creator_headers, **multipart(folder)
    )
    assert response.json()["renamed_from"] == legacy
    redirects = {
        f"/api/v1/studies/{legacy}/": f"/api/v1/studies/{SID}/",
        f"/api/v1/studies/{legacy}.json": f"/api/v1/studies/{SID}.json",
        f"/api/v2/studies/{legacy}": f"/api/v2/studies/{SID}",
        f"/api/v2/studies/{legacy}/publication": f"/api/v2/studies/{SID}/publication",
        f"/api/v1/pkdata/studies/{legacy}/": f"/api/v1/pkdata/studies/{SID}/",
    }
    for url, location in redirects.items():
        response = client.get(url, headers=creator_headers, follow_redirects=False)
        assert response.status_code == 308, url
        assert response.headers["location"] == location
        assert client.get(url, headers=creator_headers).status_code == 200, url
        # Only readers of the study learn where it is.
        assert client.get(url, follow_redirects=False).status_code == 404, url
    access = f"/api/v1/admin/studies/{legacy}/access"
    response = client.get(access, headers=admin_headers, follow_redirects=False)
    assert response.status_code == 308, response.text
    assert response.headers["location"] == f"/api/v1/admin/studies/{SID}/access"
    api = Client(
        endpoint="http://testserver",
        api_key=creator_headers["Authorization"].split(" ", 1)[1],
        transport=client,
    )
    assert api.studies.get(legacy).sid == SID


def test_live_sid_wins_over_a_legacy_sid(
    client, creator_headers, tmp_path, valid_bundle, session_factory
):
    response = client.put(
        "/api/v2/studies/TEST1",
        headers=creator_headers,
        **format_1(valid_bundle, "TEST1"),
    )
    assert response.status_code == 201, response.text
    folder = write_study(tmp_path / "sources", pmid="456")
    response = client.put(
        f"/api/v2/studies/{SID}", headers=creator_headers, **multipart(folder)
    )
    assert response.status_code == 201, response.text
    # Uploads never give a live sid as a legacy sid; the database could.
    with session_factory.begin() as session:
        session.execute(
            update(Study).where(Study.sid == SID).values(legacy_sid="TEST1")
        )
    for url in ("/api/v1/studies/TEST1/", "/api/v2/studies/TEST1"):
        response = client.get(url, headers=creator_headers, follow_redirects=False)
        assert response.status_code == 200, url
        assert response.json()["sid"] == "TEST1"


def test_study_filters_accept_sids_with_slashes(
    client, creator_headers, released, valid_bundle
):
    assert (
        client.put(
            "/api/v2/studies/TEST1",
            headers=creator_headers,
            **format_1(valid_bundle, "TEST1"),
        ).status_code
        == 201
    )
    page = client.get(
        "/api/v1/studies/",
        headers=creator_headers,
        params={"sid__in": f"{SID}__TEST1"},
    ).json()["data"]
    assert sorted(row["sid"] for row in page["data"]) == sorted([SID, "TEST1"])
    overview = client.get(
        "/api/v1/filter/",
        headers=creator_headers,
        params={"studies__sid__in": SID},
    ).json()
    assert overview["studies"] == 1
    rows = client.get(
        "/api/v1/pkdata/studies/",
        headers=creator_headers,
        params={"uuid": overview["uuid"]},
    ).json()["data"]["data"]
    assert [row["sid"] for row in rows] == [SID]
    rows = client.get(
        "/api/v2/studies", headers=creator_headers, params={"study_sid": SID}
    ).json()["items"]
    assert [row["sid"] for row in rows] == [SID]


def test_reference_with_a_doi_is_served(client, creator_headers, tmp_path):
    folder = write_study(tmp_path / "sources")
    doi = "10.1234/abc"
    study = json.loads((folder / "study.json").read_text())
    study["reference"] = {"doi": doi}
    reference = json.loads((folder / "reference.json").read_text())
    reference.update(sid=doi, doi=doi)
    del reference["pmid"]
    replaced = {
        "study.json": dump_json(study).encode(),
        "reference.json": dump_json(reference).encode(),
    }
    response = client.put(
        f"/api/v2/studies/{SID}",
        headers=creator_headers,
        **multipart(folder, json_files=replaced),
    )
    assert response.status_code == 201, response.text
    for url in (f"/api/v1/references/{doi}/", "/api/v1/references/10.1234%2Fabc/"):
        response = client.get(url, headers=creator_headers)
        assert response.status_code == 200, url
        assert (response.json()["sid"], response.json()["doi"]) == (doi, doi)


@contextmanager
def lock_holder(session_factory):
    """A connection that takes locks; closing it releases them, also on failure."""
    with session_factory.kw["bind"].connect() as connection:
        try:
            yield connection
        finally:
            connection.invalidate()


def advisory(connection, operation, name):
    connection.execute(
        text(f"SELECT pg_advisory_{operation}(:key)"), {"key": sid_lock(name)}
    )


def wait_for_waiter(connection, name):
    """Wait until a transaction waits for the advisory lock of `name`."""
    key = sid_lock(name) & 0xFFFF_FFFF_FFFF_FFFF
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if connection.scalar(
            text(
                "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' "
                "AND NOT granted AND classid = :high AND objid = :low "
                "AND objsubid = 1"
            ),
            {"high": key >> 32, "low": key & 0xFFFF_FFFF},
        ):
            return
        time.sleep(0.01)
    raise AssertionError(f"Nothing waits for the lock of {name}")


def start_update(client, headers, url, data):
    responses = []
    worker = threading.Thread(
        target=lambda: responses.append(client.put(url, headers=headers, json=data))
    )
    worker.start()
    return worker, responses


def test_access_update_waits_for_publications_of_the_released_study(
    client, admin_headers, released, session_factory
):
    """An access update locks the sid and the PKDB identifier like a publication.

    A rename of the study locks its new sid and its PKDB identifier, not the
    sid that the administrator names.
    """
    url = f"/api/v1/admin/studies/{SID}/access"
    grants = client.get(url, headers=admin_headers).json()
    with lock_holder(session_factory) as other:
        advisory(other, "lock", PKDB_ID)
        worker, responses = start_update(client, admin_headers, url, grants)
        wait_for_waiter(other, PKDB_ID)
        assert not responses
        advisory(other, "unlock", PKDB_ID)
    worker.join(timeout=30)
    [response] = responses
    assert response.status_code == 200, response.text


def test_access_update_locks_a_pkdb_identifier_released_meanwhile(
    client, creator_headers, admin_headers, tmp_path, session_factory
):
    folder = write_study(tmp_path / "sources")
    response = client.put(
        f"/api/v2/studies/{SID}", headers=creator_headers, **multipart(folder)
    )
    assert response.status_code == 201, response.text
    url = f"/api/v1/admin/studies/{SID}/access"
    grants = client.get(url, headers=admin_headers).json()
    with lock_holder(session_factory) as other:
        advisory(other, "lock", SID)
        worker, responses = start_update(client, admin_headers, url, grants)
        wait_for_waiter(other, SID)
        # The study is released while the update waits for its sid.
        other.execute(
            update(Study)
            .where(Study.sid == SID)
            .values(pkdb_id=PKDB_ID, release_date=date(2026, 9, 28))
        )
        other.commit()
        # The update notices the change before it locks the account.
        other.execute(
            select(User.id).where(User.username == "mkoenig").with_for_update()
        )
        advisory(other, "lock", PKDB_ID)
        advisory(other, "unlock", SID)
        # It starts again and locks the new PKDB identifier too.
        wait_for_waiter(other, PKDB_ID)
        assert not responses
        advisory(other, "unlock", PKDB_ID)
        other.commit()
    worker.join(timeout=30)
    [response] = responses
    assert response.status_code == 200, response.text


def test_access_update_gives_up_when_the_study_keeps_changing(
    client, admin_headers, released, monkeypatch
):
    from pkdb_server.api import management

    attempts = []

    def without_pkdb_id(session, sid, pkdb_id):
        # As if the PKDB identifier changed before every attempt took its locks.
        attempts.append(sid)
        return {sid}

    monkeypatch.setattr(management, "lock_publication", without_pkdb_id)
    url = f"/api/v1/admin/studies/{SID}/access"
    grants = client.get(url, headers=admin_headers).json()
    response = client.put(
        url, headers=admin_headers, json={**grants, "access": "public"}
    )
    assert response.status_code == 409, response.text
    assert attempts == [SID] * management.LOCK_ATTEMPTS
    assert client.get(url, headers=admin_headers).json() == grants


def test_client_reads_follow_the_redirect(client, creator_headers, released):
    api = Client(
        endpoint="http://testserver",
        api_key=creator_headers["Authorization"].split(" ", 1)[1],
        transport=client,
    )
    assert api.studies.get(PKDB_ID).sid == SID
    assert api.publication(PKDB_ID).sid == SID


def listed_sids(client, headers, **params):
    response = client.get("/api/v1/studies/", headers=headers, params=params)
    assert response.status_code == 200, response.text
    return sorted(row["sid"] for row in response.json()["data"]["data"])


def test_study_search_finds_a_released_study_by_its_pkdb_identifier(
    client, creator_headers, released
):
    for key in ("search", "search_multi_match"):
        for term in (PKDB_ID, PKDB_ID.lower()):
            assert listed_sids(client, creator_headers, **{key: term}) == [SID]
    assert listed_sids(client, creator_headers, search="PKDB00199") == []
    # The name and the sid keep working.
    assert listed_sids(client, creator_headers, search="Example") == [SID]


def test_pkdb_identifier_filter_matches_released_and_format_1_studies(
    client, creator_headers, released, valid_bundle
):
    first = format_1(valid_bundle, "PKDB00057")
    other = deepcopy(valid_bundle)
    other.reference["sid"] = other.study["reference"] = "REF2"
    second = format_1(other, "OTHER1")
    for sid, parts in (("PKDB00057", first), ("OTHER1", second)):
        response = client.put(
            f"/api/v2/studies/{sid}", headers=creator_headers, **parts
        )
        assert response.status_code == 201, response.text
    filtered = {
        "PKDB00198": [SID],
        "PKDB00057": ["PKDB00057"],
        # A sid that is not a PKDB identifier is not mistaken for one.
        "OTHER1": [],
        SID: [],
    }
    for identifier, expected in filtered.items():
        assert (
            listed_sids(client, creator_headers, pkdb_id__in=identifier) == expected
        ), identifier
    assert listed_sids(
        client, creator_headers, pkdb_id__in="PKDB00057__PKDB00198"
    ) == sorted(["PKDB00057", SID])
    # The research filter selects them the same way.
    for identifier, expected in filtered.items():
        response = client.get(
            "/api/v1/filter/",
            headers=creator_headers,
            params={"format": "json", "studies__pkdb_id__in": identifier},
        )
        assert response.status_code == 200, response.text
        assert response.json()["studies"] == len(expected), identifier


LEGACY = "Vilsboll2008"


@pytest.fixture
def legacy_study(client, creator_headers, valid_bundle):
    """A study format 1 study of the publication of write_study."""
    valid_bundle.reference["pmid"] = "123"
    response = client.put(
        f"/api/v2/studies/{LEGACY}",
        headers=creator_headers,
        **format_1(valid_bundle, LEGACY),
    )
    assert response.status_code == 201, response.text


def test_takeover_waits_for_the_lock_of_the_former_sid(
    client, creator_headers, tmp_path, legacy_study, session_factory
):
    folder = write_study(tmp_path / "sources")
    responses = []
    with lock_holder(session_factory) as other:
        # A study format 1 upload or access update of the former sid holds it.
        advisory(other, "lock", LEGACY)
        worker = threading.Thread(
            target=lambda: responses.append(
                client.put(
                    f"/api/v2/studies/{SID}",
                    headers=creator_headers,
                    **multipart(folder),
                )
            )
        )
        worker.start()
        wait_for_waiter(other, LEGACY)
        assert not responses
        advisory(other, "unlock", LEGACY)
    worker.join(timeout=30)
    [response] = responses
    assert response.status_code == 200, response.text
    assert response.json()["renamed_from"] == LEGACY


def test_takeover_starts_again_when_its_study_changed_before_the_locks(
    client, creator_headers, tmp_path, legacy_study, monkeypatch
):
    from pkdb_server.services import ingestion

    folder = write_study(tmp_path / "sources")
    calls = []

    def unlocked(session, study):
        # As if the study format 1 study appeared after its sid was read.
        calls.append(study.sid)
        return set()

    monkeypatch.setattr(ingestion, "former_sids", unlocked)
    response = client.put(
        f"/api/v2/studies/{SID}", headers=creator_headers, **multipart(folder)
    )
    assert response.status_code == 409, response.text
    assert response.json()["detail"] == (
        "The study changed during the upload; upload again"
    )
    assert calls == [SID] * ingestion.LOCK_ATTEMPTS
    monkeypatch.undo()
    real = ingestion.former_sids
    first = []

    def once(session, study):
        # Only the first attempt misses the former sid.
        first.append(study.sid)
        return set() if len(first) == 1 else real(session, study)

    monkeypatch.setattr(ingestion, "former_sids", once)
    response = client.put(
        f"/api/v2/studies/{SID}", headers=creator_headers, **multipart(folder)
    )
    assert response.status_code == 200, response.text
    assert response.json()["renamed_from"] == LEGACY
    assert first == [SID, SID]


@pytest.fixture
def moved(client, creator_headers, tmp_path):
    """The study caffeine/Before with issue 4711, and its folder moved to caffeine/After."""
    before = write_study(tmp_path / "before", "Before", issue=4711)
    response = client.put(
        "/api/v2/studies/caffeine/Before",
        headers=creator_headers,
        **multipart(before),
    )
    assert response.status_code == 201, response.text
    return write_study(tmp_path / "after", "After", issue=4711)


def start_upload(client, headers, folder):
    responses = []
    worker = threading.Thread(
        target=lambda: responses.append(
            client.put(
                f"/api/v2/studies/{folder.parent.name}/{folder.name}",
                headers=headers,
                **multipart(folder),
            )
        )
    )
    worker.start()
    return worker, responses


def test_issue_takeover_waits_for_the_lock_of_the_former_sid(
    client, creator_headers, moved, session_factory
):
    with lock_holder(session_factory) as other:
        # An upload or access update of the moved study holds its sid.
        advisory(other, "lock", "caffeine/Before")
        worker, responses = start_upload(client, creator_headers, moved)
        wait_for_waiter(other, "caffeine/Before")
        assert not responses
        advisory(other, "unlock", "caffeine/Before")
    worker.join(timeout=30)
    [response] = responses
    assert response.status_code == 200, response.text
    assert response.json()["renamed_from"] == "caffeine/Before"


def test_uploads_that_set_one_issue_wait_for_each_other(
    client, creator_headers, tmp_path, session_factory
):
    folder = write_study(tmp_path / "sources", issue=4711)
    with lock_holder(session_factory) as other:
        # Another upload that sets issue 4711 holds its lock.
        advisory(other, "lock", issue_lock(4711))
        worker, responses = start_upload(client, creator_headers, folder)
        wait_for_waiter(other, issue_lock(4711))
        assert not responses
        advisory(other, "unlock", issue_lock(4711))
    worker.join(timeout=30)
    [response] = responses
    assert response.status_code == 201, response.text


def test_issue_takeover_starts_again_when_its_study_changed_before_the_locks(
    client, creator_headers, moved, monkeypatch
):
    from pkdb_server.services import ingestion

    calls = []

    def unlocked(session, study):
        # As if the study with the issue was moved after its sid was read.
        calls.append(study.sid)
        return set()

    monkeypatch.setattr(ingestion, "former_sids", unlocked)
    url = "/api/v2/studies/caffeine/After"
    response = client.put(url, headers=creator_headers, **multipart(moved))
    assert response.status_code == 409, response.text
    assert response.json()["detail"] == (
        "The study changed during the upload; upload again"
    )
    assert calls == ["caffeine/After"] * ingestion.LOCK_ATTEMPTS
    monkeypatch.undo()
    real = ingestion.former_sids
    first = []

    def once(session, study):
        # Only the first attempt misses the sid of the study with the issue.
        first.append(study.sid)
        return set() if len(first) == 1 else real(session, study)

    monkeypatch.setattr(ingestion, "former_sids", once)
    response = client.put(url, headers=creator_headers, **multipart(moved))
    assert response.status_code == 200, response.text
    assert response.json()["renamed_from"] == "caffeine/Before"
    assert first == ["caffeine/After"] * 2
