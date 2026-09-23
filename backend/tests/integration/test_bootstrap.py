import json

import pytest
from sqlalchemy import select

from pkdb_server.db.bootstrap import bootstrap, load_vocabulary
from pkdb_server.db.models.users import User
from pkdb_server.db.models.vocabulary import VocabularyVersion


@pytest.fixture
def bootstrap_directory(tmp_path):
    (tmp_path / "users.json").write_text(
        json.dumps([{"username": "curator", "role": "curator"}])
    )
    (tmp_path / "vocabulary.json").write_text(
        json.dumps(
            {
                "version": "source-v1",
                "nodes": [
                    {
                        "sid": "concentration",
                        "name": "concentration",
                        "kind": "measurement",
                        "definition": {
                            "name": "concentration",
                            "units": ["mg/l"],
                            "time_required": True,
                        },
                    },
                ],
            }
        )
    )
    return tmp_path


def test_bootstrap_is_idempotent_and_users_are_disabled(
    db_session, bootstrap_directory
):
    with db_session.begin():
        first = bootstrap(bootstrap_directory, db_session)
        second = bootstrap(bootstrap_directory, db_session)
        assert first.inserted == 2
        assert second.inserted == 0
        assert second.unchanged == 2
        assert not first.errors
        assert not db_session.scalar(select(User)).active
        vocabulary = load_vocabulary(db_session)
        assert vocabulary.measurements[0].name == "concentration"
        assert vocabulary.version == db_session.get(VocabularyVersion, 1).version


@pytest.mark.parametrize("defect", ["duplicate", "unknown_parent", "cycle"])
def test_invalid_bootstrap_writes_nothing(db_session, bootstrap_directory, defect):
    path = bootstrap_directory / "vocabulary.json"
    data = json.loads(path.read_text())
    if defect == "duplicate":
        data["nodes"].append(data["nodes"][0])
    elif defect == "unknown_parent":
        data["nodes"][0]["parents"] = ["absent"]
    else:
        data["nodes"][0]["parents"] = ["concentration"]
    path.write_text(json.dumps(data))
    with db_session.begin():
        result = bootstrap(bootstrap_directory, db_session)
        assert result.errors
        assert db_session.scalar(select(User)) is None


def test_changed_vocabulary_changes_validation_version(db_session, bootstrap_directory):
    with db_session.begin():
        bootstrap(bootstrap_directory, db_session)
        before = load_vocabulary(db_session).version
        path = bootstrap_directory / "vocabulary.json"
        data = json.loads(path.read_text())
        data["nodes"][0]["definition"]["units"] = ["ug/l"]
        path.write_text(json.dumps(data))
        bootstrap(bootstrap_directory, db_session)
        assert load_vocabulary(db_session).version != before


def test_bootstrap_requires_explicit_transaction(db_session, bootstrap_directory):
    with pytest.raises(RuntimeError, match="transaction"):
        bootstrap(bootstrap_directory, db_session)


def test_full_offline_vocabulary_bootstraps(db_session, bootstrap_directory):
    from pathlib import Path

    source = Path(__file__).parents[2] / "bootstrap/vocabulary.json"
    (bootstrap_directory / "vocabulary.json").write_bytes(source.read_bytes())
    with db_session.begin():
        report = bootstrap(bootstrap_directory, db_session)
        assert not report.errors, report.errors
        vocabulary = load_vocabulary(db_session)
        mass = vocabulary.substance_map()["apixaban"].mass
        assert mass is not None and mass > 0
        assert "M" in vocabulary.measurement_map()["sex"].choices
