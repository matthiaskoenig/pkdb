"""Measure explicit uploads against a disposable endpoint; never resets databases.

Run separately against fresh databases to compare first imports. Running all job
counts against one endpoint measures replacements after the first run.
"""

import argparse
import json
import os
import time
from pathlib import Path

from pkdb.batch import BatchOptions, upload_many
from pkdb.domain.vocabulary import Vocabulary
from pkdb.preparation import study_folders


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--vocabulary", required=True, type=Path)
    parser.add_argument("--jobs", type=int, nargs="+", default=[1, 2, 4, 8])
    parser.add_argument("--reports", type=Path, required=True)
    args = parser.parse_args()
    args.reports.mkdir(parents=True, exist_ok=False)
    folders = study_folders(args.folder)
    vocabulary = Vocabulary.load(args.vocabulary)
    for index, jobs in enumerate(args.jobs):
        started = time.monotonic()
        report = upload_many(
            folders,
            endpoint=args.endpoint,
            api_key=os.environ["PKDB_API_KEY"],
            vocabulary=vocabulary,
            options=BatchOptions(
                jobs=jobs, report=args.reports / f"{index}-jobs-{jobs}.json"
            ),
        )
        duration = time.monotonic() - started
        succeeded = sum(row["ok"] for row in report["results"])
        print(
            json.dumps(
                dict(
                    jobs=jobs,
                    seconds=duration,
                    studies_per_minute=60 * succeeded / duration,
                    summary=report["summary"],
                )
            ),
            flush=True,
        )
        if succeeded != len(folders) or report.get("report_error"):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
