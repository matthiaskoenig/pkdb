"""What each request of the local curation app does, in words.

The label names a request in its error body, the log and the terminal, such as "Open
tables"; the phrase says what could not be done, with the study, such as "open the tables of
caffeine/Demo2020". The body of a request may be missing or anything: the words never fail.
"""

from dataclasses import dataclass
from urllib.parse import unquote

#: How a phrase names the study of a request that names none.
THE_STUDY = "the study"


@dataclass(frozen=True)
class Action:
    """A request of the app: what it does, its method and path, and the study it names."""

    label: str
    #: What the request does, after "Could not": "open the tables of caffeine/Demo2020".
    phrase: str
    method: str
    path: str
    #: The study `<substance>/<name>` of the request, when it names one.
    study: str | None = None
    #: Whether the activity of the study lists a failure: writes and opened files.
    recorded: bool = False

    def text(self) -> str:
        """The `action` of an error body: the label with the method and the path."""
        return f"{self.label} ({self.method} {self.path})"

    def failure(self) -> str:
        """The message of a failure: `Could not open the tables of caffeine/Demo2020.`"""
        return f"Could not {self.phrase}."


#: The label and the phrase of each POST route that names no study.
WORKSPACE_ROUTES: dict[str, tuple[str, str]] = {
    "/local/session": ("Start the session", "start the session"),
    "/local/workspace": ("Choose the workspace", "open the workspace"),
    "/local/workspace/forget": ("Forget a workspace", "forget the workspace"),
    "/local/directories": ("List folders", "list the folders"),
    "/local/settings": ("Save the settings", "save the settings"),
    "/local/mode": ("Set the On save action", "set the On save action"),
    "/local/jobs/cancel": ("Cancel jobs", "cancel the jobs"),
    "/local/history/clear": (
        "Clear the finished history",
        "clear the finished history",
    ),
    "/local/retry": ("Upload again", "upload the study again"),
    "/local/assignments/refresh": (
        "Refresh the assignments",
        "refresh the GitHub assignments",
    ),
    "/local/resume": ("Resume automatic actions", "resume the automatic actions"),
}
#: The label and the phrase of each POST route of a study; "{study}" stands for the study.
STUDY_ROUTES: dict[str, tuple[str, str]] = {
    "/local/studies/metadata": ("Save study.json", "save study.json of {study}"),
    "/local/studies/tables/preview": (
        "Preview a table",
        "preview the new table of {study}",
    ),
    "/local/studies/review/preview": (
        "Preview a review target",
        "preview the review target of {study}",
    ),
    "/local/reference/read": ("Read reference.json", "read reference.json of {study}"),
    "/local/reference/search": (
        "Search the publication",
        "search the publication of {study}",
    ),
    "/local/reference/preview": (
        "Preview the reference",
        "preview the reference of {study}",
    ),
    "/local/reference/save": ("Save reference.json", "save reference.json of {study}"),
}
#: The field of the body that names the study, by route.
STUDY_FIELDS: dict[str, str] = {
    "/local/studies/metadata": "study",
    "/local/studies/review": "study",
    "/local/studies/tables": "study",
    "/local/studies/tables/preview": "study",
    "/local/studies/review/preview": "study",
    "/local/reference/read": "id",
    "/local/reference/search": "id",
    "/local/reference/preview": "id",
    "/local/reference/save": "id",
    "/local/files/open": "study_id",
}
#: The actions of POST /local/studies/review.
REVIEW_ACTIONS: dict[str, tuple[str, str]] = {
    "add": ("Add a review item", "add the review item to {study}"),
    "reply": ("Reply to a review item", "reply to the review item of {study}"),
    "resolve": ("Resolve a review item", "resolve the review item of {study}"),
    "dismiss": ("Dismiss a review item", "dismiss the review item of {study}"),
    "reopen": ("Reopen a review item", "reopen the review item of {study}"),
    "status": ("Set the review status", "set the review status of {study}"),
    "acknowledge": ("Acknowledge a warning", "acknowledge the warning of {study}"),
}
REVIEW_DEFAULT = ("Change review.json", "change review.json of {study}")
#: The actions of POST /local/studies/tables.
TABLES_ACTIONS: dict[str, tuple[str, str]] = {
    "open": ("Open tables", "open the tables of {study}"),
    "sync": ("Sync the workbook", "sync the workbook of {study}"),
    "resolve": ("Resolve the sync conflicts", "resolve the sync conflicts of {study}"),
    "add": ("Add a table", "add the table to {study}"),
}
TABLES_DEFAULT = ("Change the tables", "change the tables of {study}")
#: The jobs of POST /local/jobs.
JOB_ACTIONS: dict[str, tuple[str, str]] = {
    "validate": ("Validate", "start the validation"),
    "validate_remote": ("Validate on the server", "start the server validation"),
    "upload": ("Upload", "start the upload"),
}
JOBS_DEFAULT = ("Start jobs", "start the jobs")
PAUSE = ("Pause automatic actions", "pause the automatic actions")
UNPAUSE = ("Restart automatic actions", "restart the automatic actions")
UNKNOWN = ("Request", "complete the request")
#: The routes whose failures the activity of their study lists: writes and opened files.
RECORDED = frozenset(
    {
        "/local/studies/metadata",
        "/local/studies/review",
        "/local/studies/tables",
        "/local/reference/save",
        "/local/files/open",
    }
)


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _post(path: str, body: dict, study: str | None) -> tuple[str, str]:
    """The label and the phrase of a POST route with its body."""
    named = study or THE_STUDY
    match path:
        case "/local/studies/review":
            pair = REVIEW_ACTIONS.get(_text(body.get("action")) or "", REVIEW_DEFAULT)
        case "/local/studies/tables":
            pair = TABLES_ACTIONS.get(_text(body.get("action")) or "", TABLES_DEFAULT)
        case "/local/jobs":
            pair = JOB_ACTIONS.get(_text(body.get("action")) or "", JOBS_DEFAULT)
        case "/local/pause":
            pair = UNPAUSE if body.get("paused") is False else PAUSE
        case "/local/files/open":
            file = _text(body.get("file"))
            if file is None:
                return "Open folder", f"open the folder of {named}"
            if body.get("reveal"):
                return "Show in folder", f"show {file} of {named} in its folder"
            return "Open file", f"open {file} of {named}"
        case _:
            pair = STUDY_ROUTES.get(path) or WORKSPACE_ROUTES.get(path, UNKNOWN)
    label, phrase = pair
    return label, phrase.replace("{study}", named)


