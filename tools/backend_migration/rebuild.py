"""Account for every source folder and resume only verified current publications."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import quote

import httpx
from pydantic import ValidationError

from pkdb.commands.upload import api_root, send_folder
from pkdb.schemas.replacement import PublicationState

# Support both module invocation and the documented direct script invocation.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.backend_migration.manifest import build_manifest


def fingerprint(record):
    """Hash the inventoried attachment and JSON metadata."""
    return hashlib.sha256(
        json.dumps(record["files"], sort_keys=True).encode()
    ).hexdigest()


def save_report(path, report, token):
    """Atomically checkpoint a redacted report before continuing."""

    def redact(value):
        if isinstance(value, str):
            return value.replace(token, "[redacted]") if token else value
        if isinstance(value, list):
            return [redact(item) for item in value]
        if isinstance(value, dict):
            return {key: redact(item) for key, item in value.items()}
        return value

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            json.dump(redact(report), handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def remote_state(client, api_url, sid, token):
    """Read typed publication metadata without following redirects."""
    response = client.get(
        api_url + "/studies/" + quote(sid, safe="") + "/publication",
        headers={"Authorization": f"Token {token}"},
    )
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise ValueError("Publication metadata unavailable")
    publication = PublicationState.model_validate(response.json())
    if publication.sid != sid or not publication.digest:
        raise ValueError("Publication identity was not confirmed")
    return publication.model_dump()


def current(publication):
    """Require both scientific processing and vocabulary to be current."""
    return publication is not None and all(
        publication[field] == publication["current_" + field]
        for field in ("processing_version", "vocabulary_version")
    )


def rebuild(corpus, url, report_path, token, client, *, resume=True):
    """Publish unambiguous sources and account for every discovered folder."""
    corpus = Path(corpus).resolve(strict=True)
    report_path = Path(report_path).resolve()
    if report_path.is_relative_to(corpus):
        raise ValueError("Keep the rebuild report outside the read-only corpus")
    if not token:
        raise ValueError("PKDB_API_TOKEN is required")
    api_url = api_root(url)
    manifest = build_manifest(corpus)
    previous = {}
    if resume and report_path.exists():
        saved = json.loads(report_path.read_text())
        if saved.get("api_url") != api_url or saved.get("schema_version") != 1:
            raise ValueError(
                "Resume report belongs to a different API or report schema"
            )
        previous = {item["path"]: item for item in saved["results"]}
    duplicates = {
        issue["sid"] for issue in manifest["issues"] if issue["code"] == "duplicate_sid"
    }
    symlinks = {
        str(Path(issue["path"]).parent)
        for issue in manifest["issues"]
        if issue["code"] == "symlink"
    }
    results = []
    for entry in manifest["studies"]:
        record = {
            "path": entry["path"],
            "sid": entry.get("sid"),
            "source_fingerprint": fingerprint(entry),
            "status": "pending",
        }
        if (
            entry["status"] != "inventoried"
            or entry.get("sid") in duplicates
            or entry["path"] in symlinks
        ):
            record.update(
                status="blocked",
                reason="invalid_source_identity"
                if entry["status"] != "inventoried"
                else "duplicate_sid"
                if entry.get("sid") in duplicates
                else "source_symlink",
            )
        results.append(record)
    report = {
        "schema_version": 1,
        "api_url": api_url,
        "expected_sids": sorted(
            {entry["sid"] for entry in manifest["studies"] if "sid" in entry}
        ),
        "manifest": manifest,
        "results": results,
        "complete": False,
    }
    save_report(report_path, report, token)
    for record in results:
        if record["status"] != "pending":
            continue
        old = previous.get(record["path"], {})
        folder = corpus / record["path"]
        try:
            publication = None
            resumed = False
            if (
                old.get("status") == "published"
                and old.get("source_fingerprint") == record["source_fingerprint"]
            ):
                publication = remote_state(client, api_url, record["sid"], token)
                resumed = current(publication) and publication == old.get("publication")
            if not resumed:
                outcome = send_folder(
                    folder, client=client, api_url=api_url, token=token
                )
                if not outcome["ok"]:
                    record.update(status="failed", outcome=outcome)
                    save_report(report_path, report, token)
                    continue
                publication = remote_state(client, api_url, record["sid"], token)
                if publication is None or publication["digest"] != outcome.get(
                    "digest"
                ):
                    raise ValueError("Publication changed after upload")
            after = build_manifest(folder)
            root_entry = next(
                (entry for entry in after["studies"] if entry["path"] == "."), None
            )
            if root_entry is None:
                raise ValueError("Source disappeared during rebuild")
            if fingerprint(root_entry) != record["source_fingerprint"]:
                raise ValueError(
                    "Source changed during rebuild; publication requires revalidation"
                )
            if not current(publication):
                raise ValueError(
                    "Publication is missing or has outdated processing/vocabulary"
                )
            record.update(status="published", publication=publication, resumed=resumed)
        except (OSError, ValueError, ValidationError, httpx.RequestError):
            record.update(
                status="failed", reason="Publication or source could not be verified"
            )
        save_report(report_path, report, token)
    report["complete"] = bool(results) and all(
        record["status"] == "published" for record in results
    )
    save_report(report_path, report, token)
    return report


def main():
    """Run the rebuild with an environment-provided API token."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()
    try:
        with httpx.Client(timeout=300, follow_redirects=False) as client:
            report = rebuild(
                args.corpus,
                args.api_url,
                args.report,
                os.environ.get("PKDB_API_TOKEN", ""),
                client,
                resume=not args.no_resume,
            )
    except (OSError, ValueError):
        print(
            "Rebuild could not start; check source, report, API URL and token configuration.",
            file=sys.stderr,
        )
        return 1
    counts = {
        status: sum(item["status"] == status for item in report["results"])
        for status in ("published", "blocked", "failed", "pending")
    }
    print(json.dumps({"complete": report["complete"], "counts": counts}))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
