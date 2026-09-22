"""Export legacy definitions using copied caches; network access is forbidden.

Run in the disposable metadata environment documented in bootstrap/README.md.
"""

import argparse
import ast
import hashlib
import json
import logging
import shutil
import socket
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.backend_migration.vocabulary import convert_vocabulary


def main():
    """Export cached definitions without altering legacy sources."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-backend", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    logging.disable(logging.CRITICAL)

    def forbid_network(*args, **kwargs):
        raise RuntimeError("Network forbidden during offline vocabulary export")

    socket.socket.connect = forbid_network
    import pymetadata
    from pymetadata.webservices import chebi, ols, registry, unichem
    from pymetadata.webservices.webservice import WebserviceError

    misses = []

    def cache_miss(url, **kwargs):
        misses.append(url)
        raise WebserviceError("No cached metadata in offline export")

    def read_cache(cache_path, **kwargs):
        return json.loads(Path(cache_path).read_text())

    with TemporaryDirectory(prefix="pkdb-vocabulary-") as directory:
        cache = Path(directory) / "cache"
        shutil.copytree(args.source_backend / "pkdb_data/resources/cache", cache)
        shutil.copy2(args.registry, cache / "identifiers_registry.json")
        pymetadata.CACHE_PATH = cache
        for module in (registry, chebi, unichem, ols):
            module.read_json_cache = read_cache
            module.get_json = cache_miss
            if hasattr(module, "cache_age"):
                module.cache_age = lambda path: 0 if Path(path).exists() else None
        sys.path.insert(0, str(args.source_backend.resolve()))
        import pkdb_data

        pkdb_data.CACHE_PATH = cache
        from pkdb_data.info_nodes.nodes import collect_nodes

        nodes = collect_nodes()
        serialized = [node.serialize(nodes) for node in nodes]
    policy_file = args.source_backend / "pkdb_app/info_nodes/models.py"
    module = ast.parse(policy_file.read_text())
    policy = next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == "MeasurementType"
    )
    fields = {"TIME_REQUIRED_MEASUREMENT_TYPES", "CAN_NEGATIVE"}
    constants = {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in policy.body
        if isinstance(node, ast.Assign)
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in fields
    }
    snapshot = convert_vocabulary(
        serialized,
        time_required=set(constants["TIME_REQUIRED_MEASUREMENT_TYPES"]),
        can_negative=set(constants["CAN_NEGATIVE"]),
    )
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "vocabulary.json").write_text(json.dumps(snapshot, indent=2) + "\n")
    provenance = {
        "legacy_nodes": len(serialized),
        "uncached_optional_metadata": sorted(set(misses)),
        "legacy_serialization_sha256": hashlib.sha256(
            json.dumps(serialized, sort_keys=True).encode()
        ).hexdigest(),
        "policy_sha256": hashlib.sha256(policy_file.read_bytes()).hexdigest(),
    }
    (args.output / "provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n"
    )
    print(f"Exported {len(serialized)} nodes; {len(misses)} uncached metadata requests")


if __name__ == "__main__":
    main()
