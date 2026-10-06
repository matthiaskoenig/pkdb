"""The pkdb digitize and plot commands: figure digitization and figure plots of study folders."""

import json
import sys
from pathlib import Path

from pkdb.studyformat_cli import print_issues, say, study_folder


def register(commands) -> None:
    """Add the `digitize` and `plot` commands."""
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
    plot = commands.add_parser(
        "plot",
        help="Render the figures of a study as PNG files",
        description=(
            "Render figure sources with matplotlib: the figure image with its digitized "
            "points and mapped rows, or image and data plot side by side without "
            "digitization. Files are <out>/<study>_<source>.plot.png."
        ),
    )
    plot.add_argument("study", type=Path, help="Study folder")
    plot.add_argument(
        "--source",
        help="Source to render (default: every Fig source with timecourses or scatters)",
    )
    plot.add_argument(
        "--out", type=Path, help="Output directory (default: a new temporary directory)"
    )
    plot.add_argument(
        "--format",
        choices=("human", "json"),
        help="Output format (default: human on a terminal)",
    )


def run(args) -> int:
    """Run the `digitize` or `plot` command and return the exit code."""
    if args.command == "plot":
        return _plot(args)
    return _digitize(args)


def _plot(args) -> int:
    import tempfile

    from pkdb.studyformat import study_label
    from pkdb.studyformat.load import load_study
    from pkdb.studyformat.plot import render_source
    from pkdb.studyformat.sources import study_sources

    human = args.format == "human" or (args.format is None and sys.stdout.isatty())
    try:
        study = load_study(args.study)
        if args.source:
            sources = [args.source]
        else:
            sources = [
                summary.source
                for summary in study_sources(study)
                if summary.source.startswith("Fig")
                and any(
                    table.kind in ("timecourses", "scatters")
                    and (
                        table.source == summary.source
                        or any(
                            row.cells.get("source") == summary.source
                            for row in table.rows
                        )
                    )
                    for table in study.tables
                )
            ]
        out = args.out or Path(tempfile.mkdtemp(prefix="pkdb-plot-"))
        out.mkdir(parents=True, exist_ok=True)
        plots = []
        for source in sources:
            file = out / f"{study.name}_{source}.plot.png"
            result = render_source(study, source, file)
            plots.append(
                {
                    "source": source,
                    "file": str(file),
                    "mode": "overlay" if result.points else "side_by_side",
                }
            )
    except KeyError as error:
        say(
            f"Cannot plot {args.study}: unknown source {error.args[0]}", file=sys.stderr
        )
        return 1
    except (ValueError, OSError) as error:
        say(f"Cannot plot {args.study}: {error}", file=sys.stderr)
        return 1
    if not human:
        print(
            json.dumps({"path": str(args.study), "ok": True, "plots": plots}),
            flush=True,
        )
        return 0
    label = study_label(args.study)
    for plot in plots:
        say(f"{label}: {plot['source']} ({plot['mode']}) {plot['file']}")
    return 0


def _digitize(args) -> int:
    from pkdb.studyformat import study_label
    from pkdb.studyformat.digitize import import_project

    human = args.format == "human" or (args.format is None and sys.stdout.isatty())
    folder = study_folder(args.study, args.command)
    if folder is None:
        return 1
    try:
        result = import_project(folder, args.source, args.file)
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
