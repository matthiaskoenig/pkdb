"""The sheet and the cell that a workbook opens at, set without changing a cell.

No spreadsheet program takes a sheet or a cell on its command line, so the app writes them
into the view of the workbook before it opens it: `activeTab` of the first `workbookView`
in `xl/workbook.xml`, and in each sheet `tabSelected`, the selection and the scroll
position of its `sheetView` of that workbook view. Only these start tags change, and a
`selection` is added to a sheet view without one; every other byte of these parts, and
every other part of the zip, stays as it was. Expat finds the tags by their namespace,
whatever prefix a writer gave it, and the edit rewrites the attributes in the bytes of a
tag. ElementTree would write each part anew: it renames the prefixes and drops the
namespace declarations that only `mc:Ignorable` names, and Excel takes such a part for
damaged.
"""

import os
import posixpath
import re
import zlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from xml.parsers import expat
from zipfile import BadZipFile, ZipFile, ZipInfo

from openpyxl.utils.cell import column_index_from_string, get_column_letter

from pkdb.cache import atomic_bytes
from pkdb.studyformat.workbook.base import open_lock

# The main namespace of SpreadsheetML and of the relationships of a part, transitional and
# strict.
MAIN = frozenset(
    {
        "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "http://purl.oclc.org/ooxml/spreadsheetml/main",
    }
)
RELATIONSHIPS = frozenset(
    {
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "http://purl.oclc.org/ooxml/officeDocument/relationships",
    }
)
PACKAGE_RELATIONSHIP = (
    "http://schemas.openxmlformats.org/package/2006/relationships Relationship"
)
WORKBOOK_PART = "xl/workbook.xml"
WORKBOOK_RELATIONSHIPS = "xl/_rels/workbook.xml.rels"
# The last cell of a sheet in Excel: column XFD, row 1,048,576.
MAX_COLUMN = 16384
MAX_ROW = 1048576
# The sheet opens with this many rows above the cell, and with this many columns before it
# when the cell is right of the first FIRST_COLUMNS columns.
ROWS_ABOVE = 3
COLUMNS_BEFORE = 2
FIRST_COLUMNS = 8
CELL = re.compile(r"([A-Z]{1,3})([1-9][0-9]{0,6})")
# A start tag; the quoted values of its attributes may hold ">".
START_TAG = re.compile(
    rb"""<([^\s/>]+)(?:\s+[^\s=/>]+\s*=\s*(?:"[^"]*"|'[^']*'))*\s*/?>"""
)
ATTRIBUTE = re.compile(rb"""(\s+)([^\s=/>]+)(\s*=\s*)(?:"[^"]*"|'[^']*')""")
TRUE = frozenset({"1", "true"})


class ViewError(Exception):
    """The workbook is no xlsx file whose view can be set; the message says why."""


class NoSheet(Exception):
    """The workbook has no visible sheet of that name."""


class HiddenSheet(NoSheet):
    """The workbook has a sheet of that name, but it is hidden."""


class WorkbookOpen(Exception):
    """A spreadsheet program has the workbook open, so it is not replaced."""


def parse_cell(cell: str) -> tuple[int, int]:
    """The column and the row, from 1, of a workbook address such as Y97; ValueError otherwise."""
    match = CELL.fullmatch(cell)
    if match is None:
        raise ValueError(f"{cell!r} is no workbook cell such as Y97")
    column, row = column_index_from_string(match[1]), int(match[2])
    if column > MAX_COLUMN or row > MAX_ROW:
        raise ValueError(f"{cell} is beyond the last cell of a sheet, XFD1048576")
    return column, row


@dataclass
class _Tag:
    """An element of the main namespace: its local name, the bytes of its start tag, its
    attributes, and where it closes: its end tag, or the end of an empty element."""

    name: str
    start: int
    end: int
    attributes: dict[str, str]
    empty: bool
    close: int = -1
    children: list[_Tag] = field(default_factory=list)


class _Done(Exception):
    """Stops expat after the last element that the view needs."""


