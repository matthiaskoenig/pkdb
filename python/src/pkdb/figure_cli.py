"""The pkdb digitize command: import WebPlotDigitizer projects of figures into study folders."""

import json
import sys
from pathlib import Path

from pkdb.studyformat_cli import print_issues, say


def register(commands) -> None:
    """Add the `digitize` command."""
    digitize = commands.add_parser(
        "digitize",
        help="Import WebPlotDigitizer projects of figures",
        description="Digitize figures of study format 2 folders with WebPlotDigitizer.",
    )
    actions = digitize.add_subparsers(dest="action", required=True, title="actions")
    import_ = actions.add_parser(
        "import",
        help="Import a WebPlotDigitizer project as the digitization of a figure",
        description=(
            "Write <study>_<source>.wpd.json from a WebPlotDigitizer 4 project (a JSON "
            "file or a .tar export) after checking it against the figure image "
            "<study>_<source>.png; the image is taken from the archive when the study has none."
        ),
    )
    import_.add_argument("study", type=Path, help="Study folder")
    import_.add_argument("source", help="Figure source such as Fig1")
    import_.add_argument("file", type=Path, help="Project .json or .tar file")
    import_.add_argument(
        "--format",
        choices=("human", "json"),
        help="Output format (default: human on a terminal)",
    )


def run(args) -> int:
    """Run a `digitize` action and return the exit code."""
    from pkdb.studyformat import study_label
    from pkdb.studyformat.digitize import import_project

    human = args.format == "human" or (args.format is None and sys.stdout.isatty())
    try:
        result = import_project(args.study, args.source, args.file)
    except (ValueError, OSError) as error:
        say(f"Cannot import {args.file}: {error}", file=sys.stderr)
        return 1
    ok = not any(issue.severity == "error" for issue in result.issues)
    if not human:
        print(
            json.dumps(
                {
                    "path": str(args.study),
                    "file": result.file,
                    "ok": ok,
                    "wrote_image": result.wrote_image,
                    "issues": [
                        issue.model_dump(mode="json", exclude_none=True)
                        for issue in result.issues
                    ],
                }
            ),
            flush=True,
        )
        return 0 if ok else 1
    label = study_label(args.study)
    if ok:
        image = (
            f" and {Path(result.file).stem.removesuffix('.wpd')}.png"
            if result.wrote_image
            else ""
        )
        say(f"{label}: wrote {result.file}{image}")
        return 0
    say(f"{label}: not imported")
    print_issues(result.issues)
    return 1
