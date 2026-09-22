import json

from pkdb.db.models.vocabulary import VocabularyEdge, VocabularyNode, VocabularyTerm


def test_vocabulary_detail_search_and_filters(client, session_factory):
    with session_factory.begin() as session:
        session.add_all(
            [
                VocabularyNode(sid="parent", name="parent", kind="info_node"),
                VocabularyNode(
                    sid="drug-test",
                    name="example drug",
                    kind="substance",
                    mass=12.5,
                    formula="C",
                    charge=0,
                ),
                VocabularyNode(sid="choice-test", name="example choice", kind="choice"),
                VocabularyNode(
                    sid="measure-test",
                    name="example measurement",
                    kind="measurement",
                    definition={
                        "dtype": "categorical",
                        "units": [],
                        "choices": ["example choice"],
                    },
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                VocabularyEdge(child="drug-test", parent="parent"),
                VocabularyEdge(child="choice-test", parent="measure-test"),
                VocabularyTerm(
                    node_sid="drug-test", kind="synonyms", value="unusual alias"
                ),
                VocabularyTerm(
                    node_sid="drug-test", kind="label", value=json.dumps("Example drug")
                ),
                VocabularyTerm(
                    node_sid="drug-test",
                    kind="description",
                    value=json.dumps("A vocabulary description"),
                ),
                VocabularyTerm(
                    node_sid="measure-test",
                    kind="dtype",
                    value=json.dumps("categorical"),
                ),
            ]
        )
    response = client.get("/api/v1/info_nodes/drug-test/")
    assert response.status_code == 200
    assert response.json() == {
        "sid": "drug-test",
        "name": "example drug",
        "label": "Example drug",
        "deprecated": False,
        "ntype": "substance",
        "dtype": "undefined",
        "description": "A vocabulary description",
        "synonyms": ["unusual alias"],
        "parents": [{"sid": "parent", "name": "parent", "label": "parent"}],
        "annotations": [],
        "xrefs": [],
        "measurement_type": None,
        "substance": {"mass": 12.5, "formula": "C", "charge": 0},
    }
    measurement = client.get("/api/v1/info_nodes/measure-test/").json()
    assert measurement["ntype"] == "measurement_type"
    assert measurement["measurement_type"] == {
        "units": [],
        "choices": [
            {"sid": "choice-test", "name": "example choice", "label": "example choice"}
        ],
    }
    response = client.get(
        "/api/v1/info_nodes/", params={"search": "unusual alias", "ntype": "substance"}
    )
    assert response.status_code == 200
    assert [row["sid"] for row in response.json()["data"]["data"]] == ["drug-test"]
    response = client.get(
        "/api/v1/info_nodes/", params={"dtype__in": "categorical", "ordering": "name"}
    )
    assert [row["sid"] for row in response.json()["data"]["data"]] == [
        "measure-test",
        "sex",
        "species",
    ]
    assert client.get("/api/v1/info_nodes/missing/").status_code == 404
    assert (
        client.get(
            "/api/v1/info_nodes/", params={"name__delete": "drug-test"}
        ).status_code
        == 400
    )
    assert (
        client.get("/api/v1/info_nodes/", params={"search": "%' OR true --"}).json()[
            "data"
        ]["count"]
        == 0
    )


def test_refreshed_vocabulary_preserves_legacy_api_contract(
    client, session_factory, tmp_path
):
    from pathlib import Path

    from pkdb.db.bootstrap import bootstrap

    root = Path(__file__).parents[2]
    (tmp_path / "users.json").write_text("[]")
    (tmp_path / "vocabulary.json").write_bytes(
        (root / "bootstrap/vocabulary.json").read_bytes()
    )
    with session_factory.begin() as session:
        assert not bootstrap(tmp_path, session).errors
    golden = json.loads((root / "tests/fixtures/golden/vocabulary.json").read_text())

    def unordered(value):
        if isinstance(value, dict):
            return {key: unordered(item) for key, item in value.items()}
        if isinstance(value, list):
            return sorted(
                (unordered(item) for item in value),
                key=lambda item: json.dumps(item, sort_keys=True),
            )
        return value

    snapshot = json.loads((root / "bootstrap/vocabulary.json").read_text())
    current_nodes = {node["sid"]: node for node in snapshot["nodes"]}
    for sid, expected in golden.items():
        # Keep the historical API contract, but compare volatile enrichment with
        # the freshly generated source data that was actually bootstrapped.
        current = current_nodes[sid]
        for field in ("annotations", "xrefs"):
            expected[field] = [json.loads(value) for value in current["terms"][field]]
        expected["synonyms"] = current["terms"]["synonyms"]
        if expected["substance"] is not None:
            expected["substance"] = {
                key: current["definition"][key] for key in ("mass", "charge", "formula")
            }
        response = client.get(f"/api/v1/info_nodes/{sid}/")
        assert response.status_code == 200
        assert unordered(response.json()) == unordered(expected)
    matches = client.get(
        "/api/v1/info_nodes/", params={"search": "Eliquis", "ntype": "substance"}
    ).json()["data"]
    assert "apixaban" in {row["sid"] for row in matches["data"]}
