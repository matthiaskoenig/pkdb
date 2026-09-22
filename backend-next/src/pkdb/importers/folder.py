"""Expand an unchanged PK-DB study bundle into canonical scientific records."""

import hashlib
import json
import math
from copy import deepcopy
from pathlib import Path

from pydantic import ValidationError

from pkdb.importers.expressions import (
    bind_columns,
    clean,
    external_aliases,
    split_entry,
)
from pkdb.importers.structure import entry_structure, list_value, validate_json_tree
from pkdb.importers.workbook import read_table
from pkdb.schemas.source import SourceBundle, SourceLocation
from pkdb.schemas.study import CanonicalStudy, Statistics
from pkdb.schemas.validation import (
    StudyValidationError,
    ValidationIssue,
    ValidationReport,
    fail,
)

SECTIONS = {
    "groupset": "groups",
    "individualset": "individuals",
    "interventionset": "interventions",
    "outputset": "outputs",
    "dataset": "data",
}
META_KEYS = {
    "name",
    "date",
    "creator",
    "curators",
    "collaborators",
    "licence",
    "access",
    "descriptions",
    "comments",
}


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(
            path.read_text(),
            object_pairs_hook=_unique_object,
            parse_constant=lambda value: fail("invalid_number", value),
        )
    except (ValueError, OSError, RecursionError) as error:
        fail("invalid_json", str(error), SourceLocation(file=path.name))
    if not isinstance(value, dict):
        fail("invalid_json", "Expected a JSON object", SourceLocation(file=path.name))
    return value


def load_folder(path: Path) -> SourceBundle:
    root = path.resolve(strict=True)
    files = {}
    for file in sorted(root.rglob("*")):
        if file.is_symlink():
            fail("symlink", f"Symlinks are not accepted: {file.name}")
        if file.is_file() and file.name not in {"study.json", "reference.json"}:
            if file.name in files:
                fail("duplicate_file", f"Duplicate file basename: {file.name}")
            files[file.name] = file
    study = _read_json(root / "study.json")
    if study.get("name") != root.name:
        fail("study_name", "Study name must match its folder")
    return SourceBundle(
        study=study, reference=_read_json(root / "reference.json"), files=files
    )


def _notes(data: dict) -> dict:
    if not isinstance(data, dict):
        fail("invalid_entry", "Notes must belong to an object")
    result = deepcopy(data)
    for key in ("comments", "descriptions"):
        if key in result:
            result[key] = [
                {"text": item}
                if isinstance(item, str)
                else (
                    {"user": item[0], "text": item[1]}
                    if key == "comments" and isinstance(item, list) and len(item) == 2
                    else item
                )
                for item in list_value(result[key], key)
            ]
    return result


def _numeric(value, *, integer=False):
    value = clean(value)
    if value is None:
        return None
    if isinstance(value, bool):
        fail("invalid_number", "Boolean values are not scientific numbers")
    try:
        number = float(value)
    except (ValueError, TypeError):
        fail("invalid_number", f"Not a numeric value: {value!r}")
    if not math.isfinite(number):
        fail("invalid_number", "Scientific numbers must be finite")
    if integer:
        if not number.is_integer():
            fail("invalid_count", "Counts must be whole numbers")
        return int(number)
    return number


def _scientific(data: dict, key: str, source: SourceLocation) -> dict:
    reserved = data.keys() & {
        "origin",
        "derived_from",
        "calculated",
        "key",
        "statistics",
        "series_key",
        "time_not_reported",
        "time_unit_not_reported",
    }
    if reserved:
        fail(
            "reserved_field",
            f"Server-generated fields cannot be uploaded: {sorted(reserved)}",
            source,
        )
    result = _notes(data)
    stats = {
        name: _numeric(result.pop(name), integer=name == "count")
        for name in Statistics.model_fields
        if name in result
    }
    result.update(key=key, statistics=stats, source=source)
    return result


