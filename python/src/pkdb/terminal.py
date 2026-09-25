"""Human-readable study results without interpreting source text as markup."""

import json
import re
import sys
import time

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from pkdb.progress import ProgressEvent


def safe_text(value: object) -> str:
    """Strip terminal controls and bound potentially untrusted display text."""
    return re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", str(value))[:2000]


class Terminal:
    """Render live stages on terminals and stable lines on redirected streams."""

    def __init__(self, enabled: bool, verbose: bool = False):
        self.enabled = enabled
        self.verbose = verbose
        self.console = Console(markup=False, highlight=False)
        self.live = None
        self.task = None
        self.started = time.monotonic()
        self.stage = ""
        self.current = ""

    def begin(
        self, command: str, endpoint: str | None, source: str, count: int
    ) -> None:
        if self.enabled:
            self.console.print(f"PK-DB · {command.capitalize()} studies", style="bold")
            self.console.print(
                f"Server   {safe_text(endpoint or 'Offline')}\nSource   {safe_text(source)}\nStudies  {count}\n"
            )

    def start(self, name: str, index: int, total: int) -> None:
        self.current = f"[{index}/{total}] {safe_text(name)}"
        self.stage = ""
        if self.enabled:
            self.console.print(self.current, style="bold")
            if sys.stdout.isatty():
                self.live = Progress(
                    SpinnerColumn(),
                    TextColumn("{task.description}", markup=False),
                    TimeElapsedColumn(),
                    console=self.console,
                )
                self.task = self.live.add_task("Reading source files", total=None)
                self.live.start()

    def progress(self, event: ProgressEvent) -> None:
        labels = {
            "read": "Reading source files",
            "parse": "Parsing source tables",
            "validate": "Validating study",
            "compatibility": "Checking server compatibility",
            "transfer": "Transferring source bundle",
            "server_validation": "Waiting for server validation and save",
            "complete": "Save confirmed",
        }
        message = labels.get(event.stage, event.stage)
        if event.completed is not None:
            message += f" · {event.completed:,} bytes"
            if event.total:
                message += f" / {event.total:,} ({event.completed / event.total:.0%})"
        if self.live is not None and self.task is not None:
            self.live.update(self.task, description=message)
        elif self.enabled and (
            self.stage != event.stage
            or (event.total is not None and event.completed == event.total)
        ):
            self.console.print(f"  {message}")
        self.stage = event.stage

    def batch_progress(self, event) -> None:
        """Render independent task stages without changing single-study state."""
        if self.enabled:
            counts = ""
            if event.completed is not None:
                counts = f" · {event.completed:,} bytes"
                if event.total:
                    counts += (
                        f" / {event.total:,} ({event.completed / event.total:.0%})"
                    )
            self.console.print(
                f"  [{event.index + 1}] {safe_text(event.path)} · {safe_text(event.stage)}{counts}"
            )

    def stop(self) -> None:
        if self.live is not None:
            self.live.stop()
            self.live = None

    def result(self, result: dict) -> None:
        self.stop()
        if not self.enabled:
            return
        ok = result.get("ok", False)
        state = result.get("persistence", "not_attempted")
        label = (
            state.capitalize()
            if state in {"created", "replaced", "unknown"}
            else ("Valid" if ok else "Failed")
        )
        self.console.print(
            "  "
            + " · ".join(
                part
                for part in (
                    label,
                    safe_text(result.get("relative_path", "")),
                    safe_text(result.get("sid", "")),
                    f"{result.get('elapsed_seconds', 0):.1f}s",
                )
                if part
            ),
            style="green" if ok else "red",
        )
        if state in {"created", "replaced"} and result.get("counts"):
            counts = result["counts"]
            preferred = (
                "groups",
                "individuals",
                "interventions",
                "measurements",
                "timecourses",
                "attachments",
            )
            names = [name for name in preferred if name in counts]
            names.extend(sorted(set(counts) - set(preferred)))
            self.console.print(
                "  Uploaded: "
                + ", ".join(
                    f"{safe_text(name)}={safe_text(counts[name])}" for name in names
                )
            )
        if state == "unknown":
            self.console.print(
                "  Save outcome is unknown. Check the server before retrying."
            )
        elif not ok and state in {"created", "replaced"}:
            self.console.print(
                "  Save confirmed, but the request reported an error. Inspect the server before retrying."
            )
        elif not ok:
            self.console.print("  This attempt did not save study data.")
        if result.get("error"):
            self.console.print(f"  {safe_text(result['error'])}")
        if result.get("status_code") == 403:
            self.console.print(
                "  Forbidden (HTTP 403). PK-DB reports rate limits as HTTP 429."
            )
            if not result.get("report"):
                self.console.print(
                    "  Check the API key upload scope, account role, study assignment, and changes to creator or licence."
                )
        if result.get("status_code") == 429:
            self.console.print(
                "  Rate limited (HTTP 429). Batch stopped; review this study before restarting."
            )
        if result.get("retry_after") and result.get("status_code") in {429, 503}:
            self.console.print(
                f"  Retry-After: {safe_text(result['retry_after'])} (seconds or HTTP date)."
            )
        if result.get("url"):
            self.console.print(f"  {safe_text(result['url'])}")
        if result.get("request_id"):
            self.console.print(f"  Request: {safe_text(result['request_id'])}")
        report = result.get("report") or {}
        issues = report.get("issues", result.get("warnings", []))
        groups = {}
        for issue in issues:
            source = issue.get("source") or {}
            key = (
                issue.get("code"),
                issue.get("message"),
                source.get("file"),
                source.get("sheet"),
                json.dumps(issue.get("expected", {}), sort_keys=True),
            )
            groups.setdefault(key, []).append(issue)
        displayed = list(groups.values())
        for group in displayed if self.verbose else displayed[:5]:
            issue = group[0]
            source = issue.get("source") or {}
            location = [
                source.get("file"),
                source.get("sheet"),
                source.get("cell")
                or (f"row {source['row']}" if source.get("row") else None),
            ]
            if source.get("path"):
                location.append(
                    "/"
                    + "/".join(
                        str(part).replace("~", "~0").replace("/", "~1")
                        for part in source["path"]
                    )
                )
            self.console.print("  " + " → ".join(safe_text(x) for x in location if x))
            self.console.print(
                f"    {safe_text(issue.get('message', ''))} [{safe_text(issue.get('code', ''))}]"
            )
            if len(group) > 1:
                locations = [
                    (item.get("source") or {}).get("cell")
                    or str((item.get("source") or {}).get("row", "?"))
                    for item in group
                ]
                self.console.print(
                    f"    {len(group)} occurrences: {safe_text(', '.join(locations))}"
                )
            if "actual" in issue:
                self.console.print(
                    f"    Received: {safe_text(issue['actual']) if issue['actual'] is not None else 'empty (null)'}"
                )
            if issue.get("expected"):
                constraints = []
                for key, value in issue["expected"].items():
                    label = {
                        "minimum": "minimum",
                        "maximum": "maximum",
                        "vocabulary": "vocabulary category",
                    }.get(key, key.replace("_", " "))
                    rendered = (
                        ", ".join(str(item) for item in value)
                        if isinstance(value, list)
                        else str(value)
                    )
                    constraints.append(f"{label}: {rendered}")
                self.console.print(f"    Expected {safe_text('; '.join(constraints))}")
            for related in issue.get("related_sources", []):
                location = related.get("source", {})
                coordinate = " → ".join(
                    str(value)
                    for value in (
                        location.get("file"),
                        location.get("sheet"),
                        location.get("cell") or location.get("row"),
                    )
                    if value
                )
                self.console.print(
                    f"    Related {safe_text(related.get('label', 'source'))}: {safe_text(coordinate)}"
                )
            for suggestion in issue.get("suggestions", []):
                self.console.print(
                    f"    Next: {safe_text(suggestion.get('message', suggestion))}"
                )
                if suggestion.get("candidates"):
                    self.console.print(
                        "    Candidates to review: "
                        + safe_text(
                            ", ".join(str(value) for value in suggestion["candidates"])
                        )
                    )
                if suggestion.get("command"):
                    self.console.print(
                        f"    Command: {safe_text(suggestion['command'])}"
                    )
        if not self.verbose and len(displayed) > 5:
            self.console.print(
                f"  … {len(displayed) - 5} more issue groups; use --verbose or --report for all returned details."
            )
        if report.get("truncated") or report.get("complete") is False:
            self.console.print(
                "  Report is incomplete or truncated; fix reported issues and validate again."
            )

    def finish(self, summary: dict, path: str | None) -> None:
        self.stop()
        if self.enabled:
            self.console.print("\nSummary", style="bold")
            table = Table.grid(padding=(0, 2))
            table.add_column()
            table.add_column(justify="right")
            for key, value in summary.items():
                table.add_row(key.replace("_", " ").capitalize(), str(value))
            self.console.print(table)
            self.console.print(f"Elapsed: {time.monotonic() - self.started:.1f}s")
            if path:
                self.console.print(f"Report: {safe_text(path)}")
