from datetime import UTC, date, datetime

from pkdb.migration.metadata import review, study_metadata
from pkdb.schemas.review import Release
from pkdb.studyformat.models import canonical_review_json, canonical_study_json

V1 = {
    "sid": "PKDB00198",
    "name": "Harder1988",
    "reference": "3402561",
    "date": "2020-05-05",
    "creator": "mkoenig",
    "curators": [["mkoenig", 1], ["janekg", 0.5], "dimitra"],
    "collaborators": ["Jan Grzegorzewski"],
    "licence": "closed",
    "access": "public",
    "descriptions": ["Caffeine pharmacokinetics.\nSecond line."],
    "comments": [["janekg", "Check Fig2"], "No user"],
    "groupset": {"descriptions": ["Healthy volunteers"], "groups": []},
    "individualset": {"comments": [["mkoenig", "Ages from Tab1"]], "individuals": []},
    "outputset": {"descriptions": ["Plasma"], "outputs": []},
}
REFERENCE = {
    "sid": "3402561",
    "name": "Harder1988",
    "pmid": "3402561",
    "doi": "10.1111/x.1",
}


def test_study_json_from_v1_metadata():
    metadata, decisions = study_metadata(
        V1,
        REFERENCE,
        Release(pkdb_id="PKDB00198", date=date(2020, 5, 5)),
        creator_fallback="mkoenig",
    )
    assert metadata.reference is not None
    assert (metadata.reference.pmid, metadata.reference.doi) == (
        "3402561",
        "10.1111/x.1",
    )
    assert metadata.creator == "mkoenig"
    assert [(c.user, c.rating) for c in metadata.curators] == [
        ("mkoenig", 1),
        ("janekg", 0.5),
        ("dimitra", 0),
    ]
    assert metadata.collaborators == ["Jan Grzegorzewski"]
    assert (metadata.licence, metadata.access) == ("closed", "public")
    assert metadata.release is not None and metadata.release.pkdb_id == "PKDB00198"
    # Line breaks become spaces: study.json texts are single lines in the app.
    assert metadata.descriptions == ["Caffeine pharmacokinetics. Second line."]
    # A comment without a user is the creator's.
    assert [(c.user, c.text) for c in metadata.comments] == [
        ("janekg", "Check Fig2"),
        ("mkoenig", "No user"),
    ]
    # groupset and individualset both describe subjects.
    assert metadata.notes["subjects"].descriptions == ["Healthy volunteers"]
    assert [c.text for c in metadata.notes["subjects"].comments] == ["Ages from Tab1"]
    assert metadata.notes["outputs"].descriptions == ["Plasma"]
    assert decisions == []
    canonical_study_json(metadata)  # serializes


def test_a_v1_date_other_than_the_release_date_is_a_decision():
    _, decisions = study_metadata(
        V1,
        REFERENCE,
        Release(pkdb_id="PKDB00198", date=date(2021, 1, 1)),
        creator_fallback="mkoenig",
    )
    assert [d.kind for d in decisions] == ["registry_date"]
    assert "2020-05-05" in decisions[0].detail and "2021-01-01" in decisions[0].detail


def test_the_pubmed_id_of_study_json_wins_over_the_snapshot():
    # reference.json describes another publication: its DOI is not kept either.
    snapshot = {**REFERENCE, "sid": "999", "pmid": "999", "doi": "10.1111/other"}
    metadata, _ = study_metadata(V1, snapshot, None, creator_fallback="mkoenig")
    assert metadata.reference is not None
    assert (metadata.reference.pmid, metadata.reference.doi) == ("3402561", None)


def test_a_study_without_creator_takes_the_fallback_and_a_decision():
    v1 = {key: value for key, value in V1.items() if key != "creator"}
    metadata, decisions = study_metadata(
        v1,
        REFERENCE,
        Release(pkdb_id="PKDB00198", date=date(2020, 5, 5)),
        creator_fallback="mkoenig",
    )
    assert metadata.creator == "mkoenig"
    assert [(d.kind, d.detail) for d in decisions] == [
        ("creator_fallback", "study.json has no creator; mkoenig is the creator")
    ]


def test_a_public_study_without_release_becomes_private():
    v1 = {**V1, "sid": "Harder1988"}
    metadata, decisions = study_metadata(v1, REFERENCE, None, creator_fallback="x")
    assert metadata.access == "private"
    assert [(d.kind, d.detail) for d in decisions] == [
        ("access_private", "Public study without a release becomes private")
    ]


def test_a_reference_without_pmid_or_doi_is_a_manual_reference():
    v1 = {**V1, "reference": "Harder1988"}
    metadata, _ = study_metadata(
        v1, {"sid": "Harder1988", "name": "Harder1988"}, None, creator_fallback="x"
    )
    assert metadata.reference is None


def test_registered_studies_are_approved_by_the_approver_on_the_release_date():
    released = review(Release(pkdb_id="PKDB00198", date=date(2020, 5, 5)), "mkoenig")
    assert released.status == "approved"
    assert released.reviewers == ["mkoenig"]
    assert released.approved_by == "mkoenig"
    assert released.approved == datetime(2020, 5, 5, tzinfo=UTC)
    assert review(None, "mkoenig").status == "draft"
    assert review(None, None).reviewers == []
    canonical_review_json(released)
