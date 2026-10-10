"""The client reads and writes text files as UTF-8 with LF line endings, also on Windows.

Without an explicit encoding, Python 3.14 on Windows decodes and encodes text files in
the locale encoding, such as cp1252, which garbles the UTF-8 files of a study and
refuses characters such as Greek letters. Without an explicit newline, a text file
written on Windows gets CRLF line endings, which study files must not have.
"""

import ast
import re
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "src" / "pkdb"
MODE = re.compile(r"[rwax][rwaxbt+]*")


def _argument(call: ast.Call, position: int, name: str) -> ast.expr | None:
    """An argument given by keyword or at its position."""
    if position < len(call.args):
        return call.args[position]
    return next((k.value for k in call.keywords if k.arg == name), None)


def _mode(call: ast.Call, position: int, default: str) -> str | None:
    """The constant mode of a call; None when it is not a constant."""
    mode = _argument(call, position, "mode")
    if mode is None:
        return default
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        return mode.value
    return None


def _problems(call: ast.Call) -> list[str]:
    """What a call that opens a file in text mode leaves to the platform."""
    function = call.func
    name = function.attr if isinstance(function, ast.Attribute) else None
    if isinstance(function, ast.Name):
        name = function.id
    if name == "read_text" and isinstance(function, ast.Attribute):
        # Path.read_text(encoding, errors); importlib's read_text takes a file name.
        mode, encoding, newline = "r", _argument(call, 0, "encoding"), None
    elif name == "write_text" and isinstance(function, ast.Attribute):
        # Path.write_text(data, encoding, errors, newline)
        mode = "w"
        encoding, newline = (
            _argument(call, 1, "encoding"),
            _argument(call, 3, "newline"),
        )
    elif name == "open" and isinstance(function, ast.Name):
        mode = _mode(call, 1, "r")
        encoding, newline = (
            _argument(call, 3, "encoding"),
            _argument(call, 6, "newline"),
        )
    elif name == "open" and isinstance(function, ast.Attribute):
        # Path.open(mode, ...); other open methods, such as ZipFile.open, take a name.
        first = _argument(call, 0, "mode")
        if first is None:
            mode = "r"
        elif isinstance(first, ast.Constant) and MODE.fullmatch(str(first.value)):
            mode = str(first.value)
        else:
            return []
        encoding, newline = (
            _argument(call, 3, "encoding"),
            _argument(call, 4, "newline"),
        )
    elif name == "NamedTemporaryFile":
        mode = _mode(call, 0, "w+b")
        encoding, newline = (
            _argument(call, 2, "encoding"),
            _argument(call, 3, "newline"),
        )
    else:
        return []
    if mode is not None and "b" in mode:
        return []
    problems = []
    if encoding is None:
        problems.append("encoding")
    writes = mode is None or any(c in mode for c in "wax+")
    if writes and newline is None:
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
    ],
)
def test_text_files_left_to_the_platform_are_found(source, problems):
    [statement] = ast.parse(source).body
    assert isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call)
    assert _problems(statement.value) == problems