def _read(method: str, path: str) -> Action:
    """The words of a GET request."""
    if path == "/local/state":
        return Action(
            "Read the workspace state", "read the workspace state", method, path
        )
    if path == "/local/curators":
        return Action("Read the curators", "read the curator roster", method, path)
    if path.startswith("/local/reports/"):
        return Action("Read a report", "read the report", method, path)
    if path.startswith("/local/studies/"):
        parts = [
            unquote(part) for part in path.removeprefix("/local/studies/").split("/")
        ]
        study = "/".join(parts[:2]) if len(parts) >= 2 and all(parts[:2]) else None
        named = study or THE_STUDY
        match parts[2:]:
            case ["tables", file]:
                label, phrase = "Read a table", f"read {file} of {named}"
            case ["sources", source]:
                label, phrase = "Read a source", f"read the source {source} of {named}"
            case ["files", file]:
                label, phrase = "Read a file", f"read {file} of {named}"
            case _:
                label, phrase = "Read the study", f"read {named}"
        return Action(label, phrase, method, path, study)
    return Action("Read a page", "read the page", method, path)


def action_of(method: str, path: str, body: object = None) -> Action:
    """What the request `method` `path` with the JSON `body` does."""
    if method != "POST":
        return _read(method, path)
    fields = body if isinstance(body, dict) else {}
    field = STUDY_FIELDS.get(path)
    study = _text(fields.get(field)) if field else None
    label, phrase = _post(path, fields, study)
    return Action(
        label, phrase, method, path, study, path in RECORDED and study is not None
    )
