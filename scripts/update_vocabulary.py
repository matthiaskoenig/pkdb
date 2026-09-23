"""Refresh public metadata and compile info_nodes into backend bootstrap JSON.

Run: uv run --project backend python scripts/update_vocabulary.py
Use --check in CI to detect stale generated files without changing them.
"""

import argparse
import hashlib
import importlib
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
DEFINITIONS = ROOT / "backend" / "info_nodes"
CACHE = DEFINITIONS / "cache"


def encode(value: object) -> str:
    """Use stable formatting for committed generated files."""
    return json.dumps(value, indent=2, ensure_ascii=True) + "\n"


def compile_vocabulary(cache_path: Path, *, offline: bool) -> dict[str, str]:
    """Compile definitions against a staged cache, with optional remote refresh."""
    sys.dont_write_bytecode = True
    logging.disable(logging.CRITICAL)
    sys.path.insert(0, str(ROOT / "backend"))
    from info_nodes.metadata_cache import use_metadata_cache

    with use_metadata_cache(cache_path, offline=offline) as metadata:
        # Definitions resolve annotations when imported. Rebuild them for each cache.
        for name, module in list(sys.modules.items()):
            if name.startswith("info_nodes.definitions."):
                importlib.reload(module)
        if "info_nodes.nodes" in sys.modules:
            importlib.reload(sys.modules["info_nodes.nodes"])
        from info_nodes.audit import audit_nodes
        from info_nodes.convert import convert_vocabulary
        from info_nodes.nodes import collect_nodes
        from info_nodes.policies import CAN_NEGATIVE, TIME_REQUIRED_MEASUREMENT_TYPES

        nodes = collect_nodes()
        serialized = [node.serialize(nodes) for node in nodes]
        issues = audit_nodes(
            nodes,
            policies={
                "time_required": TIME_REQUIRED_MEASUREMENT_TYPES,
                "can_negative": CAN_NEGATIVE,
            },
        )
    snapshot = convert_vocabulary(
        serialized,
        time_required=set(TIME_REQUIRED_MEASUREMENT_TYPES),
        can_negative=set(CAN_NEGATIVE),
    )
    snapshot["version"] = hashlib.sha256(
        json.dumps(snapshot["nodes"], sort_keys=True).encode()
    ).hexdigest()
    from pkdb_server.db.bootstrap import Snapshot, validate_snapshot

    validate_snapshot(Snapshot.model_validate(snapshot))
    inputs = [*DEFINITIONS.rglob("*.py"), Path(__file__).resolve()]
    hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(inputs)
    }
    hashes.update(
        {
            str(
                (CACHE / path.relative_to(cache_path)).relative_to(ROOT)
            ): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(cache_path.rglob("*.json"))
        }
    )
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
        "uncached_optional_metadata": sorted(metadata.misses),
        "metadata_issues": issues,
    }
    return {"vocabulary.json": encode(snapshot), "provenance.json": encode(provenance)}


def publish_cache(staged_cache: Path) -> None:
    """Replace the cache after validation, without retaining obsolete entries."""
    with TemporaryDirectory(dir=DEFINITIONS, prefix=".cache-refresh-") as directory:
        replacement = Path(directory) / "new"
        previous = Path(directory) / "old"
        shutil.copytree(staged_cache, replacement)
        if CACHE.exists():
            os.replace(CACHE, previous)
        try:
            os.replace(replacement, CACHE)
        except OSError:
            if previous.exists():
                os.replace(previous, CACHE)
            raise


def main() -> int:
    """Validate everything before replacing generated files, or check for drift."""
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--check", action="store_true", help="Check committed output offline"
    )
    modes.add_argument(
        "--offline", action="store_true", help="Generate without remote requests"
    )
    modes.add_argument(
        "--refresh-cache", action="store_true", help="Fetch into an empty cache"
    )
    parser.add_argument("--output", type=Path, default=ROOT / "backend" / "bootstrap")
    args = parser.parse_args()
    try:
        with TemporaryDirectory(prefix="pkdb-metadata-") as directory:
            staged_cache = Path(directory) / "cache"
            if args.refresh_cache or not CACHE.exists():
                staged_cache.mkdir()
            else:
                shutil.copytree(CACHE, staged_cache)
            offline = args.offline or args.check
            outputs = compile_vocabulary(staged_cache, offline=offline)
            # Promote only a cache whose definitions and snapshot validated.
            if not offline:
                publish_cache(staged_cache)
        issues = json.loads(outputs["provenance.json"])["metadata_issues"]
        if issues:
            print(
                f"Metadata review: {len(issues)} issues recorded in provenance.json.",
                file=sys.stderr,
            )
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