def _elements(data: bytes, names: frozenset[str], last: str) -> list[_Tag]:
    """The elements of the main namespace named in `names`, in document order.

    Each lists the elements of `names` within it as its children. Expat stops at the end of
    the first `last` element, so the rows of a long sheet are not parsed.
    """
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        raise ViewError("a part of the workbook is not UTF-8")
    parser = expat.ParserCreate(namespace_separator=" ")
    found: list[_Tag] = []
    within: list[_Tag | None] = []

    def start(name: str, attributes: dict[str, str]) -> None:
        namespace, _, local = name.rpartition(" ")
        if namespace not in MAIN or local not in names:
            within.append(None)
            return
        offset = parser.CurrentByteIndex
        match = START_TAG.match(data, offset)
        if match is None:
            raise ViewError(f"the tag {local} of the workbook cannot be edited")
        tag = _Tag(local, offset, match.end(), attributes, match[0].endswith(b"/>"))
        parent = next((item for item in reversed(within) if item is not None), None)
        if parent is not None:
            parent.children.append(tag)
        found.append(tag)
        within.append(tag)

    def end(name: str) -> None:
        tag = within.pop()
        if tag is None:
            return
        tag.close = tag.end if tag.empty else parser.CurrentByteIndex
        if tag.name == last:
            raise _Done

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    try:
        parser.Parse(data, True)
    except _Done:
        pass
    except expat.ExpatError as error:
        raise ViewError(f"a part of the workbook is no XML: {error}") from None
    return found


def _number(tag: _Tag, name: str) -> int:
    """The whole number in the attribute `name` of `tag`, 0 without it.

    ViewError for a value that is no finite number: a ValueError means a bad cell address.
    """
    value = tag.attributes.get(name, "0")
    try:
        return int(float(value))
    except ValueError, OverflowError:
        raise ViewError(f"the {name} {value!r} of the workbook is no number") from None


def _with_attributes(tag: bytes, values: Mapping[str, str | None]) -> bytes:
    """The start tag `tag` with the attributes of `values` set, or removed for None.

    The other attributes keep their bytes; an attribute that `tag` lacks goes last.
    """
    missing = dict(values)

    def replace(match: re.Match[bytes]) -> bytes:
        name = match[2].decode("utf-8", "replace")
        if name not in missing:
            return match[0]
        value = missing.pop(name)
        if value is None:
            return b""
        return match[1] + match[2] + match[3] + b'"' + value.encode() + b'"'

    edited = ATTRIBUTE.sub(replace, tag)
    added = b"".join(
        b" " + name.encode() + b'="' + value.encode() + b'"'
        for name, value in missing.items()
        if value is not None
    )
    if not added:
        return edited
    closing = 2 if edited.endswith(b"/>") else 1
    return edited[:-closing].rstrip() + added + edited[-closing:]


@dataclass(frozen=True)
class _Edit:
    """Replace the bytes from `start` to `end` with `text`."""

    start: int
    end: int
    text: bytes


def _edited(data: bytes, edits: list[_Edit]) -> bytes:
    for edit in sorted(edits, key=lambda edit: edit.start, reverse=True):
        data = data[: edit.start] + edit.text + data[edit.end :]
    return data


def _attributes(
    data: bytes, tag: _Tag, values: Mapping[str, str | None]
) -> list[_Edit]:
    """The edit that sets `values` in the start tag of `tag`; none when it has them."""
    if all(tag.attributes.get(name) == value for name, value in values.items()):
        return []
    text = _with_attributes(data[tag.start : tag.end], values)
    return [_Edit(tag.start, tag.end, text)]


def _address(column: int, row: int) -> str:
    """The cell address of a column and a row; ViewError for a column outside the sheet."""
    try:
        return f"{get_column_letter(column)}{row}"
    except ValueError:
        raise ViewError(f"the column {column} of the workbook is no column") from None


