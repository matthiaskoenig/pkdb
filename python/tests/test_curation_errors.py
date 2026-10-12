"""The error body, the redaction and the log of the local curation app."""

import json
import re
import subprocess
from datetime import datetime

import pytest

from pkdb.curation.errors import (
    LOG_BACKUPS,
    LOG_BYTES,
    REPEAT_SECONDS,
    STDERR_TAIL,
    ActionFailed,
    ErrorLog,
    MissingField,
    describe,
    detail_of,
    new_request_id,
    redact,
    required,
    without_traceback,
)

SECRET = "pkdb-api-key-0123456789"
OPEN = "Open tables (POST /local/studies/tables)"


def test_redact_replaces_every_secret_the_longest_first():
    assert (
        redact("key abc-123 and abc", ["abc", "abc-123", None, ""])
        == "key [redacted] and [redacted]"
    )


def test_blank_values_are_no_secrets():
    assert redact("a b  c", ["", " ", "\t", None]) == "a b  c"


def test_a_secret_with_surrounding_whitespace_is_redacted_without_it():
    assert redact("token=ghp_1234", [" ghp_1234\n"]) == "token=[redacted]"


def test_a_failed_command_names_its_program_exit_status_and_the_end_of_its_stderr():
    stderr = b"x" * 3000 + "\u00fcnicode end".encode()
    error = subprocess.CalledProcessError(
        4, ["/usr/bin/xdg-open", "/x/Demo2020.xlsx"], stderr=stderr
    )
    head, tail = detail_of(error).split("\n", 1)
    assert head == "CalledProcessError: xdg-open exited with status 4"
    assert tail.endswith("\u00fcnicode end")
    assert len(tail.encode()) <= STDERR_TAIL


def test_stderr_that_is_no_utf8_does_not_break_the_detail():
    error = subprocess.CalledProcessError(1, "false", stderr=b"\xff\xfe broken")
    assert (
        detail_of(error)
        == "CalledProcessError: false exited with status 1\n\ufffd\ufffd broken"
    )


def test_a_command_without_stderr_has_no_second_line():
    error = subprocess.CalledProcessError(1, ["false", "/x"], stderr=b"")
    assert detail_of(error) == "CalledProcessError: false exited with status 1"


def test_a_windows_command_line_names_its_program():
    command = '"C:\\Program Files\\Rec\\rec.exe" --flag "C:\\x.xlsx"'
    error = subprocess.CalledProcessError(1, command)
    assert detail_of(error) == "CalledProcessError: rec.exe exited with status 1"


def test_a_command_that_did_not_return():
    error = subprocess.TimeoutExpired(["xdg-open", "/x"], 15)
    assert (
        detail_of(error) == "TimeoutExpired: xdg-open did not return within 15 seconds"
    )


def test_other_errors_give_their_type_and_text():
    assert detail_of(ValueError("Unknown setting")) == "ValueError: Unknown setting"
    assert detail_of(RuntimeError()) == "RuntimeError"


def test_an_action_that_failed_brings_its_message_code_and_cause():
    cause = subprocess.CalledProcessError(1, ["false", "/x/Demo2020.xlsx"], stderr=b"")
    failed = ActionFailed(
        "Could not open the tables of caffeine/Demo2020.",
        code="open_failed",
        cause=cause,
    )
    body = describe(
        failed, action=OPEN, request_id="3f9c2a71", message="ignored", code="ignored"
    )
    assert {key: body[key] for key in ("error", "code", "detail", "action")} == {
        "error": "Could not open the tables of caffeine/Demo2020.",
        "code": "open_failed",
        "detail": "CalledProcessError: false exited with status 1",
        "action": OPEN,
    }
    assert body["request_id"] == "3f9c2a71"
    assert "traceback" not in body
    time = datetime.fromisoformat(body["time"])
    assert time.utcoffset() == datetime.now().astimezone().utcoffset()


def test_a_refusal_for_the_curator_is_not_repeated_as_detail():
    body = describe(
        ValueError("Folder does not exist: /x"),
        action="List folders (POST /local/directories)",
        request_id="3f9c2a71",
        code="workspace_refused",
        detailed=False,
    )
    assert (body["error"], body["code"], body["detail"]) == (
        "Folder does not exist: /x",
        "workspace_refused",
        None,
    )


