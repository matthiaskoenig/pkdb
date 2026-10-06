"""Study format 2 folders as curators write them, and the parts the client uploads."""

from pathlib import Path

from pkdb.studyformat.formatter import format_folder
from pkdb.studyformat.jsonio import dump_json
from pkdb.studyformat.tables import TABLES
from pkdb.studyformat.text import render_tsv

JSON_FILES = ("study.json", "reference.json")


def tsv(kind, *rows):
    names = TABLES[kind].names
    return render_tsv(
        names, [tuple(row.get(name, "") for name in names) for row in rows]
    )


def write_study(root: Path, name="Example", *, pmid="123", release=None) -> Path:
    """A formatted study format 2 folder at <root>/caffeine/<name>."""
    folder = root / "caffeine" / name
    folder.mkdir(parents=True)
    study = {
        "format": 2,
        "reference": {"pmid": pmid},
        "creator": "curator",
        "curators": [{"user": "curator", "rating": 3}],
        "licence": "closed",
        "access": "private",
        "issue": 2158,
        "descriptions": ["Plasma levels in µg/l."],
    }
    if release:
        study["release"] = {"pkdb_id": release, "date": "2026-09-28"}
    files = {
        "study.json": dump_json(study),
        "reference.json": dump_json(
            {"sid": pmid, "name": name, "pmid": pmid, "title": "Example study"}
        ),
        "review.json": dump_json(
            {
                "status": "in_review",
                "reviewers": ["curator"],
                "items": [
                    {
                        "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2AB",
                        "kind": "question",
                        "target": {"file": "outputs_Tab2.tsv", "column": "mean"},
                        "text": "Is the mean read from the table?",
                        "author": "curator",
                        "created": "2026-10-05T10:12:00Z",
                    }
                ],
            }
        ),
        "subjects.tsv": tsv(
            "subjects", {"name": "all", "count": "4", "source": "Tab1"}
        ),
        "interventions.tsv": tsv(
            "interventions",
            {
                "source": "Text",
                "name": "D1",
                "measurement": "dosing",
                "substance": "drug",
                "route": "oral",
                "form": "tablet",
                "application": "single dose",
                "time": "0",
                "time_unit": "h",
                "mean": "10",
                "unit": "mg",
            },
        ),
        "characteristica.tsv": tsv(
            "characteristica",
            *(
                {"source": "Tab1", "subjects": "all", "measurement": m, "choice": c}
                for m, c in (
                    ("species", "Homo sapiens"),
                    ("sex", "NR"),
                    ("healthy", "Y"),
                )
            ),
        ),
        "outputs_Tab2.tsv": tsv(
            "outputs",
            {
                "subjects": "all",
                "interventions": "D1",
                "measurement": "concentration",
                "substance": "drug",
                "tissue": "plasma",
                "time": "1",
                "time_unit": "h",
                "mean": "2",
                "unit": "mg/l",
            },
        ),
    }
    for file, text in files.items():
        (folder / file).write_text(text, encoding="utf-8", newline="")
    (folder / f"{name}.pdf").write_bytes(b"%PDF-1.4 example")
    (folder / f"{name}_Tab1.png").write_bytes(b"png 1")
    (folder / f"{name}_Tab2.png").write_bytes(b"png 2")
    assert format_folder(folder).ok
    return folder


def multipart(
    folder: Path,
    files: dict[str, bytes] | None = None,
    *,
    json_files: dict[str, bytes] | None = None,
):
    """The parts the client sends: study.json and reference.json as files with
    their exact bytes, and every other study file.

    `files` replaces or adds file parts, `json_files` replaces JSON files.
    """
    contents = {path.name: path.read_bytes() for path in sorted(folder.iterdir())}
    contents |= json_files or {}
    attachments = {
        name: content for name, content in contents.items() if name not in JSON_FILES
    } | (files or {})
    return {
        "files": [
            *(
                (part, (file, contents[file], "application/json"))
                for part, file in zip(("study", "reference"), JSON_FILES, strict=True)
            ),
            *(
                ("files", (name, content, "application/octet-stream"))
                for name, content in attachments.items()
            ),
        ]
    }