def _select(data: bytes, view: _Tag, cell: str) -> list[_Edit]:
    """Select `cell` in the active pane of `view` and scroll the sheet to show it.

    The sheet shows ROWS_ABOVE rows above the cell, and COLUMNS_BEFORE columns before it
    when it is right of the first FIRST_COLUMNS columns. Frozen rows and columns stay; a
    split view keeps its scroll positions, as its panes are measured in points.
    """
    column, row = parse_cell(cell)
    left = 1 if column <= FIRST_COLUMNS else column - COLUMNS_BEFORE
    top = max(1, row - ROWS_ABOVE)
    pane = next((child for child in view.children if child.name == "pane"), None)
    active = (pane.attributes.get("activePane") if pane else None) or "topLeft"
    values: dict[str, str | None] = {"tabSelected": "1"}
    edits: list[_Edit] = []
    if pane is None:
        values["topLeftCell"] = _address(left, top)
    elif pane.attributes.get("state") in {"frozen", "frozenSplit"}:
        columns, rows = _number(pane, "xSplit"), _number(pane, "ySplit")
        # The top left pane scrolls only along the frozen edge that it does not have.
        values["topLeftCell"] = _address(
            left if columns == 0 else 1, top if rows == 0 else 1
        )
        edits += _attributes(
            data,
            pane,
            {"topLeftCell": _address(max(columns + 1, left), max(rows + 1, top))},
        )
    selection = next(
        (
            child
            for child in view.children
            if child.name == "selection"
            and (child.attributes.get("pane") or "topLeft") == active
        ),
        None,
    )
    if selection is not None:
        edits += _attributes(
            data, selection, {"activeCell": cell, "sqref": cell, "activeCellId": None}
        )
        return edits + _attributes(data, view, values)
    # A sheet view without a selection of its active pane gets one, after its pane.
    name = START_TAG.match(data, view.start)
    assert name is not None
    prefix = name[1][: -len(b"sheetView")]
    pane_attribute = b"" if active == "topLeft" else b' pane="' + active.encode() + b'"'
    added = b'<%bselection%b activeCell="%b" sqref="%b"/>' % (
        prefix,
        pane_attribute,
        cell.encode(),
        cell.encode(),
    )
    tag = _with_attributes(data[view.start : view.end], values)
    if view.empty:
        opened = tag[:-2].rstrip() + b">"
        closed = opened + added + b"</" + prefix + b"sheetView>"
        return edits + [_Edit(view.start, view.end, closed)]
    if pane is None:
        place = view.end
    elif pane.empty:
        place = pane.end
    else:
        place = data.index(b">", pane.close) + 1
    return edits + [_Edit(view.start, view.end, tag), _Edit(place, place, added)]


def _sheet(data: bytes, selected: bool, cell: str | None) -> bytes | None:
    """The sheet `data` with the tab of its first view selected or not, and `cell` selected.

    None when the sheet is like that already.
    """
    tags = _elements(
        data, frozenset({"sheetViews", "sheetView", "pane", "selection"}), "sheetViews"
    )
    view = next(
        (
            tag
            for tag in tags
            if tag.name == "sheetView"
            and tag.attributes.get("workbookViewId", "0") == "0"
        ),
        None,
    )
    if view is None:
        if selected:
            raise ViewError("the sheet has no view")
        return None
    if not selected:
        if view.attributes.get("tabSelected", "0") not in TRUE:
            return None
        edits = _attributes(data, view, {"tabSelected": None})
    elif cell is None:
        edits = _attributes(data, view, {"tabSelected": "1"})
    else:
        edits = _select(data, view, cell)
    return _edited(data, edits) if edits else None


@dataclass(frozen=True)
class _Sheet:
    name: str
    part: str
    visible: bool


def _sheets(workbook: bytes, relationships: bytes) -> tuple[list[_Sheet], _Tag]:
    """The sheets of a workbook in their order, and its first workbook view."""
    tags = _elements(workbook, frozenset({"workbookView", "sheets", "sheet"}), "sheets")
    view = next((tag for tag in tags if tag.name == "workbookView"), None)
    if view is None:
        raise ViewError("the workbook has no view")
    targets: dict[str, str] = {}
    parser = expat.ParserCreate(namespace_separator=" ")

    def relationship(name: str, attributes: dict[str, str]) -> None:
        if name == PACKAGE_RELATIONSHIP:
            targets[attributes.get("Id", "")] = attributes.get("Target", "")

    parser.StartElementHandler = relationship
    try:
        parser.Parse(relationships, True)
    except expat.ExpatError as error:
        raise ViewError(
            f"the relationships of the workbook are no XML: {error}"
        ) from None
    sheets = []
    for tag in tags:
        if tag.name != "sheet":
            continue
        identifier = next(
            (
                value
                for key, value in tag.attributes.items()
                if key.rpartition(" ")[0] in RELATIONSHIPS
                and key.rpartition(" ")[2] == "id"
            ),
            "",
        )
        target = targets.get(identifier)
        if not target:
            raise ViewError(f"the sheet {tag.attributes.get('name')} has no part")
        # openpyxl writes absolute targets, Excel and LibreOffice relative ones.
        part = (
            target.removeprefix("/")
            if target.startswith("/")
            else posixpath.normpath(posixpath.join("xl", target))
        )
        sheets.append(
            _Sheet(
                tag.attributes.get("name", ""),
                part,
                tag.attributes.get("state", "visible") == "visible",
            )
        )
    return sheets, view


