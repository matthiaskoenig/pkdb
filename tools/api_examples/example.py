"""Read a study and export its dataset through the documented REST API."""

import argparse
import json
import os
import zipfile
from pathlib import Path


def run_examples(client, output_dir, *, substance="apixaban", study_sid="PKDB01110"):
    """Accept an HTTPX-compatible client; never create or replace study data."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    def read(path, **kwargs):
        response = client.get(path, **kwargs)
        response.raise_for_status()
        return response.json()

    studies = read("/api/v2/studies", params={"substance": substance, "page_size": 20})
    study = read(f"/api/v2/studies/{study_sid}")
    measurements = read(
        "/api/v2/measurements",
        params={"study_sid": study_sid, "measurement_type": "concentration"},
    )
    response = client.post(
        "/api/v2/query",
        json={
            "entity": "groups",
            "predicates": [{"field": "study_sid", "value": study_sid}],
        },
    )
    response.raise_for_status()
    groups = response.json()
    response = client.post(
        "/api/v2/exports",
        json={
            "queries": {
                "studies": {
                    "entity": "studies",
                    "predicates": [{"field": "sid", "value": study_sid}],
                }
            },
            "concise": True,
        },
    )
    response.raise_for_status()
    archive_path = destination / "dataset.zip"
    archive_path.write_bytes(response.content)
    (destination / "study.json").write_text(json.dumps(study, indent=2) + "\n")
    with zipfile.ZipFile(archive_path) as archive:
        archive_files = sorted(archive.namelist())
    summary = {
        "study_sids": [item["sid"] for item in studies["items"]],
        "canonical_sid": study["sid"],
        "measurement_total": measurements["total"],
        "group_total": groups["total"],
        "archive_files": archive_files,
    }
    (destination / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main():
    import httpx

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--endpoint", default=os.getenv("PKDB_ENDPOINT", "http://localhost:18083")
    )
    parser.add_argument("--substance", default="apixaban")
    parser.add_argument("--study-sid", default="PKDB01110")
    parser.add_argument("--output", type=Path, default=Path("api-example-results"))
    args = parser.parse_args()
    api_key = os.environ.get("PKDB_API_KEY")
    if not api_key:
        parser.error("Set PKDB_API_KEY to a read-scoped API key for dataset export.")
    with httpx.Client(
        base_url=args.endpoint,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=120,
    ) as client:
        summary = run_examples(
            client, args.output, substance=args.substance, study_sid=args.study_sid
        )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
