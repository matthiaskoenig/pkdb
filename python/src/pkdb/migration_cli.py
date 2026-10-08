"""The `migrate` command: convert study format 1 folders into study format 2."""

import json
import sys
from pathlib import Path

FAILING = ("mismatch", "invalid_v1", "not_converted")
CLASSES = ("identical", "intended", *FAILING)


def bundled_vocabulary():
    """The vocabulary shipped with the package; imported late to keep help fast."""
    from pkdb.cache import bundled_vocabulary as load

    return load()


def register(commands) -> None:
    """Add the `migrate` command to the command line parser."""
    command = commands.add_parser(
        "migrate",
        help="Convert study format 1 folders into study format 2",
        description="Convert study format 1 folders into study format 2, proven by an equivalence gate with the format 1 parser.",
    )
    command.add_argument(
        "paths",
        nargs="+",
        type=Path,
        metavar="PATH",
        help="Studies folder, substance folders or study folders of one checkout",
    )
    command.add_argument(
        "--registry",
        type=Path,
        help="Study identifier registry (default: studies/study_identifiers.json when it exists)",
    )
    command.add_argument(
        "--approver",
        help="Maintainer who approves released studies (required with a registry)",
    )
    command.add_argument(
        "--report",
        type=Path,
        default=Path("migration.json"),
        help="Report file; migration.md is written next to it (default: migration.json)",
    )
    command.add_argument(
        "--dry-run",
        action="store_true",
        help="Only write the report; change no study folder",
    )
    command.add_argument(
        "--jobs", type=int, help="Number of worker processes (default: all cores)"
    )
    command.add_argument(
        "--format",
        dest="output",
        choices=("human", "json"),
        default="human",
        help="Output format (default: human)",
    )


def run(args) -> int:
    """Run the `migrate` command and return the exit code."""
    from pkdb.migration.run import RunRefused, SwapError, migrate, repository_root
    from pkdb.terminal import safe_text

    try:
        registry = args.registry
        if registry is None:
            default = repository_root(args.paths[0]) / "studies/study_identifiers.json"
            registry = default if default.is_file() else None
        if registry is not None and not args.approver:
            raise ValueError(
                "--approver is required with a registry: name the maintainer who approves released studies"
            )
        report = migrate(
            args.paths,
            report=args.report,
            registry=registry,
            approver=args.approver,
            dry_run=args.dry_run,
            jobs=args.jobs,
            vocabulary=bundled_vocabulary(),
        )
    except SwapError as error:
        print(safe_text(str(error)), file=sys.stderr)
        print(
            "Run pkdb migrate again to finish or undo the interrupted swap.",
            file=sys.stderr,
        )
        return 1
    except (ValueError, RunRefused) as error:
        print(safe_text(str(error)), file=sys.stderr)
        return 2
    except OSError as error:
        print(safe_text(f"Cannot run the migration: {error}"), file=sys.stderr)
        return 1
    counts = {name: 0 for name in CLASSES}
    for study in report.studies:
        counts[study.outcome] += 1
    if args.output == "json":
        print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
    else:
        for name in CLASSES:
            print(f"{name}: {counts[name]}")
        print(f"Report: {safe_text(str(args.report.with_suffix('.md')))}")
    return 1 if any(counts[name] for name in FAILING) else 0
