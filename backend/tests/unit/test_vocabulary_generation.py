"""Test the authoring command through its public JSON output, without a database."""

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from pkdb.domain.validation import prepare_study
from pkdb.domain.vocabulary import Vocabulary
from pkdb.schemas.validation import StudyValidationError
from pkdb_server.db.bootstrap import Snapshot, vocabulary_from_snapshot

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def generated_vocabulary(tmp_path_factory):
    output = tmp_path_factory.mktemp("vocabulary")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/update_vocabulary.py"),
            "--offline",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/update_vocabulary.py"),
            "--output",
            str(output),
            "--check",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return {
        name: json.loads((output / f"{name}.json").read_text())
        for name in ("vocabulary", "provenance")
    }


def test_annotation_urls_are_resolved(generated_vocabulary):
    annotations = [
        json.loads(value)
        for node in generated_vocabulary["vocabulary"]["nodes"]
        for value in node["terms"]["annotations"]
    ]
    assert annotations
    assert not [a for a in annotations if a["url"] and "{$" in a["url"]]
    assert all(
        a["description"] is None or isinstance(a["description"], str)
        for a in annotations
    )


def test_generation_tracks_authoring_sources(generated_vocabulary):
    sources = generated_vocabulary["provenance"]["definition_sha256"]
    assert "backend/info_nodes/node.py" in sources
    assert "backend/info_nodes/convert.py" in sources
    assert not any("pkdb_data" in path for path in sources)


def test_annotation_metadata_is_available_offline(generated_vocabulary):
    provenance = generated_vocabulary["provenance"]
    assert provenance["uncached_optional_metadata"] == []
    assert not [
        issue
        for issue in provenance["metadata_issues"]
        if issue["code"] == "annotation_metadata"
        and (
            "No collection" in issue["message"]
            or "No cached metadata" in issue["message"]
        )
    ]


def test_chmo_annotations_resolve_from_offline_cache(generated_vocabulary):
    annotations = [
        json.loads(value)
        for node in generated_vocabulary["vocabulary"]["nodes"]
        for value in node["terms"]["annotations"]
    ]
    chmo = [
        annotation for annotation in annotations if annotation["collection"] == "chmo"
    ]
    assert len(chmo) == 23
    for annotation in chmo:
        assert annotation["term"].startswith("CHMO:")
        assert annotation["url"] == f"https://bioregistry.io/{annotation['term']}"
        assert annotation["label"]
        # CHMO:0002876 has no definition in the cached ontology record.
        assert annotation["description"] or annotation["term"] == "CHMO:0002876"
    assert not [
        issue
        for issue in generated_vocabulary["provenance"]["metadata_issues"]
        if "CHMO:" in issue["message"]
    ]


@pytest.mark.parametrize(
    ("sid", "collection", "label"),
    [
        ("sex", "ncit", "Sex"),
        ("age", "sio", "age"),
        ("assay", "obi", "assay"),
        ("alpha-fetoprotein", "pr", "alpha-fetoprotein"),
        ("macroalbuminuria", "scdo", "High Level Albuminuria"),
        ("asleep", "nbo", "asleep"),
    ],
)
def test_ontology_annotations_are_enriched(
    generated_vocabulary, sid, collection, label
):
    node = next(
        n for n in generated_vocabulary["vocabulary"]["nodes"] if n["sid"] == sid
    )
    annotations = [json.loads(value) for value in node["terms"]["annotations"]]
    annotation = next(a for a in annotations if a["collection"] == collection)
    assert annotation["label"] == label
    assert annotation["description"]
    assert annotation["url"].startswith(("http://", "https://"))


def test_stable_identities_and_scientific_rules(generated_vocabulary):
    baseline = json.loads((ROOT / "backend/bootstrap/vocabulary.json").read_text())
    generated = deepcopy(generated_vocabulary["vocabulary"])
    for node in baseline["nodes"] + generated["nodes"]:
        if "choices" in node["definition"]:
            node["definition"]["choices"] = list(
                dict.fromkeys(node["definition"]["choices"])
            )
    fields = ("sid", "name", "kind", "parents", "definition")
    assert [{key: node[key] for key in fields} for node in generated["nodes"]] == [
        {key: node[key] for key in fields} for node in baseline["nodes"]
    ]


def test_descriptions_have_consistent_whitespace(generated_vocabulary):
    for node in generated_vocabulary["vocabulary"]["nodes"]:
        description = json.loads(node["terms"]["description"][0])
        assert description == " ".join(description.split()), node["sid"]
        assert description.endswith((".", "?", "!")), node["sid"]


@pytest.fixture(params=["server", "client"])
def scientific_vocabulary(request, generated_vocabulary):
    if request.param == "client":
        return Vocabulary.bundled()
    return vocabulary_from_snapshot(
        Snapshot.model_validate(generated_vocabulary["vocabulary"])
    )


def test_all_change_measurements_allow_negative_values(scientific_vocabulary):
    changes = [
        rule
        for rule in scientific_vocabulary.measurements
        if "change" in rule.name.lower()
    ]
    assert changes
    assert all(rule.can_negative for rule in changes), [
        rule.name for rule in changes if not rule.can_negative
    ]


@pytest.mark.parametrize(
    "name",
    [
        "inr (change)",
        "pH change",
        "prothrombin time (change relative)",
        "weight (change relative)",
    ],
)
def test_negative_changes_pass_scientific_validation(
    scientific_vocabulary, valid_study, vocabulary, name
):
    rule = scientific_vocabulary.measurement_map()[name]
    vocabulary = vocabulary.model_copy(
        update={"measurements": (*vocabulary.measurements, rule)}
    )
    measurement = valid_study.measurements[0]
    measurement.measurement_type = name
    measurement.unit = rule.units[0]
    measurement.statistics.mean = -1
    assert prepare_study(valid_study, vocabulary).report.valid


def test_negative_baseline_inr_remains_invalid(
    scientific_vocabulary, valid_study, vocabulary
):
    rule = scientific_vocabulary.measurement_map()["inr"]
    vocabulary = vocabulary.model_copy(
        update={"measurements": (*vocabulary.measurements, rule)}
    )
    measurement = valid_study.measurements[0]
    measurement.measurement_type = "inr"
    measurement.unit = rule.units[0]
    measurement.statistics.mean = -1
    with pytest.raises(StudyValidationError) as error:
        prepare_study(valid_study, vocabulary)
    assert "negative_value" in {issue.code for issue in error.value.report.issues}
