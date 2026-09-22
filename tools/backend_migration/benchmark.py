"""Benchmark uploads and reads against an explicitly isolated backend instance.

Use the same corpus, workload, machine and database population for comparisons.
"""

import argparse
import json
import math
import os
import platform
import statistics
import sys
import time
from pathlib import Path

import httpx

from pkdb.commands.upload import api_root, send_folder, study_folders

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.backend_migration.manifest import build_manifest


def summarize(values):
    """Retain every sample and derive nearest-rank p95 and baseline budgets."""
    ordered = sorted(values)
    median = statistics.median(values)
    p95 = ordered[math.ceil(len(ordered) * 0.95) - 1]
    return {
        "samples_seconds": values,
        "first_seconds": values[0],
        "warm_median_seconds": median,
        "median_seconds": median,
        "p95_seconds": p95,
        "budget_median_seconds": round(median * 1.10, 9),
        "budget_p95_seconds": round(p95 * 1.10, 9),
    }


def matches(response, case):
    """Require the configured response status and complete result cardinality."""
    if response.status_code != 200:
        return False
    try:
        value = response.json()
        if "count" in case:
            return value["data"]["count"] == case["count"]
        return value.get("sid") == case["sid"]
    except ValueError, KeyError, TypeError, AttributeError:
        return False


def wait_visible(client, cases, *, timeout=180, clock=time.monotonic, sleep=time.sleep):
    """Wait until every configured query sees its complete expected result."""
    deadline = clock() + timeout
    while clock() < deadline:
        complete = True
        for case in cases:
            remaining = deadline - clock()
            if remaining <= 0:
                raise TimeoutError("Complete query visibility was not confirmed")
            response = client.get(case["path"], timeout=remaining)
            if response.status_code in {400, 401, 403, 405, 422}:
                raise ValueError("Invalid visibility request: " + case["name"])
            if not matches(response, case):
                complete = False
                break
        if complete:
            return
        sleep(min(0.05, max(0, deadline - clock())))
    raise TimeoutError("Complete query visibility was not confirmed")


def measure_reads(client, cases):
    """Time only reads whose responses satisfy the workload contract."""
    results = {}
    for case in cases:
        start = time.perf_counter()
        response = client.get(case["path"])
        elapsed = time.perf_counter() - start
        if not matches(response, case):
            raise ValueError("Read contract failed: " + case["name"])
        results[case["name"]] = {"seconds": elapsed, "bytes": len(response.content)}
    return results


def memory(pid):
    """Observe Linux server RSS and lifetime high-water mark without process arguments."""
    if pid is None:
        return {"observed": False}
    values = {}
    for line in Path(f"/proc/{pid}/status").read_text().splitlines():
        if line.startswith(("VmRSS:", "VmHWM:")):
            key, amount, unit = line.split()
            assert unit == "kB"
            values[key.rstrip(":") + "_kib"] = int(amount)
    return {"observed": True, **values}


def main(argv=None):
    """Measure an isolated backend and persist shareable results without credentials."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--workload",
        type=Path,
        required=True,
        help="JSON list of named paths with expected count or SID",
    )
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--server-pid", type=int)
    parser.add_argument(
        "--cold-start",
        action="store_true",
        help="Record a separate first run after the caller restarts the application; does not flush OS/database caches",
    )
    args = parser.parse_args(argv)
    token = os.environ.get("PKDB_API_TOKEN")
    if not token or args.runs < 5:
        parser.error("Set PKDB_API_TOKEN and request at least five runs")
    root = args.corpus.resolve(strict=True)
    output = args.output.resolve()
    if output.is_relative_to(root):
        parser.error("Metrics output must be outside the source corpus")
    url = api_root(args.base_url).removesuffix("/api/v2")
    cases = json.loads(args.workload.read_text())
    if not isinstance(cases, list) or not cases:
        parser.error("Workload must be a nonempty list")
    for case in cases:
        if (
            not isinstance(case, dict)
            or not isinstance(case.get("name"), str)
            or not isinstance(case.get("path"), str)
            or not case["path"].startswith("/api/v1/")
            or not ({"count", "sid"} & case.keys())
        ):
            parser.error(
                "Each workload case needs a name, local API path and expected count or SID"
            )
    if len({case["name"] for case in cases}) != len(cases):
        parser.error("Workload names must be unique")
    folders = study_folders(root)
    manifest = build_manifest(root)
    if manifest["issues"] or any(
        row["status"] != "inventoried" for row in manifest["studies"]
    ):
        parser.error(
            "Benchmark corpus must have valid unique identities and regular files"
        )
    expected_sids = {row["sid"] for row in manifest["studies"]}
    probed_sids = {case.get("sid") for case in cases}
    if not expected_sids.issubset(probed_sids):
        parser.error("Every uploaded SID requires a study visibility probe")
    report = {
        "schema_version": 1,
        "complete": False,
        "profile": "current",
        "hardware": {
            "machine": platform.machine(),
            "system": platform.system(),
            "cpu_count": os.cpu_count(),
            "memory_kib": next(
                (
                    int(line.split()[1])
                    for line in Path("/proc/meminfo").read_text().splitlines()
                    if line.startswith("MemTotal:")
                ),
                None,
            ),
        },
        "client_python": platform.python_version(),
        "manifest": manifest,
        "workload": cases,
        "runs": [],
        "cache_note": "One excluded warmup precedes five or more measured warm runs. Optional cold run requires a fresh application process; OS/database caches are not flushed.",
        "memory_note": "Server process RSS and lifetime high-water mark, before and after each iteration; excludes PostgreSQL.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    try:
        with httpx.Client(
            base_url=url,
            headers={"Authorization": "Token " + token},
            timeout=180,
            follow_redirects=False,
        ) as client:
            phases = (
                (["cold"] if args.cold_start else [])
                + ["warmup"]
                + ["measured"] * args.runs
            )
            for phase in phases:
                before = memory(args.server_pid)
                start = time.perf_counter()
                for folder in folders:
                    result = send_folder(
                        folder, client=client, api_url=url + "/api/v2", token=token
                    )
                    if not result["ok"]:
                        raise ValueError("Study upload failed")
                wait_visible(client, cases)
                upload_seconds = time.perf_counter() - start
                reads = measure_reads(client, cases)
                observation = {
                    "phase": phase,
                    "iteration": len(report["runs"]) + 1 if phase == "measured" else 0,
                    "upload_visible_seconds": upload_seconds,
                    "reads": reads,
                    "memory_before": before,
                    "memory_after": memory(args.server_pid),
                }
                if phase == "measured":
                    report["runs"].append(observation)
                else:
                    report[phase] = observation
                output.write_text(json.dumps(report, indent=2) + "\n")
        if build_manifest(root) != manifest:
            raise ValueError("Source files changed during measurement")
        report["upload"] = summarize(
            [row["upload_visible_seconds"] for row in report["runs"]]
        )
        report["reads"] = {
            case["name"]: summarize(
                [row["reads"][case["name"]]["seconds"] for row in report["runs"]]
            )
            for case in cases
        }
        report["complete"] = True
    except (
        OSError,
        ValueError,
        TimeoutError,
        httpx.HTTPError,
    ) as error:
        report["failure_type"] = type(error).__name__
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"complete": report["complete"], "runs": len(report["runs"])}))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
