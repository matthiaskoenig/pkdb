"""Hidden TSV tables generated from a study's Excel workbook.

Each non-empty ``Tab*`` or ``Fig*`` sheet of ``<Study>/<Study>.xlsx`` is written to
``.<Study>_<Sheet>.tsv`` in the same format as the legacy upload: the description
row is skipped, ``#`` starts a comment, unnamed columns and empty rows are dropped,
and missing values are written as ``NA``. Validation reads the workbook itself; the
TSV files keep a reviewable text copy of each table next to it.

The workbook is read with calamine (through fastexcel) and tabulated with polars.
Cells and columns are converted by the rules of the earlier pandas implementation,
so regenerating the tables of existing studies leaves their files unchanged:

* Text from the first ``#`` of a cell and all later cells of its row are dropped.
  Lines that are only a comment are skipped before the first data lines; later
  ones, like blank lines, count as missing values until empty rows are dropped.
* The first remaining line names the columns. Empty names become ``Unnamed: <n>``
  (and are dropped); repeated names are numbered ``name.1``, ``name.2``, ...
* A column is numeric when all its values are numbers, booleans, or numeric text
  (booleans alone only with missing values). It is written as integers unless it
  has missing or fractional values.
* Boolean text (``True``, ``false``, ...) is written as ``True``/``False``, and a
  column of dates as dates, with times only where any cell has one.
* Other columns keep each cell as written: text unchanged, numbers in their shortest
  form, booleans as ``True``/``False``, and dates as ``YYYY-MM-DD HH:MM:SS``.

Rare differences remain where calamine reads cells differently from openpyxl: error
cells (such as ``#N/A``) used as column names, whitespace-only text written without
``xml:space="preserve"``, and corrupted ``_xHHHH_`` escapes.
"""

import os
from glob import escape
from pathlib import Path
from tempfile import NamedTemporaryFile

import fastexcel
import polars as pl

from pkdb.studyformat.validation import is_v2_folder

SHEET_PREFIXES = ("Tab", "Fig")
COMMENT = "#"
# Text read as a missing value, as in the earlier pandas tables.
NA_STRINGS = (
    "",
    "#N/A",
    "#N/A N/A",
    "#NA",
    "-1.#IND",
    "-1.#QNAN",
    "-NaN",
    "-nan",
    "1.#IND",
    "1.#QNAN",
    "<NA>",
    "N/A",
    "NA",
    "NULL",
    "NaN",
    "None",
    "n/a",
    "nan",
    "null",
)
BOOLEAN_STRINGS = ("True", "TRUE", "true", "False", "FALSE", "false")
# Numeric text may be padded with ASCII whitespace only (not, e.g., no-break spaces).
INTEGER_TEXT = r"^[ \t\n\v\f\r]*[+-]?[0-9]+[ \t\n\v\f\r]*$"
NUMBER_TEXT = (
    r"(?i)^[ \t\n\v\f\r]*[+-]?"
    r"([0-9]+\.?[0-9]*(e[+-]?[0-9]+)?|\.[0-9]+(e[+-]?[0-9]+)?|inf|infinity)"
    r"[ \t\n\v\f\r]*$"
)
ASCII_WHITESPACE = " \t\n\v\f\r"
# calamine reads date and time cells as text of this form; times fall on 1899-12-31.
DATETIME_TEXT = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d+)?$"
TIME_DATE = "1899-12-31 "
# polars and Python print floats alike in this range; others use Python's repr.
POSITIONAL = (1e-4, 1e16)

# Cell kinds
EMPTY, TEXT, NUMBER, BOOLEAN, DATE, TIME = range(6)
# Column modes: how a column's values are written
CELLS, INTEGERS, FLOATS, BOOLEANS, DATES = range(5)


class WorkbookError(ValueError):
    """The study workbook cannot be read."""


