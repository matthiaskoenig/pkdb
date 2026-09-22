"""Compile authored node definitions into an offline bootstrap snapshot."""

import hashlib
import json


def convert_vocabulary(
    nodes: list[dict], *, time_required: set[str], can_negative: set[str]
) -> dict:
    """Preserve stable identities and explicit scientific policies."""
    lookup = {node["sid"]: node for node in nodes}
    if len(lookup) != len(nodes):
        raise ValueError("Duplicate vocabulary SID")
    converted = []
    for node in nodes:
        kind = "measurement" if node["ntype"] == "measurement_type" else node["ntype"]
        definition = {}
        if kind == "measurement":
            extra = node.get("measurement_type") or {}
            definition = {
                "dtype": node["dtype"],
                "units": extra.get("units", []),
                "choices": [lookup[sid]["name"] for sid in extra.get("choices", [])],
                "time_required": node["name"] in time_required,
                "can_negative": node["name"] in can_negative,
                "deprecated": node.get("deprecated", False),
            }
        elif kind == "substance":
            extra = node.get("substance") or {}
            definition = {
                "mass": float(extra["mass"]) if extra.get("mass") is not None else None,
                "charge": int(extra["charge"])
                if extra.get("charge") is not None
                else None,
                "formula": extra.get("formula"),
            }
        terms = {
            name: [
                json.dumps(value, sort_keys=True)
                if isinstance(value, (dict, list))
                else str(value)
                for value in node.get(name, [])
            ]
            for name in ("synonyms", "annotations", "xrefs")
        }
        for field in ("label", "description", "dtype", "ntype", "deprecated"):
            if node.get(field) is not None:
                terms[field] = [json.dumps(node[field])]
        converted.append(
            {
                "sid": node["sid"],
                "name": node["name"],
                "kind": kind,
                "definition": definition,
                "parents": list(dict.fromkeys(node.get("parents", []))),
                "terms": terms,
            }
        )
    digest = hashlib.sha256(json.dumps(nodes, sort_keys=True).encode()).hexdigest()
    return {"version": digest, "nodes": converted}
