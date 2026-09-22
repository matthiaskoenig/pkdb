"""Test the authoring command through its public JSON output, without a database."""

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def generated_vocabulary(tmp_path_factory):
    output = tmp_path_factory.mktemp("vocabulary")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/update_vocabulary.py"),
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


def test_generation_reports_metadata_issues(generated_vocabulary):
    issues = generated_vocabulary["provenance"]["metadata_issues"]
    assert any(
        issue["sid"] == "mixed-race" and issue["code"] == "curation_review"
        for issue in issues
    )
    assert any(issue["code"] == "unknown_policy_measurement" for issue in issues)
    sources = generated_vocabulary["provenance"]["definition_sha256"]
    assert "backend/info_nodes/node.py" in sources
    assert not any("pkdb_data/info_nodes" in path for path in sources)


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


@pytest.mark.parametrize(
    ("sid", "collection", "label"),
    [
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
