"""Study and reference summaries shown in the local curation interface."""

import json

from pkdb.curation.metadata import profile, reference_summary, study_summary


def test_known_curator_resolves_bundled_profile_and_avatar():
    known = profile("MKOENIG")
    assert known["username"] == "mkoenig"
    assert known["display_name"] == "Matthias König"
    assert known["title"] == "Prof. Dr."
    assert known["avatar_url"] == "/static/avatars/matthias_koenig.webp"
    unknown = profile("someone-new")
    assert unknown == {
        "username": "someone-new",
        "display_name": "someone-new",
        "title": None,
        "affiliation": None,
        "avatar_url": None,
    }


def test_study_summary_lists_curators_and_entry_counts():
    summary = study_summary(
        {
            "sid": "PKDB00001",
            "name": "Example2020",
            "date": "2025-11-09",
            "reference": 123,
            "licence": "open",
            "access": "public",
            "creator": "mkoenig",
            "curators": [["mkoenig", 2.5], "someone-new", {"username": "x"}],
            "collaborators": None,
            "groupset": {"groups": [{}, {}], "descriptions": ["d"]},
            "individualset": {"individuals": []},
            "interventionset": {"interventions": [{}]},
            "outputset": {"outputs": [{}, {}, {}]},
        }
    )
    assert summary["sid"] == "PKDB00001"
    assert summary["reference"] == "123"
    assert summary["creator"]["display_name"] == "Matthias König"
    assert [(c["username"], c["score"]) for c in summary["curators"]] == [
        ("mkoenig", 2.5),
        ("someone-new", None),
    ]
    assert summary["collaborators"] == []
    assert summary["counts"] == {
        "groups": 2,
        "individuals": 0,
        "interventions": 1,
        "outputs": 3,
        "data": 0,
    }


def test_study_summary_tolerates_invalid_values():
    summary = study_summary({"creator": 5, "curators": "mkoenig", "groupset": []})
    assert summary["creator"] is None
    assert [c["username"] for c in summary["curators"]] == ["mkoenig"]
    assert summary["counts"]["groups"] == 0
    assert summary["reference"] is None


def test_reference_summary(tmp_path):
    assert reference_summary(tmp_path) is None
    path = tmp_path / "reference.json"
    path.write_text("{broken")
    assert reference_summary(tmp_path) == {"error": "reference.json is not valid JSON"}
    path.write_text(
        json.dumps(
            {
                "sid": 123,
                "pmid": 123,
                "doi": "10.1/x",
                "title": "A title",
                "journal": "Journal",
                "date": "2020-03-01",
                "abstract": "Text",
                "authors": [
                    {"first_name": "Ada", "last_name": "Smith"},
                    {"organization": "Study Consortium"},
                    "ignored",
                ],
            }
        )
    )
    assert reference_summary(tmp_path) == {
        "sid": "123",
        "pmid": "123",
        "doi": "10.1/x",
        "title": "A title",
        "journal": "Journal",
        "publication_date": "2020-03-01",
        "abstract": "Text",
        "authors": ["Ada Smith", "Study Consortium"],
    }
