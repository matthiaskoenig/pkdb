"""Read-only OSP release check. Exit 0: current, 2: update, 1: check failed."""

import argparse
import json
import os
import re
import runpy
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

# Load only the shared constants; monitoring needs no scientific dependencies.
PIN = runpy.run_path(
    str(
        Path(__file__).resolve().parents[1] / "python/src/pkdb/importers/osp/release.py"
    )
)


def version(tag):
    if not isinstance(tag, str) or not re.fullmatch(r"v?\d+\.\d+(?:\.\d+)?", tag):
        raise ValueError("Unrecognized upstream release tag; review required")
    parts = tuple(int(part) for part in tag.removeprefix("v").split("."))
    return parts + (0,) * (3 - len(parts))


def check_release(*, opener=urlopen, token=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "pkdb-osp-release-check",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(
        f"https://api.github.com/repos/{PIN['REPOSITORY']}/releases/latest",
        headers=headers,
    )
    with opener(request, timeout=30) as response:
        release = json.load(response)
    if (
        not isinstance(release, dict)
        or release.get("draft") is not False
        or release.get("prerelease") is not False
    ):
        raise ValueError("Expected a published stable release")
    tag = release.get("tag_name")
    latest, pinned = version(tag), version(PIN["RELEASE"])
    if latest < pinned:
        raise ValueError(
            "Upstream latest release is older than the pinned version; review required"
        )
    return {
        "ok": True,
        "status": "update_available" if latest > pinned else "current",
        "pinned_release": PIN["RELEASE"],
        "latest_release": tag,
        "release_url": f"https://github.com/{PIN['REPOSITORY']}/releases/tag/{tag}",
        "checked_at": datetime.now(UTC).isoformat(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--summary", type=Path, help="Write a GitHub Actions job summary"
    )
    args = parser.parse_args(argv)
    try:
        report = check_release(token=os.environ.get("GITHUB_TOKEN"))
        code = 2 if report["status"] == "update_available" else 0
    except (URLError, OSError, ValueError) as error:
        report = {"ok": False, "status": "check_failed", "error": str(error)}
        code = 1
    print(json.dumps(report, indent=2))
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as summary:
            summary.write("## OSP observed-data release check\n\n")
            if code == 1:
                summary.write(
                    "Release check failed. See the job log; availability is unknown.\n"
                )
            else:
                summary.write(
                    f"Pinned: **{report['pinned_release']}**. Latest: **{report['latest_release']}**.\n\n"
                )
                summary.write(f"[Upstream release]({report['release_url']})\n\n")
                summary.write(
                    "New release available. Review the source and mapping, update release.py, validate, and import.\n"
                    if code == 2
                    else "No new release available.\n"
                )
    return code


if __name__ == "__main__":
    sys.exit(main())