def parse_bundle(bundle: SourceBundle, *, max_rows: int = 1_000_000) -> CanonicalStudy:
    if max_rows <= 0:
        fail("row_limit", "Row limit must be positive")
    validate_json_tree(bundle.study, "study.json")
    validate_json_tree(bundle.reference, "reference.json")
    data = external_aliases(bundle.study)
    unexpected = (
        data.keys() - META_KEYS - SECTIONS.keys() - {"sid", "reference", "files"}
    )
    if unexpected:
        fail("unknown_field", f"Unknown study fields: {sorted(unexpected)}")
    reference = deepcopy(bundle.reference)
    if type(data.get("sid")) not in (str, int) or isinstance(data.get("sid"), bool):
        fail("invalid_identity", "Study SID must be a string or integer")
    for name in ("sid", "pmid"):
        if reference.get(name) is not None:
            if type(reference[name]) not in (str, int):
                fail(
                    "invalid_identity",
                    f"Reference {name} must be text or integer",
                    SourceLocation(file="reference.json", path=(name,)),
                )
            reference[name] = str(reference[name])
    if str(data.get("reference")) != reference.get("sid"):
        fail("reference_mismatch", "Study reference must match reference.json SID")
    metadata = _notes({key: value for key, value in data.items() if key in META_KEYS})
    entry_structure(metadata, SourceLocation(file="study.json"))
    curators = []
    for value in list_value(
        metadata.get("curators"),
        "curators",
        SourceLocation(file="study.json", path=("curators",)),
    ):
        if isinstance(value, str):
            curators.append({"user": value, "rating": 0})
        elif isinstance(value, list) and len(value) == 2:
            curators.append({"user": value[0], "rating": value[1]})
        elif isinstance(value, dict):
            curators.append(value)
        else:
            fail("invalid_curator", "Expected a username or [username, rating]")
    metadata["curators"] = curators
    metadata["collaborators"] = list_value(
        metadata.get("collaborators"),
        "collaborators",
        SourceLocation(file="study.json", path=("collaborators",)),
    )
    result = {
        "sid": str(data["sid"]),
        "metadata": metadata,
        "reference": reference,
        "groups": [],
        "individuals": [],
        "interventions": [],
        "measurements": [],
        "scatters": [],
        "section_notes": {},
        "attachments": [],
    }
    records: dict[str, list[dict]] = {
        key: []
        for key in (
            "groups",
            "individuals",
            "interventions",
            "measurements",
            "scatters",
        )
    }
    result.update(records)
    tables = {}
    expanded = 0
    digest = hashlib.sha256(
        json.dumps(
            {"study": bundle.study, "reference": reference},
            sort_keys=True,
            allow_nan=False,
        ).encode()
    )
    for name, file in sorted(bundle.files.items()):
        if file.is_symlink():
            fail("symlink", "Symlink attachments are not accepted")
        if Path(name).name != name or name in {".", ".."}:
            fail("invalid_filename", "Attachment names must be basenames")
        file_digest = hashlib.sha256()
        with file.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                file_digest.update(chunk)
        result["attachments"].append(
            {
                "name": name,
                "size": file.stat().st_size,
                "sha256": file_digest.hexdigest(),
            }
        )
        digest.update(name.encode())
        digest.update(file_digest.digest())
    result["source_digest"] = digest.hexdigest()

    def table(source):
        if not isinstance(source, str):
            fail("invalid_source", "Source must identify a workbook sheet or TSV")
        if source not in tables:
            study_name = metadata["name"]
            filename = (
                source if source.endswith(".tsv") else f".{study_name}_{source}.tsv"
            )
            if f"{study_name}.xlsx" in bundle.files and not source.endswith(".tsv"):
                tables[source] = read_table(
                    bundle.files[f"{study_name}.xlsx"], source, max_rows
                )
            elif filename in bundle.files:
                tables[source] = read_table(bundle.files[filename], None, max_rows)
            else:
                fail("unknown_source", f"No source file for {source}")
        return tables[source]

    def image_name(value):
        if not value:
            return None
        name = value if Path(value).suffix else f"{metadata['name']}_{value}.png"
        if name not in bundle.files:
            fail("unknown_image", f"No image file for {value}")
        return name

    for section, entity in SECTIONS.items():
        content = data.get(section)
        if content is None:
            content = {}
        if not isinstance(content, dict):
            fail("invalid_section", f"{section} must be an object")
        unknown = content.keys() - {entity, "comments", "descriptions"}
        if unknown:
            fail("unknown_field", f"Unknown {section} fields: {sorted(unknown)}")
        result["section_notes"][section] = _notes(
            {k: v for k, v in content.items() if k != entity}
        )
        destination = {"outputs": "measurements", "data": "scatters"}.get(
            entity, entity
        )
        templates = list_value(
            content.get(entity),
            entity,
            SourceLocation(file="study.json", path=(section, entity)),
        )
        for template_index, raw in enumerate(templates):
            entry_structure(
                raw,
                SourceLocation(
                    file="study.json", path=(section, entity, template_index)
                ),
            )
            for split_index, template in enumerate(split_entry(raw)):
                source = template.pop("source", None)
                subset = template.pop("subset", None)
                template.pop("figure", None)
                rows = (
                    table(source)
                    if source
                    else [
                        (
                            {},
                            SourceLocation(
                                file="study.json",
                                path=(section, entity, template_index),
                            ),
                        )
                    ]
                )
                grouped = {}
                for row, location in rows:
                    if subset:
                        keep = True
                        for predicate in subset.split("&"):
                            parts = [x.strip() for x in predicate.split("==")]
                            if len(parts) != 2 or parts[0] not in row:
                                fail(
                                    "invalid_subset",
                                    f"Invalid subset: {subset}",
                                    location,
                                )
                            actual = row[parts[0]]
                            expected = parts[1]
                            if isinstance(actual, (float, int)):
                                try:
                                    expected = float(expected)
                                except ValueError:
                                    pass
                            keep = keep and actual == expected
                        if not keep:
                            continue
                    bound = bind_columns(template, row, location)
                    entry_structure(bound, location)
                    for entry in split_entry(bound):
                        expanded += 1
                        if expanded > max_rows:
                            fail(
                                "row_limit",
                                "Expanded study exceeds configured row limit",
                            )
                        if entity in {"groups", "individuals"}:
                            name = entry.get("name")
                            if name in grouped and source:
                                grouped[name][0].setdefault(
                                    "characteristica", []
                                ).extend(entry.get("characteristica", []))
                            else:
                                if name in grouped:
                                    fail(
                                        "duplicate_name",
                                        f"Duplicate subject: {name}",
                                        location,
                                    )
                                grouped[name] = (entry, location)
                        elif entity == "data" and source:
                            name = entry.get("name")
                            if name in grouped:
                                existing = grouped[name][0]
                                if {
                                    key: value
                                    for key, value in existing.items()
                                    if key != "subsets"
                                } != {
                                    key: value
                                    for key, value in entry.items()
                                    if key != "subsets"
                                }:
                                    fail(
                                        "dataset_metadata",
                                        "Mapped dataset rows contain inconsistent metadata",
                                        location,
                                    )
                                existing.setdefault("subsets", []).extend(
                                    entry.get("subsets", [])
                                )
                            else:
                                grouped[name] = (entry, location)
                        else:
                            grouped[len(grouped)] = (entry, location)
                if subset and not grouped:
                    fail("empty_subset", f"Subset matches no records: {subset}")
                for entry, location in grouped.values():
                    key = f"{entity}:{len(records[destination])}"
                    entry = _notes(entry)
                    if entity in {"groups", "individuals"}:
                        entry["key"] = str(entry.get("name", ""))
                        entry["source"] = location
                        if "count" in entry:
                            entry["count"] = _numeric(entry["count"], integer=True)
                        entry["characteristica"] = [
                            _scientific(c, f"{key}:characteristic:{i}", location)
                            for i, c in enumerate(
                                [
                                    part
                                    for original in (entry.get("characteristica") or [])
                                    for part in split_entry(original)
                                ]
                            )
                        ]
                    elif entity in {"interventions", "outputs"}:
                        entry = _scientific(
                            entry, str(entry.get("name", key)), location
                        )
                        if entity == "outputs":
                            for field in ("time", "time_unit"):
                                if entry.get(field) == "NR":
                                    entry[field] = None
                                    entry[f"{field}_not_reported"] = True
                        for field in ("time", "time_end"):
                            if field in entry and (
                                entity == "outputs"
                                or not isinstance(entry[field], str)
                                or "|" not in entry[field]
                                and not entry[field].startswith("S")
                            ):
                                entry[field] = _numeric(entry[field])
                        if entity == "outputs":
                            entry["series_key"] = (
                                f"outputs:{template_index}:{split_index}"
                            )
                            entry["interventions"] = entry.get("interventions") or []
                            if isinstance(entry["interventions"], str):
                                entry["interventions"] = [
                                    v.strip() for v in entry["interventions"].split(",")
                                ]
                    else:
                        entry["key"] = key
                        entry["source"] = location
                        if entry.get("data_type") == "timecourse":
                            fail(
                                "explicit_timecourse",
                                "Timecourses are generated from labeled timecourse outputs",
                                location,
                            )
                        entry["subsets"] = [
                            _notes(value) for value in entry.get("subsets", [])
                        ]
                        for subset_entry in entry["subsets"]:
                            if "points" in subset_entry:
                                fail(
                                    "reserved_field",
                                    "Dataset points are server-generated",
                                    location,
                                )
                            for field in ("dimensions", "shared"):
                                value = subset_entry.get(field, [])
                                if isinstance(value, str):
                                    value = [
                                        item.strip()
                                        for item in value.split(",")
                                        if item.strip()
                                    ]
                                if field == "dimensions" and isinstance(value, list):
                                    value = [
                                        {"dimension": str(index), "output": item}
                                        if isinstance(item, str)
                                        else item
                                        for index, item in enumerate(value)
                                    ]
                                subset_entry[field] = value
                    if "image" in entry:
                        entry["image"] = image_name(entry["image"])
                    records[destination].append(entry)
    try:
        return CanonicalStudy.model_validate(result)
    except ValidationError as error:
        issues = []
        for item in error.errors()[:100]:
            issues.append(
                ValidationIssue(
                    code=item["type"],
                    message=item["msg"],
                    source=SourceLocation(file="study.json", path=item["loc"]),
                )
            )
        raise StudyValidationError(
            ValidationReport(
                issues=issues,
                truncated=error.error_count() > 100,
                error_count=error.error_count(),
            )
        ) from error