def _entry(info: ZipInfo) -> ZipInfo:
    """A new entry of the name, time, compression and attributes of `info`."""
    entry = ZipInfo(info.filename, info.date_time)
    entry.compress_type = info.compress_type
    entry.create_system = info.create_system
    entry.external_attr = info.external_attr
    entry.comment = info.comment
    return entry


def with_view(data: bytes, sheet: str, cell: str | None = None) -> bytes | None:
    """The workbook `data` opening at `sheet`, with `cell` selected when given.

    None when it opens there already. NoSheet when the workbook has no visible sheet of the
    name, HiddenSheet when that sheet is hidden, ViewError when its view cannot be found,
    ValueError for a cell that is no workbook address. The entries keep their order, names,
    times and compression; only the parts whose view changes differ in their content.
    """
    if cell is not None:
        parse_cell(cell)
    try:
        archive = ZipFile(BytesIO(data))
    except BadZipFile as error:
        raise ViewError(f"the workbook is no xlsx file: {error}") from None
    with archive:
        try:
            workbook = archive.read(WORKBOOK_PART)
            sheets, view = _sheets(workbook, archive.read(WORKBOOK_RELATIONSHIPS))
            index = next(
                (number for number, entry in enumerate(sheets) if entry.name == sheet),
                None,
            )
            if index is None:
                raise NoSheet(sheet)
            if not sheets[index].visible:
                raise HiddenSheet(sheet)
            values: dict[str, str | None] = {"activeTab": str(index)}
            # The tab bar starts at the active sheet at the latest.
            if _number(view, "firstSheet") > index:
                values["firstSheet"] = str(index)
            parts: dict[str, bytes] = {}
            if edits := _attributes(workbook, view, values):
                parts[WORKBOOK_PART] = _edited(workbook, edits)
            for number, entry in enumerate(sheets):
                selected = number == index
                changed = _sheet(
                    archive.read(entry.part), selected, cell if selected else None
                )
                if changed is not None:
                    parts[entry.part] = changed
            if not parts:
                return None
            output = BytesIO()
            with ZipFile(output, "w", allowZip64=True) as written:
                written.comment = archive.comment
                for info in archive.infolist():
                    content = parts.get(info.filename)
                    written.writestr(
                        _entry(info),
                        archive.read(info) if content is None else content,
                    )
        except (
            BadZipFile,
            KeyError,
            NotImplementedError,
            EOFError,
            zlib.error,
        ) as error:
            raise ViewError(f"the workbook cannot be read: {error}") from None
    return output.getvalue()


def show_place(path: Path, sheet: str, cell: str | None = None) -> bool:
    """Make the workbook at `path` open at `sheet`, with `cell` selected; whether it changed.

    The workbook is replaced atomically through a temporary file in its folder. A workbook
    that a spreadsheet program has open raises WorkbookOpen; one saved while it was read, or
    in a folder that refuses the replace, raises ViewError. Each is left as it is.
    """
    before = path.stat()
    data = path.read_bytes()
    viewed = with_view(data, sheet, cell)
    if viewed is None:
        return False
    if open_lock(path) is not None:
        raise WorkbookOpen(path.name)
    now = path.stat()
    if (now.st_mtime_ns, now.st_size) != (before.st_mtime_ns, before.st_size):
        raise ViewError(f"{path.name} was saved meanwhile")
    try:
        atomic_bytes(path, viewed)
    except PermissionError:
        if os.name == "nt":
            # Windows keeps a workbook locked while a program has it open.
            raise WorkbookOpen(path.name) from None
        # Elsewhere programs lock no file: the folder refuses the write.
        raise ViewError(f"{path.name} cannot be replaced: permission denied") from None
    return True
