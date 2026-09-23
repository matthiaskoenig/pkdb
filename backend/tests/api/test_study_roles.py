"""Exercise role changes through the upload interface used by curator scripts."""

import json

from sqlalchemy import delete, select

from pkdb_server.db.models.studies import Study, StudyGrant
from pkdb_server.db.models.users import User
from pkdb_server.services.authentication import issue_token


def payload(bundle):
    return {
        "files": {
            name: (None, json.dumps(getattr(bundle, name)), "application/json")
            for name in ("study", "reference")
        }
    }


def test_reviewer_needs_private_assignment_and_demoted_creator_cannot(
    client, creator_headers, valid_bundle, ingestion_context, session_factory
):
    url = "/api/v2/studies/" + valid_bundle.study["sid"]
    assert (
        client.put(url, headers=creator_headers, **payload(valid_bundle)).status_code
        == 201
    )
    with session_factory.begin() as session:
        reviewer = User(username="reviewer", role="reviewer", active=True)
        session.add(reviewer)
        session.flush()
        token = issue_token(reviewer, session)
    response = client.put(
        url, headers={"Authorization": f"Bearer {token}"}, **payload(valid_bundle)
    )
    assert response.status_code == 403, response.text
    with session_factory.begin() as session:
        study = session.scalar(
            select(Study).where(Study.sid == valid_bundle.study["sid"])
        )
        reviewer = session.scalar(select(User).where(User.username == "reviewer"))
        session.add(StudyGrant(study_id=study.id, user_id=reviewer.id, role="curator"))
    assert (
        client.put(
            url, headers={"Authorization": f"Bearer {token}"}, **payload(valid_bundle)
        ).status_code
        == 200
    )
    with session_factory.begin() as session:
        session.get(User, ingestion_context[1].user_id).role = "user"
    response = client.put(url, headers=creator_headers, **payload(valid_bundle))
    assert response.status_code == 403, response.text


def test_contributor_payload_cannot_grant_access_but_writer_can_publish(
    client, creator_headers, valid_bundle, session_factory
):
    with session_factory.begin() as session:
        other = User(username="other", role="curator", active=True)
        session.add(other)
        session.flush()
        other_id = other.id
        token = issue_token(other, session)
    valid_bundle.study["curators"].append({"user": "other"})
    url = "/api/v2/studies/" + valid_bundle.study["sid"]
    assert (
        client.put(url, headers=creator_headers, **payload(valid_bundle)).status_code
        == 201
    )
    assert (
        client.put(
            url, headers={"Authorization": f"Bearer {token}"}, **payload(valid_bundle)
        ).status_code
        == 403
    )
    with session_factory.begin() as session:
        study = session.scalar(
            select(Study).where(Study.sid == valid_bundle.study["sid"])
        )
        session.add(StudyGrant(study_id=study.id, user_id=other_id, role="curator"))
    valid_bundle.study["curators"] = [{"user": "curator"}]
    assert (
        client.put(url, headers=creator_headers, **payload(valid_bundle)).status_code
        == 200
    )
    assert (
        client.put(
            url, headers={"Authorization": f"Bearer {token}"}, **payload(valid_bundle)
        ).status_code
        == 200
    )
    valid_bundle.study["access"] = "public"
    assert (
        client.put(url, headers=creator_headers, **payload(valid_bundle)).status_code
        == 200
    )
    valid_bundle.study["access"] = "private"
    assert (
        client.put(url, headers=creator_headers, **payload(valid_bundle)).status_code
        == 200
    )
    with session_factory.begin() as session:
        session.execute(delete(StudyGrant).where(StudyGrant.user_id == other_id))
    assert (
        client.put(
            url, headers={"Authorization": f"Bearer {token}"}, **payload(valid_bundle)
        ).status_code
        == 403
    )
