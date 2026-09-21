"""Read-only corpus inventory: every discovered study gets an explicit result."""

import argparse
import hashlib
import json
from pathlib import Path


def _file_record(path: Path) -> dict:
    """Hash a file without loading its contents into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"sha256": digest.hexdigest(), "bytes": path.stat().st_size}


def _unique_object(pairs):
    """Reject duplicate keys as the legacy JSON reader does."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def build_manifest(root: Path) -> dict:
    """Build manifest."""
    root = root.resolve(strict=True)
    studies = []
    identifiers: dict[str, list[str]] = {}
    issues = []
    for source in sorted(root.rglob("study.json")):
        relative = source.parent.relative_to(root).as_posix()
        record = {"path": relative, "status": "inventoried", "files": {}}
        for file in sorted(source.parent.iterdir()):
            if file.is_symlink():
                issues.append({"code": "symlink", "path": str(file.relative_to(root))})
            elif file.is_file():
                record["files"][file.name] = _file_record(file)
        try:
            data = json.loads(source.read_text(), object_pairs_hook=_unique_object)
            if (
                not isinstance(data, dict)
                or type(data.get("sid")) not in (str, int)
                or not str(data.get("sid", "")).strip()
            ):
                record["status"] = "invalid_identity"
            else:
                record["sid"] = str(data["sid"])
                record["name"] = data.get("name")
                identifiers.setdefault(str(data["sid"]), []).append(relative)
        except (ValueError, UnicodeError):
            record["status"] = "invalid_json"
        studies.append(record)
    for sid, paths in sorted(identifiers.items()):
        if len(paths) > 1:
            issues.append({"code": "duplicate_sid", "sid": sid, "paths": paths})
    return {
        "schema_version": 1,
        "study_count": len(studies),
        "studies": studies,
        "issues": issues,
    }


def main() -> None:
    """Main."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(build_manifest(args.root), indent=2) + "\n")


if __name__ == "__main__":
    main()
