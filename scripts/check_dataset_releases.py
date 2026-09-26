"""Read-only public dataset monitoring. Exit 0 current, 2 changed, 1 unknown."""

import argparse
import hashlib
import json
import re
import runpy
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

PINS = runpy.run_path(
    str(
        Path(__file__).resolve().parents[1]
        / "python/src/pkdb/importers/datasets/releases.py"
    )
)["RELEASES"]


def fetch(url):
    with urlopen(
        Request(url, headers={"User-Agent": "pkdb-dataset-release-check"}), timeout=60
    ) as response:
        return response.read()


def check(provider, read=fetch):
    pin = PINS[provider]
    if provider == "frdb":
        page = read("https://drugs.ncats.io/downloads-public").decode()
        versions = re.findall(r"frdb-v(\d{4}-\d{2}-\d{2})\.zip", page)
        if not versions:
            raise ValueError("FRDB release links missing; availability unknown")
        latest = max(versions)
        current = pin["release"]
    elif provider == "cvtdb":
        page = read(
            "https://cran.r-project.org/web/packages/invivoPKfit/DESCRIPTION"
        ).decode()
        match = re.search(r"^Version:\s*(\d+\.\d+\.\d+)\s*$", page, re.M)
        if not match:
            raise ValueError("CRAN version missing; availability unknown")
        latest, current = match[1], pin["release"].removeprefix("invivoPKfit-")
    else:
        # No tagged releases: monitor the actual data, not unrelated repository commits.
        payload = read(
            "https://raw.githubusercontent.com/nlmixr2/nlmixr2data/main/data/warfarin.rda"
        )
        latest, current = hashlib.sha256(payload).hexdigest(), pin["sha256"]
    return {
        "provider": provider,
        "status": "current" if latest == current else "update_available",
        "pinned": current,
        "latest": latest,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args(argv)
    reports = []
    for provider in PINS:
        try:
            reports.append(check(provider))
        except (OSError, URLError, ValueError) as error:
            reports.append(
                {"provider": provider, "status": "check_failed", "error": str(error)}
            )
    print(
        json.dumps(
            {"checked_at": datetime.now(UTC).isoformat(), "sources": reports}, indent=2
        )
    )
    if args.summary:
        with args.summary.open("a") as stream:
            stream.write("## Public dataset release checks\n\n")
            for report in reports:
                stream.write(
                    f"- {report['provider']}: {report['status']}. "
                    + (
                        "Availability unknown."
                        if report["status"] == "check_failed"
                        else f"Pinned: {report['pinned']}; latest: {report['latest']}."
                    )
                    + "\n"
                )
    return (
        1
        if any(x["status"] == "check_failed" for x in reports)
        else 2
        if any(x["status"] == "update_available" for x in reports)
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