def _sheet(reader, name: str, sheet: int) -> pl.LazyFrame | None:
    """The cells below a sheet's description row, one row per cell."""
    loads = [
        reader.load_sheet(name, header_row=None, skip_rows=[0], dtypes=dtype)
        for dtype in ("string", "float", "boolean")
    ]
    columns = loads[0].available_columns()
    text, number, boolean = (load.to_polars() for load in loads)
    if not columns or text.is_empty():
        return None
    offset, height = columns[0].absolute_index, text.height
    return (
        pl.DataFrame(
            {
                "text": pl.concat(text.get_columns()),
                "number": pl.concat(number.get_columns()),
                # Only number and boolean cells have a boolean reading.
                "readable": pl.concat(boolean.get_columns()),
            }
        )
        .lazy()
        .select(
            sheet=pl.lit(sheet, dtype=pl.UInt32),
            line=(pl.int_range(pl.len()) % height).cast(pl.UInt32),
            position=(pl.int_range(pl.len()) // height + offset).cast(pl.UInt32),
            end=pl.lit(offset + len(columns), dtype=pl.UInt32),
            text="text",
            number="number",
            readable=pl.col("readable").is_not_null(),
        )
    )


def _classify(cells: pl.LazyFrame) -> pl.LazyFrame:
    t = pl.col("text")
    return cells.with_columns(
        kind=pl.when(t.is_null() | (t == ""))
        .then(EMPTY)
        .when(pl.col("readable") & t.is_in(["true", "false"]))
        .then(BOOLEAN)
        .when(pl.col("readable"))
        .then(NUMBER)
        .when(t.str.contains(DATETIME_TEXT) & t.str.starts_with(TIME_DATE))
        .then(TIME)
        .when(t.str.contains(DATETIME_TEXT))
        .then(DATE)
        .otherwise(TEXT)
        .cast(pl.UInt8),
        # Whole numbers are read as integers, so -0.0 becomes 0.
        number=pl.when(pl.col("number") == 0).then(0.0).otherwise(pl.col("number")),
    ).drop("readable")


def _lines(cells: pl.LazyFrame) -> pl.LazyFrame:
    """Cut comments and number the lines that pandas read as header and data.

    Text from the first ``#`` of a line is dropped with all later cells; ``length``
    counts the remaining cells. Lines that are only a comment are skipped while the
    header and the first two data lines are read; later ones remain as empty lines,
    as do blank lines. ``row`` 0 is the header line.
    """
    line = ["sheet", "line"]
    t = pl.col("text")
    comment = (
        (pl.col("kind") == TEXT)
        & t.str.contains(COMMENT, literal=True)
        & ~t.is_in(list(NA_STRINGS))
    )
    cells = cells.with_columns(
        cut=pl.when(comment).then(pl.col("position")).min().over(line)
    ).with_columns(
        text=pl.when(pl.col("position") == pl.col("cut"))
        .then(t.str.slice(0, t.str.find(COMMENT, literal=True)))
        .otherwise(t)
    )
    kept = ((pl.col("position") == pl.col("cut")) & (t != "")).any().over(line)
    cells = cells.with_columns(
        length=pl.when(pl.col("cut").is_null())
        .then(pl.col("end"))
        .otherwise(pl.col("cut") + kept.cast(pl.UInt32))
    ).drop("cut", "end")
    content = (pl.col("length") > 0).cast(pl.UInt32).cum_sum().over("sheet")
    third = (
        pl.when(content == 3)
        .then(pl.col("line"))
        .min()
        .over("sheet")
        .fill_null(pl.col("line").max().over("sheet"))
    )
    lines = (
        cells.group_by(line)
        .agg(pl.col("length").first())
        .sort(line)
        .filter(((pl.col("length") > 0) & (content <= 3)) | (pl.col("line") > third))
        .with_columns(row=pl.int_range(pl.len(), dtype=pl.UInt32).over("sheet"))
        .drop("length")
    )
    return cells.join(lines, on=line)


def _text(kind: int, text: str | None, number: float | None) -> str:
    """A cell's text as the earlier pandas tables wrote it in mixed columns."""
    if kind == EMPTY or text is None:
        return ""
    if kind == NUMBER and number is not None:
        return str(int(number)) if number.is_integer() else repr(number)
    if kind == BOOLEAN:
        return "True" if text == "true" else "False"
    if kind == TIME:
        return text.removeprefix(TIME_DATE)
    return text


def _names(cells: dict[int, dict], length: int) -> list[str]:
    header = [cells.get(position) for position in range(length)]
    dates = [cell["text"] for cell in header if cell and cell["kind"] == DATE]
    # Headers of dates only were written like a date column.
    midnight = len(dates) == length and all(d.endswith(" 00:00:00") for d in dates)
    names: list[str] = []
    counts: dict[str, int] = {}
    for position, cell in enumerate(header):
        name = _text(cell["kind"], cell["text"], cell["number"]) if cell else ""
        if midnight:
            name = name.removesuffix(" 00:00:00")
        name = name or f"Unnamed: {position}"
        count = counts.get(name, 0)
        while count:
            counts[name] = count + 1
            name = f"{name}.{count}"
            count = counts.get(name, 0)
        counts[name] = count + 1
        names.append(name)
    return names


def _columns(
    cells: pl.DataFrame, sheets: list[str]
) -> tuple[dict[int, list[tuple[int, str]]], list[int]]:
    """The named columns of each sheet with data, as ``(position, name)`` pairs.

    Also returns the sheets whose first data line names the index columns.
    """
    header = cells.filter(pl.col("row") == 0)
    lines = (
        cells.filter(pl.col("row") > 0)
        .select("sheet", "row", "line", "length")
        .unique()
        .sort("sheet", "row")
        .group_by("sheet", maintain_order=True)
        .agg(
            first=pl.col("length").first(),
            second=pl.col("length").slice(1, 1).first(),
            lengths=pl.col("length"),
            lines=pl.col("line"),
        )
    )
    headers: dict[int, dict[int, dict]] = {}
    lengths: dict[int, int] = {}
    for cell in header.iter_rows(named=True):
        headers.setdefault(cell["sheet"], {})[cell["position"]] = cell
        lengths[cell["sheet"]] = cell["length"]
    columns = {}
    index_names = []
    for sheet, first, second, line_lengths, line_numbers in lines.iter_rows():
        names = _names(headers[sheet], lengths[sheet])
        # As in pandas, extra leading cells in the first data line form an index.
        implicit = max(0, first - len(names))
        data = list(zip(line_numbers, line_lengths))
        if second is not None and second == first + len(names):
            # ... unless the second line is longer by the header: then the first
            # line holds the index names and is no data.
            implicit, data = first, data[1:]
            index_names.append(sheet)
        expected = len(names) + implicit
        for line, length in data:
            if length > expected:
                # Lines count from the sheet row after the description row.
                raise WorkbookError(
                    f"Sheet {sheets[sheet]} row {line + 2} has {length} fields, "
                    f"but its header has {expected}"
                )
        columns[sheet] = [
            (index + implicit, name)
            for index, name in enumerate(names)
            if "Unnamed:" not in name
        ]
    return columns, index_names


def _modes(cells: pl.LazyFrame) -> pl.LazyFrame:
    """Decide per column how values are written, as pandas inferred column types."""
    kind, text, missing = pl.col("kind"), pl.col("text"), pl.col("missing")
    present = ~missing
    numeric_text = (kind == TEXT) & text.str.contains(NUMBER_TEXT)
    integral = (
        (kind == BOOLEAN)
        | ((kind == NUMBER) & (pl.col("number") == pl.col("number").floor()))
        | ((kind == TEXT) & text.str.contains(INTEGER_TEXT))
    )
    boolean = (kind == BOOLEAN) | ((kind == TEXT) & text.is_in(list(BOOLEAN_STRINGS)))
    stamp = pl.col("stamp")
    complete = present.all()
    # Booleans alone are numeric (1.0 and 0.0) only together with missing values.
    numeric = (
        (present & ((kind == NUMBER) | numeric_text)).any()
        | ((present & (kind == BOOLEAN)).any() & ~complete)
    ) & (missing | (kind == NUMBER) | (kind == BOOLEAN) | numeric_text).all()
    mode = (
        pl.when(numeric & complete & (missing | integral).all())
        .then(INTEGERS)
        .when(numeric)
        .then(FLOATS)
        # pandas converted boolean text unless the column started with a boolean.
        .when(
            (present & boolean).any()
            & (missing | boolean).all()
            & ~(present & (kind == BOOLEAN)).sort_by("row").first()
        )
        .then(BOOLEANS)
        .when((present & (kind == DATE)).any() & (missing | (kind == DATE)).all())
        .then(DATES)
        .otherwise(CELLS)
    )
    date_format = (
        pl.when(~(present & (stamp.dt.time() != pl.time(0))).any())
        .then(0)
        .when((present & (stamp.dt.microsecond() % 1000 != 0)).any())
        .then(3)
        .when((present & (stamp.dt.microsecond() != 0)).any())
        .then(2)
        .otherwise(1)
    )
    return cells.group_by("sheet", "position").agg(
        mode=mode.cast(pl.UInt8), date_format=date_format.cast(pl.UInt8)
    )


def _values(cells: pl.DataFrame) -> pl.Series:
    """Format every cell by its column's mode; missing cells become null."""
    kind, text, mode, number = (
        pl.col("kind"),
        pl.col("text"),
        pl.col("mode"),
        pl.col("number"),
    )
    stamp = pl.col("stamp")
    stripped = text.str.strip_chars(ASCII_WHITESPACE)
    true = ((kind == BOOLEAN) & (text == "true")) | text.is_in(
        list(BOOLEAN_STRINGS[:3])
    )
    as_bool = pl.when(true).then(pl.lit("True")).otherwise(pl.lit("False"))
    as_number = (
        pl.when(kind == BOOLEAN)
        .then(true.cast(pl.Float64))
        .when(kind == TEXT)
        .then(stripped.cast(pl.Float64, strict=False))
        .otherwise(number)
    )
    as_integer = (
        pl.when(kind == TEXT)
        .then(stripped.cast(pl.Int64, strict=False))
        .otherwise(as_number.cast(pl.Int64, strict=False))
        .cast(pl.String)
    )
    whole = (kind == NUMBER) & (number == number.floor())
    seconds = "%Y-%m-%d %H:%M:%S"
    as_date = (
        pl.when(pl.col("date_format") == 0)
        .then(stamp.dt.strftime("%Y-%m-%d"))
        .when(pl.col("date_format") == 1)
        .then(stamp.dt.strftime(seconds))
        .when(pl.col("date_format") == 2)
        .then(stamp.dt.strftime(seconds + "%.3f"))
        .otherwise(stamp.dt.strftime(seconds + "%.6f"))
    )
    fraction = stamp.dt.microsecond() != 0
    as_cell = (
        pl.when(kind == TEXT)
        .then(text)
        .when(kind == BOOLEAN)
        .then(as_bool)
        .when(whole)
        .then(number.cast(pl.Int64, strict=False).cast(pl.String))
        .when(kind == NUMBER)
        .then(number.cast(pl.String))
        .when(kind == DATE)
        .then(
            pl.when(fraction)
            .then(stamp.dt.strftime(seconds + "%.6f"))
            .otherwise(stamp.dt.strftime(seconds))
        )
        .otherwise(
            pl.when(fraction)
            .then(stamp.dt.strftime("%H:%M:%S%.6f"))
            .otherwise(stamp.dt.strftime("%H:%M:%S"))
        )
    )
    floats = (mode == FLOATS) | ((mode == CELLS) & (kind == NUMBER) & ~whole)
    integers = (mode == INTEGERS) | ((mode == CELLS) & whole)
    magnitude = as_number.abs()
    frame = cells.select(
        value=pl.when(pl.col("missing"))
        .then(None)
        .when(mode == INTEGERS)
        .then(as_integer)
        .when(mode == FLOATS)
        .then(as_number.cast(pl.String))
        .when(mode == BOOLEANS)
        .then(as_bool)
        .when(mode == DATES)
        .then(as_date)
        .otherwise(as_cell),
        # Python formats these: floats outside polars' matching range and integers
        # beyond 64 bits.
        python_float=~pl.col("missing")
        & floats
        & (magnitude > 0)
        & ((magnitude < POSITIONAL[0]) | (magnitude >= POSITIONAL[1]))
        & as_number.is_finite(),
        python_integer=~pl.col("missing")
        & integers
        & as_integer.is_null()
        & ((kind != TEXT) | (mode == INTEGERS)),
        number=as_number,
        source=pl.when(kind == TEXT).then(stripped),
    )
    values = frame["value"]
    for mask, convert in (
        ("python_float", lambda number, source: repr(number)),
        ("python_integer", lambda number, source: str(int(source or number))),
    ):
        if frame[mask].any():
            rows = frame.filter(mask)
            values = values.scatter(
                frame[mask].arg_true(),
                [convert(*row) for row in rows.select("number", "source").iter_rows()],
            )
    return values


def _quote(value: str) -> str:
    """Quote a field as Python's csv module does with minimal quoting."""
    if any(character in value for character in '\t"\n\r'):
        return '"' + value.replace('"', '""') + '"'
    return value


def _quoted(value: pl.Expr) -> pl.Expr:
    """Quote fields as :func:`_quote` does."""
    return (
        pl.when(value.str.contains(r'[\t"\n\r]'))
        .then(
            pl.lit('"') + value.str.replace_all('"', '""', literal=True) + pl.lit('"')
        )
        .otherwise(value)
    )


def _tables(workbook: Path) -> dict[str, str]:
    try:
        reader = fastexcel.read_excel(workbook)
        names = [name for name in reader.sheet_names if name.startswith(SHEET_PREFIXES)]
        sheets = [_sheet(reader, name, index) for index, name in enumerate(names)]
    except Exception as error:
        raise WorkbookError(f"Cannot read {workbook.name}: {error}") from error
    if not (sheets := [sheet for sheet in sheets if sheet is not None]):
        return {}
    cells = _lines(_classify(pl.concat(sheets))).collect()
    columns, index_names = _columns(cells, names)
    if index_names:
        cells = cells.filter(
            ~(pl.col("sheet").is_in(index_names) & (pl.col("row") == 1))
        )
    kept = pl.DataFrame(
        [
            (sheet, position, order)
            for sheet, named in columns.items()
            for order, (position, _) in enumerate(named)
        ],
        schema={"sheet": pl.UInt32, "position": pl.UInt32, "order": pl.UInt32},
        orient="row",
    )
    data = (
        cells.lazy()
        .filter(pl.col("row") > 0)
        .join(kept.lazy(), on=["sheet", "position"])
        .with_columns(
            missing=(pl.col("position") >= pl.col("length"))
            | (pl.col("kind") == EMPTY)
            | ((pl.col("kind") == TEXT) & pl.col("text").is_in(list(NA_STRINGS))),
            stamp=pl.col("text").str.to_datetime(
                "%Y-%m-%d %H:%M:%S%.f", time_unit="us", strict=False
            ),
        )
    )
    data = data.join(_modes(data), on=["sheet", "position"]).collect()
    data = data.with_columns(value=_values(data))
    # pandas reused the first of equal values in mixed columns, where False == 0
    # and True == 1, so the first of them sets how all of them are written.
    kind, number = pl.col("kind"), pl.col("number")
    equal = pl.when(
        ~pl.col("missing")
        & (pl.col("mode") == CELLS)
        & ((kind == BOOLEAN) | ((kind == NUMBER) & number.is_in([0.0, 1.0])))
    ).then(
        pl.when(kind == BOOLEAN).then(pl.col("text") == "true").otherwise(number == 1)
    )
    data = data.with_columns(equal=equal).with_columns(
        value=pl.when(pl.col("equal").is_not_null())
        .then(pl.col("value").sort_by("row").first().over("sheet", "position", "equal"))
        .otherwise(pl.col("value"))
    )
    body = (
        data.lazy()
        # Lines without any value in the named columns are dropped.
        .filter(pl.col("value").is_not_null().any().over("sheet", "row"))
        .sort("sheet", "row", "order")
        .group_by("sheet", "row", maintain_order=True)
        .agg(_quoted(pl.col("value").fill_null("NA")).str.join("\t").alias("value"))
        .group_by("sheet", maintain_order=True)
        .agg(pl.col("value").str.join("\n"))
        .collect()
    )
    lines = dict(body.iter_rows())
    tables = {}
    for sheet, named in columns.items():
        text = "\t".join(_quote(name) for _, name in named) + "\n"
        if sheet in lines:
            text += lines[sheet] + "\n"
        tables[f".{workbook.stem}_{names[sheet]}.tsv"] = text
    return tables


def _write(path: Path, text: str) -> None:
    # The temporary name is ignored by source scanning, so watchers never see it.
    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        prefix=".",
        suffix=".swp",
        delete=False,
    ) as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    Path(handle.name).replace(path)


