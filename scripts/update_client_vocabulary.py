#!/usr/bin/env python3
"""Regenerate the offline client snapshot from the server bootstrap vocabulary.

Run from the repository: uv run --project backend python scripts/update_client_vocabulary.py [--check]
"""

import argparse
import json
from pathlib import Path

from pkdb.domain.vocabulary import vocabulary_hash
from pkdb_server.db.bootstrap import Snapshot, vocabulary_from_snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    snapshot = Snapshot.model_validate_json(
        (root / "backend/bootstrap/vocabulary.json").read_text(encoding="utf-8")
    )
    vocabulary = vocabulary_from_snapshot(snapshot)
    content = (
        json.dumps(
            {
                "schema_version": 1,
                "vocabulary": vocabulary.model_dump(mode="json"),
                "vocabulary_hash": vocabulary_hash(vocabulary),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )
    target = root / "python/src/pkdb/data/vocabulary.json"
    if args.check:
        if not target.exists() or target.read_text(encoding="utf-8") != content:
            parser.exit(
                1, "Bundled vocabulary is stale; run this script without --check.\n"
            )
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