def test_a_generic_failure_keeps_the_text_of_the_error_in_the_detail():
    body = describe(
        ValueError("Unknown setting"),
        action="Save the settings (POST /local/settings)",
        request_id="3f9c2a71",
        message="Could not save the settings.",
        code="invalid_request",
    )
    assert (body["error"], body["detail"]) == (
        "Could not save the settings.",
        "ValueError: Unknown setting",
    )


def test_describe_redacts_message_detail_action_and_traceback():
    try:
        raise RuntimeError(f"echoed {SECRET}")
    except RuntimeError as error:
        body = describe(
            error,
            action=f"Save the settings ({SECRET})",
            request_id="3f9c2a71",
            message=f"Could not use {SECRET}.",
            code="unexpected",
            unexpected=True,
            secrets=[SECRET],
        )
    assert SECRET not in json.dumps(body)
    assert body["error"] == "Could not use [redacted]."
    assert body["detail"] == "RuntimeError: echoed [redacted]"
    assert body["action"] == "Save the settings ([redacted])"
    assert "RuntimeError: echoed [redacted]" in body["traceback"]
    assert without_traceback(body) == {
        "error": "Could not use [redacted].",
        "code": "unexpected",
        "detail": "RuntimeError: echoed [redacted]",
        "action": "Save the settings ([redacted])",
        "request_id": "3f9c2a71",
        "time": body["time"],
    }


def test_request_ids_are_eight_hex_characters():
    first, second = new_request_id(), new_request_id()
    assert re.fullmatch(r"[0-9a-f]{8}", first) and first != second


def test_a_missing_field_is_named():
    with pytest.raises(MissingField, match='Missing field "ids"') as missing:
        required({}, "ids")
    assert missing.value.name == "ids"
    assert required({"ids": []}, "ids") == []


def test_the_log_keeps_the_traceback_without_secrets_and_names_it_in_the_terminal(
    tmp_path, capsys
):
    secrets = []
    log = ErrorLog(tmp_path / "logs" / "curation.log", lambda: secrets)
    # A secret that becomes known after the log was opened is redacted too.
    secrets.append(SECRET)
    try:
        raise RuntimeError(f"echoed {SECRET}")
    except RuntimeError as error:
        body = describe(
            error,
            action=OPEN,
            request_id="3f9c2a71",
            message="Could not open the tables of caffeine/Demo2020.",
            code="unexpected",
            unexpected=True,
            secrets=secrets,
        )
        log.unexpected(body, error, label="Open tables")
    log.close()
    text = log.path.read_text(encoding="utf-8")
    assert f"ERROR Error 3f9c2a71 in {OPEN}: RuntimeError: echoed [redacted]" in text
    assert "Traceback (most recent call last)" in text
    assert SECRET not in text
    assert capsys.readouterr().err == (
        f"Error 3f9c2a71 in Open tables: RuntimeError (see {log.path})\n"
    )
    assert (log.handler.maxBytes, log.handler.backupCount) == (LOG_BYTES, LOG_BACKUPS)
    assert (LOG_BYTES, LOG_BACKUPS) == (1024 * 1024, 3)


def test_an_expected_failure_goes_to_the_file_and_the_terminal(tmp_path, capsys):
    log = ErrorLog(tmp_path / "logs" / "curation.log", lambda: [])
    cause = subprocess.CalledProcessError(1, ["false", "/x"], stderr=b"")
    try:
        raise ActionFailed(
            "Could not open the tables of caffeine/Demo2020.",
            code="open_failed",
            cause=cause,
        ) from cause
    except ActionFailed as failed:
        body = describe(failed, action=OPEN, request_id="0badc0de")
        log.failed(body, failed)
    log.close()
    text = log.path.read_text(encoding="utf-8")
    assert f"WARNING Error 0badc0de in {OPEN}: CalledProcessError" in text
    assert "subprocess.CalledProcessError" in text
    assert capsys.readouterr().err == (
        f"Error 0badc0de in {OPEN}: CalledProcessError (see {log.path})\n"
    )