def sync_tsvs(folder: str | Path) -> str | None:
    """Write changed TSV tables and remove orphaned ones; describe the change.

    Study format 2 folders are left alone: their tables are the TSV files, and
    their workbook is a generated working copy.
    """
    folder = Path(folder)
    workbook = folder / f"{folder.name}.xlsx"
    if not workbook.is_file() or workbook.is_symlink() or is_v2_folder(folder):
        return None
    tables = _tables(workbook)
    study = folder / "study.json"
    referenced = study.read_text(encoding="utf-8") if study.is_file() else ""
    created = updated = removed = 0
    for name, text in tables.items():
        path = folder / name
        if path.is_file() and path.read_bytes() == text.encode("utf-8"):
            continue
        exists = path.exists()
        _write(path, text)
        updated += exists
        created += not exists
    prefix = f".{folder.name}_"
    for path in folder.glob(f"{escape(prefix)}*.tsv"):
        # A table study.json still uses (by file or sheet name) may be the last copy
        # of a deleted sheet; keep it so validation reports the missing sheet.
        sheet = path.name.removeprefix(prefix).removesuffix(".tsv")
        used = f'"{path.name}"' in referenced or f'"{sheet}"' in referenced
        if path.name not in tables and not used:
            path.unlink()
            removed += 1
    parts = [
        f"{verb} {count}"
        for verb, count in (
            ("created", created),
            ("updated", updated),
            ("removed", removed),
        )
        if count
    ]
    if not parts:
        return None
    joined = parts[0] if len(parts) == 1 else f"{', '.join(parts[:-1])} and {parts[-1]}"
    return f"{joined[0].upper()}{joined[1:]} TSV files from {workbook.name}"
