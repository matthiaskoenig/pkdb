"""The client reads and writes text files as UTF-8 with LF line endings, also on Windows.

Without an explicit encoding, Python 3.14 on Windows decodes and encodes text files in
the locale encoding, such as cp1252, which garbles the UTF-8 files of a study and
refuses characters such as Greek letters. Without an explicit newline, a text file
written on Windows gets CRLF line endings, which study files must not have.
"""

import ast
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "src" / "pkdb"
MODE = re.compile(r"[rwax][rwaxbt+]*")
SUBPROCESS = {"run", "Popen", "call", "check_call", "check_output"}


@dataclass(frozen=True)
class Opener:
    """Where a call that opens a file takes its arguments; None where it has none."""

    mode: int | None
    default: str
    encoding: int
    newline: int | None


# The signatures of open, io.open and os.fdopen.
OPEN = Opener(mode=1, default="r", encoding=3, newline=5)
# codecs.open reads and writes bytes when it has an encoding, so it has no newline.
CODECS_OPEN = Opener(mode=1, default="r", encoding=2, newline=None)
PATH_OPEN = Opener(mode=0, default="r", encoding=2, newline=4)
READ_TEXT = Opener(mode=None, default="r", encoding=0, newline=None)
WRITE_TEXT = Opener(mode=None, default="w", encoding=1, newline=3)
TEMPORARY_FILE = Opener(mode=0, default="w+b", encoding=2, newline=3)


def _argument(call: ast.Call, position: int | None, name: str) -> ast.expr | None:
    """An argument given at its position or by keyword; None when missing or None."""
    if position is not None and position < len(call.args):
        value = call.args[position]
    else:
        value = next((k.value for k in call.keywords if k.arg == name), None)
    if isinstance(value, ast.Constant) and value.value is None:
        return None
    return value


def _opener(call: ast.Call) -> Opener | None:
    function = call.func
    if isinstance(function, ast.Name):
        owner, name = None, function.id
    elif isinstance(function, ast.Attribute):
        value = function.value
        owner = value.id if isinstance(value, ast.Name) else ""
        name = function.attr
    else:
        return None
    match owner, name:
        case (None, "open") | ("io", "open") | ("os", "fdopen"):
            return OPEN
        case ("codecs", "open"):
            return CODECS_OPEN
        case (_, "NamedTemporaryFile" | "TemporaryFile"):
            return TEMPORARY_FILE
        case (str(), "read_text"):
            return READ_TEXT
        case (str(), "write_text"):
            return WRITE_TEXT
        case (str(), "open"):
            # Path.open(mode, ...); other open methods, such as ZipFile.open, take a
            # name first.
            first = _argument(call, 0, "mode")
            if first is None or (
                isinstance(first, ast.Constant) and MODE.fullmatch(str(first.value))
            ):
                return PATH_OPEN
    return None


def _subprocess_problems(call: ast.Call) -> list[str]:
    """A subprocess call that decodes its output in the locale encoding."""
    function = call.func
    if not (
        isinstance(function, ast.Attribute)
        and isinstance(function.value, ast.Name)
        and function.value.id == "subprocess"
        and function.attr in SUBPROCESS
    ):
        return []
    text = [
        k.value
        for k in call.keywords
        if k.arg in {"text", "universal_newlines"}
        and not (isinstance(k.value, ast.Constant) and not k.value.value)
    ]
    if text and _argument(call, None, "encoding") is None:
        return ["encoding"]
    return []


def _problems(call: ast.Call) -> list[str]:
    """What a call that opens a file in text mode leaves to the platform."""
    opener = _opener(call)
    if opener is None:
        return _subprocess_problems(call)
    mode: str | None = opener.default
    if opener.mode is not None:
        given = _argument(call, opener.mode, "mode")
        if isinstance(given, ast.Constant) and isinstance(given.value, str):
            mode = given.value
        elif given is not None:
            mode = None
    if mode is not None and "b" in mode:
        return []
    problems = []
    if _argument(call, opener.encoding, "encoding") is None:
        problems.append("encoding")
    writes = mode is None or any(c in mode for c in "wax+")
    if (
        writes
        and opener.newline is not None
        and _argument(call, opener.newline, "newline") is None
    ):
        problems.append("newline")
    return problems


def _calls_left_to_the_platform(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        f"{path.relative_to(SOURCE).as_posix()}:{node.lineno} {', '.join(problems)}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and (problems := _problems(node))
    ]


def test_every_text_file_is_opened_with_an_encoding_and_a_newline():
    found = [
        location
        for path in sorted(SOURCE.rglob("*.py"))
        for location in _calls_left_to_the_platform(path)
    ]
    assert found == []


@pytest.mark.parametrize(
    ("source", "problems"),
    [
        ("path.read_text()", ["encoding"]),
        ("path.read_text('utf-8')", []),
        ("path.read_text(encoding='utf-8')", []),
        ("distribution.read_text('direct_url.json')", []),
        ("path.write_text(text)", ["encoding", "newline"]),
        ("path.write_text(text, encoding='utf-8')", ["newline"]),
        ("path.write_text(text, 'utf-8', None, '')", []),
        ("path.write_text(text, encoding='utf-8', newline='')", []),
        ("open(path)", ["encoding"]),
        ("open(path, 'w')", ["encoding", "newline"]),
        ("open(path, mode='a', encoding='utf-8')", ["newline"]),
        ("open(path, 'rb')", []),
        ("open(path, mode='wb')", []),
        ("open(path, 'w', encoding='utf-8', newline='')", []),
        ("open(path, mode, encoding='utf-8')", ["newline"]),
        ("path.open('w', encoding='utf-8')", ["newline"]),
        ("path.open(newline='', encoding='utf-8-sig')", []),
        ("archive.open(name)", []),
        ("NamedTemporaryFile(dir=folder)", []),
        ("NamedTemporaryFile('w', encoding='utf-8')", ["newline"]),
        ("NamedTemporaryFile('w', encoding='utf-8', newline='')", []),
        ("tempfile.NamedTemporaryFile('w', encoding='utf-8')", ["newline"]),
        ("open(path, 'w', -1, 'utf-8', None, '')", []),
        ("open(path, 'w', -1, 'utf-8', None, None, True)", ["newline"]),
        ("path.open('w', -1, 'utf-8', None, '')", []),
        ("path.open('r', -1, 'utf-8')", []),
        ("path.read_text(encoding=None)", ["encoding"]),
        ("path.write_text(text, encoding='utf-8', newline=None)", ["newline"]),
        ("io.open(path, 'w', encoding='utf-8')", ["newline"]),
        ("io.open(path, 'rb')", []),
        ("os.fdopen(descriptor, 'w')", ["encoding", "newline"]),
        ("os.fdopen(descriptor, 'wb')", []),
        ("codecs.open(path, 'w')", ["encoding"]),
        ("codecs.open(path, 'w', 'utf-8')", []),
        ("subprocess.run(command, text=True)", ["encoding"]),
        ("subprocess.check_output(command, universal_newlines=True)", ["encoding"]),
        ("subprocess.run(command, text=True, encoding='utf-8')", []),
        ("subprocess.run(command, encoding='utf-8')", []),
        ("subprocess.run(command, text=False)", []),
        ("subprocess.run(command, capture_output=True)", []),
    ],
)
def test_text_files_left_to_the_platform_are_found(source, problems):
    [statement] = ast.parse(source).body
    assert isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call)
    assert _problems(statement.value) == problems
