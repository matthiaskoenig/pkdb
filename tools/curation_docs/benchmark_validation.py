"""Offline preparation benchmark: stage wall times plus a separate cProfile run.

Run with python/.venv/bin/python tools/curation_docs/benchmark_validation.py PATH.
No source files are modified and no server requests are made.
"""

import argparse
import cProfile
import hashlib
import json
import platform
import pstats
import statistics
import time
from pathlib import Path

from pkdb.cache import bundled_vocabulary
from pkdb.preparation import prepare, study_folders
from pkdb.schemas.validation import StudyValidationError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument(
        "--output", type=Path, default=Path("/tmp/pkdb-validation-benchmark")
    )
    parser.add_argument(
        "--fingerprints",
        action="store_true",
        help="Hash complete prepared outputs or error reports outside measured time",
    )
    parser.add_argument(
        "--no-profile", action="store_true", help="Skip the separate profiled pass"
    )
    args = parser.parse_args()
    if args.repeats < 1 or args.limit < 1:
        parser.error("repeats and limit must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    vocabulary = bundled_vocabulary()
    vocabulary_seconds = time.perf_counter() - started
    folders = study_folders(args.path)[: args.limit]
    results = []

    def measure(folder, *, fingerprint=False):
        started = previous = time.perf_counter()
        stage = "setup"
        stages = {}

        def progress(event):
            nonlocal previous, stage
            now = time.perf_counter()
            stages[stage] = stages.get(stage, 0) + now - previous
            previous, stage = now, event.stage

        status, issues = "valid", 0
        prepared = report = None
        try:
            prepared = prepare(folder, vocabulary=vocabulary, progress=progress)
            issues = len(prepared.report.issues)
        except StudyValidationError as error:
            status = "invalid"
            issues = len(error.report.issues)
            report = error.report
        now = time.perf_counter()
        stages[stage] = stages.get(stage, 0) + now - previous
        result = {
            "seconds": now - started,
            "stages": stages,
            "status": status,
            "issues": issues,
        }

        if fingerprint:
            output = (
                prepared.model_dump()
                if prepared is not None
                else {"report": report.model_dump(mode="json")}
            )
            result["output_sha256"] = hashlib.sha256(
                json.dumps(output, sort_keys=True, allow_nan=False).encode()
            ).hexdigest()
        return result

    for folder in folders:
        runs = [
            measure(folder, fingerprint=args.fingerprints) for _ in range(args.repeats)
        ]
        results.append(
            {
                "study": str(folder),
                "runs": runs,
                "median_seconds": statistics.median(r["seconds"] for r in runs),
            }
        )
        print(folder.name, round(results[-1]["median_seconds"], 4), flush=True)
    (args.output / "results.json").write_text(
        json.dumps(
            {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "vocabulary_seconds": vocabulary_seconds,
                "results": results,
            },
            indent=2,
        )
        + "\n"
    )
    if args.no_profile:
        return
    profiler = cProfile.Profile()
    profiler.enable()
    for folder in folders:
        measure(folder)
        print("Profiled", folder.name, flush=True)
    profiler.disable()
    profiler.dump_stats(str(args.output / "validation.prof"))
    with (args.output / "profile.txt").open("w") as handle:
        pstats.Stats(profiler, stream=handle).strip_dirs().sort_stats(
            "cumulative"
        ).print_stats(50)


if __name__ == "__main__":
    main()