def test_a_closed_log_writes_nothing_anywhere(tmp_path, capsys):
    log = ErrorLog(tmp_path / "logs" / "curation.log", lambda: [])
    log.close()
    body = {"request_id": "3f9c2a71", "action": OPEN, "detail": None, "error": "x"}
    log.failed(body, RuntimeError("x"))
    assert not log.path.exists()
    # The last resort handler of logging would print the record unredacted.
    assert capsys.readouterr().err == ""


def test_a_console_that_cannot_encode_the_line_does_not_fail_the_handling(
    tmp_path, monkeypatch
):
    class Console:
        def write(self, text):
            raise UnicodeEncodeError("ascii", text, 0, 1, "no")

        def flush(self):
            pass

    monkeypatch.setattr("sys.stderr", Console())
    log = ErrorLog(tmp_path / "logs" / "curation.log", lambda: [])
    body = {"request_id": "3f9c2a71", "action": OPEN, "detail": None, "error": "x"}
    log.failed(body, RuntimeError("x"))
    log.close()
    assert "Error 3f9c2a71" in log.path.read_text(encoding="utf-8")


class BrokenConsole:
    """A console whose stream fails in a way no console should."""

    def write(self, text):
        raise RuntimeError("the console is gone")

    def flush(self):
        pass


@pytest.mark.parametrize(
    "console", [None, BrokenConsole()], ids=["no console", "broken console"]
)
def test_a_missing_or_broken_console_does_not_fail_the_handling(
    tmp_path, monkeypatch, console
):
    # pythonw on Windows has no console: sys.stderr is None.
    monkeypatch.setattr("sys.stderr", console)
    log = ErrorLog(tmp_path / "logs" / "curation.log", lambda: [])
    body = {"request_id": "3f9c2a71", "action": OPEN, "detail": None, "error": "x"}
    log.failed(body, RuntimeError("x"))
    log.unexpected(body, RuntimeError("x"), label="Open tables")
    log.close()
    assert log.path.read_text(encoding="utf-8").count("Error 3f9c2a71") == 2


class Clock:
    """A clock whose seconds pass when the test says so."""

    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def _read_failure(request_id, detail="PermissionError: outputs_Tab2.tsv"):
    """The body of a failed read of the study detail, which the app polls."""
    return {
        "error": "Could not read caffeine/Demo2020.",
        "code": "file_error",
        "detail": detail,
        "action": "Read the study (GET /local/studies/caffeine/Demo2020)",
        "request_id": request_id,
    }


def test_a_repeated_failure_is_logged_and_named_once_a_minute(tmp_path, capsys):
    clock = Clock()
    log = ErrorLog(tmp_path / "logs" / "curation.log", lambda: [], clock=clock)
    try:
        raise PermissionError(13, "Permission denied")
    except PermissionError as raised:
        error = raised
    # The app polls the study every 1.5 seconds: the same failure, again and again.
    for index, request_id in enumerate(["00000001", "00000002", "00000003"]):
        clock.now = 1000.0 + 1.5 * index
        log.failed(_read_failure(request_id), error, label="Read the study")
    # The same detail of another action, and another detail of the same action.
    log.failed(_read_failure("00000004"), error, label="Read a table")
    log.failed(
        _read_failure("00000005", "PermissionError: other"),
        error,
        label="Read the study",
    )
    # A minute after it was logged, the failure is logged again.
    clock.now = 1000.0 + REPEAT_SECONDS
    log.failed(_read_failure("00000006"), error, label="Read the study")
    log.close()
    text = log.path.read_text(encoding="utf-8")
    assert text.count("Traceback") == 4
    # A repeat names the failure that the log keeps with its traceback, in one line.
    repeat = (
        "WARNING Error {} in Read the study (GET /local/studies/caffeine/Demo2020) "
        "repeats Error 00000001, which the log has with its traceback"
    )
    assert repeat.format("00000002") in text
    assert repeat.format("00000003") in text
    terminal = [
        line.split(" (see ")[0] for line in capsys.readouterr().err.splitlines()
    ]
    assert terminal == [
        "Error 00000001 in Read the study: PermissionError",
        "Error 00000004 in Read a table: PermissionError",
        "Error 00000005 in Read the study: PermissionError",
        "Error 00000006 in Read the study: PermissionError",
    ]
    assert REPEAT_SECONDS == 60
