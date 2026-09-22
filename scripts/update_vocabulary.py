"""Compile editable pkdb_data definitions into the backend's offline JSON files.

Run: uv run --project backend python scripts/update_vocabulary.py
Use --check in CI to detect stale generated files without changing them.
"""

import argparse
import hashlib
import json
import logging
import os
import shutil
import socket
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "backend" / "pkdb_data"


def encode(value):
    """Use stable formatting for committed generated files."""
    return json.dumps(value, indent=2, ensure_ascii=True) + "\n"


def compile_vocabulary():
    """Read only committed metadata caches; never contact external services."""
    sys.dont_write_bytecode = True
    logging.disable(logging.CRITICAL)

    def forbid_network(*args, **kwargs):
        raise RuntimeError("Network forbidden during vocabulary generation")

    socket.socket.connect = forbid_network
    socket.socket.connect_ex = forbid_network
    import pymetadata
    from pymetadata.webservices import chebi, ols, registry, unichem
    from pymetadata.webservices.webservice import WebserviceError

    misses = set()

    def cache_miss(url, **kwargs):
        misses.add(url)
        raise WebserviceError("No cached metadata; define scientific values explicitly")

    def read_cache(cache_path, **kwargs):
        return json.loads(Path(cache_path).read_text())

    with TemporaryDirectory(prefix="pkdb-vocabulary-") as directory:
        cache = Path(directory) / "cache"
        shutil.copytree(SOURCE / "resources" / "cache", cache)
        pymetadata.CACHE_PATH = cache
        for module in (registry, chebi, unichem, ols):
            module.read_json_cache = read_cache
            module.get_json = cache_miss
            if hasattr(module, "cache_age"):
                module.cache_age = lambda path: 0 if Path(path).exists() else None
        sys.path.insert(0, str(ROOT / "backend"))
        import pkdb_data

        pkdb_data.CACHE_PATH = cache
        from pkdb_data.convert import convert_vocabulary
        from pkdb_data.info_nodes.nodes import collect_nodes
        from pkdb_data.info_nodes.policies import (
            CAN_NEGATIVE,
            TIME_REQUIRED_MEASUREMENT_TYPES,
        )

        nodes = collect_nodes()
        serialized = [node.serialize(nodes) for node in nodes]
    snapshot = convert_vocabulary(
        serialized,
        time_required=set(TIME_REQUIRED_MEASUREMENT_TYPES),
        can_negative=set(CAN_NEGATIVE),
    )
    snapshot["version"] = hashlib.sha256(
        json.dumps(snapshot["nodes"], sort_keys=True).encode()
    ).hexdigest()
    from pkdb.db.bootstrap import Snapshot, validate_snapshot

    validate_snapshot(Snapshot.model_validate(snapshot))
    inputs = [*SOURCE.rglob("*.py"), *SOURCE.rglob("*.json"), Path(__file__).resolve()]
    hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(inputs)
    }
    provenance = {
        "generator": "scripts/update_vocabulary.py",
        "nodes": len(nodes),
        "version": snapshot["version"],
        "inputs_sha256": hashlib.sha256(
            json.dumps(hashes, sort_keys=True).encode()
        ).hexdigest(),
        "definition_sha256": {
            name: digest for name, digest in hashes.items() if name.endswith(".py")
        },
        "uncached_optional_metadata": sorted(misses),
    }
    return {"vocabulary.json": encode(snapshot), "provenance.json": encode(provenance)}


def main():
    """Validate everything before replacing generated files, or check for drift."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "backend" / "bootstrap")
    args = parser.parse_args()
    try:
        outputs = compile_vocabulary()
        if args.check:
            stale = [
                name
                for name, content in outputs.items()
                if not (args.output / name).is_file()
                or (args.output / name).read_text() != content
            ]
            if stale:
                print(
                    "Stale generated vocabulary: " + ", ".join(stale), file=sys.stderr
                )
                return 1
            print("Vocabulary JSON files are current.")
            return 0
        args.output.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=args.output, prefix=".vocabulary-") as directory:
            for name, content in outputs.items():
                (Path(directory) / name).write_text(content)
            for name in outputs:
                os.replace(Path(directory) / name, args.output / name)
        print("Updated vocabulary.json and provenance.json (users.json unchanged).")
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Vocabulary generation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
