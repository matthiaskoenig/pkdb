"""Curator profiles and reference summaries shown in the local curation interface."""

import json

from pkdb.curation.metadata import profile, reference_summary


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
