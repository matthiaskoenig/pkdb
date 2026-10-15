"""Artificial studies shared by browser and API contract tests.

`FRONTEND_SCOPE` is a public study format 1 study. `drug/Format2Fixture` is a
study format 2 study that stays private to its curators. The browser fixture adds
`drug/Format2Public`, a public copy with the study pages of the website (#963),
which the anonymous search sees as a second study, and `drug/Format2Legacy`,
which it keeps without stored views, as a study uploaded before those pages, so
that it shows on the record page.
"""

from pathlib import Path

from pkdb.schemas.source import SourceBundle

FORMAT2_SID = "drug/Format2Fixture"
FORMAT2_PKDB_ID = "PKDB09901"
FORMAT2_ISSUE = 2158
FORMAT2_PMID = "99001"
#: A public study format 2 study with the study pages of the website (#963), which visitors read.
FORMAT2_PUBLIC_SID = "drug/Format2Public"
FORMAT2_PUBLIC_PKDB_ID = "PKDB09903"
FORMAT2_PUBLIC_ISSUE = 2160
FORMAT2_PUBLIC_PMID = "99003"
#: A second study format 2 study, which the browser fixture keeps as uploaded before the study
#: pages of the website (#963): without stored views, so it shows on the record page.
FORMAT2_LEGACY_SID = "drug/Format2Legacy"
FORMAT2_LEGACY_PKDB_ID = "PKDB09902"
FORMAT2_LEGACY_ISSUE = 2159
FORMAT2_LEGACY_PMID = "99002"
#: The width and height of the image of each source of a format 2 fixture study.
FORMAT2_IMAGES = {"Tab1": (240, 120), "Tab2": (320, 160), "Fig1": (400, 300)}


def fixture_pdf(text: str) -> bytes:
    """A one-page PDF that shows `text` in Helvetica, the same bytes on every call."""
    stream = f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    return bytes(out)


def fixture_png(size: tuple[int, int]) -> bytes:
    """A PNG image of `size` in a light teal with a darker frame, the same bytes on every call."""
    from io import BytesIO

    from PIL import Image, ImageDraw

    image = Image.new("RGB", size, (236, 243, 244))
    ImageDraw.Draw(image).rectangle(
        (0, 0, size[0] - 1, size[1] - 1), outline=(23, 107, 112), width=2
    )
    buffer = BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def forget_views(session, sid: str) -> None:
    """Make `sid` a study uploaded before the study pages of the website (#963): without stored
    views and without the texts of its JSON files."""
    from sqlalchemy import delete, select, update

    from pkdb_server.db.models.studies import Study
    from pkdb_server.db.models.views import StudyView

    study_id = session.scalar(select(Study.id).where(Study.sid == sid))
    session.execute(delete(StudyView).where(StudyView.study_id == study_id))
    session.execute(
        update(Study)
        .where(Study.id == study_id)
        .values(study_json=None, reference_json=None)
    )


def frontend_search_bundle(*, related=False, sid="FRONTEND_SCOPE"):
    outputs = [
        dict(
            group="all",
            interventions=["oral-A"],
            measurement_type="concentration",
            substance="drug",
            mean=0.0,
            unit="mg/l",
            time=0.0,
            time_unit="h",
            tissue="plasma",
        ),
        dict(
            group="all",
            interventions=["iv-B"],
            measurement_type="concentration",
            substance="drug-b",
            mean=2.125,
            unit="mg/l",
            time=1.0,
            time_unit="h",
            tissue="plasma",
        ),
    ]
    if related:
        outputs.append(dict(outputs[1], interventions=["oral-A", "iv-B"], mean=3.25))
    return SourceBundle(
        study={
            "sid": sid,
            "name": "Frontend scientific scope fixture",
            "creator": "curator",
            "curators": [{"user": "curator"}],
            "reference": "FRONTEND_REF",
            "access": "private",
            "licence": "open",
            "groupset": {
                "groups": [
                    {
                        "name": "all",
                        "count": 4,
                        "characteristica": [
                            {"measurement_type": "species", "choice": "homo sapiens"},
                            {"measurement_type": "sex", "choice": "NR"},
                            {"measurement_type": "healthy", "choice": "Y"},
                        ],
                    }
                ]
            },
            "interventionset": {
                "interventions": [
                    dict(
                        name=name,
                        measurement_type="dosing",
                        substance=substance,
                        value=10.0,
                        unit="mg",
                        time=0.0,
                        time_unit="h",
                        route=route,
                        form="tablet",
                        application="single dose",
                    )
                    for name, substance, route in [
                        ("oral-A", "drug", "oral"),
                        ("iv-B", "drug-b", "iv"),
                    ]
                ]
            },
            "outputset": {"outputs": outputs},
        },
        reference={
            "sid": "FRONTEND_REF",
            "name": "Artificial frontend verification reference",
        },
    )


def add_frontend_vocabulary(session):
    from sqlalchemy import select

    from pkdb_server.db.models.vocabulary import VocabularyNode

    # The complete vocabulary has this application; the controlled one lacks it.
    if (
        session.scalar(
            select(VocabularyNode).where(
                VocabularyNode.kind == "application",
                VocabularyNode.name == "multiple dose",
            )
        )
        is None
    ):
        session.add(
            VocabularyNode(
                sid="multiple-dose",
                name="multiple dose",
                kind="application",
                definition={},
            )
        )

    for sid, kind, definition in [
        ("drug-b", "substance", {"mass": 500.0}),
        ("drug", "substance", {"mass": 500.0}),
        ("iv", "route", {}),
    ]:
        if session.get(VocabularyNode, sid) is None:
            session.add(
                VocabularyNode(sid=sid, name=sid, kind=kind, definition=definition)
            )


def publish_frontend_fixture(session):
    from sqlalchemy import update

    from pkdb_server.db.models.studies import Study

    session.execute(
        update(Study).where(Study.sid == "FRONTEND_SCOPE").values(access="public")
    )


def add_frontend_plot_context(session):
    """Relate both existing normalized points; one may be outside a selection."""
    from sqlalchemy import func, select

    from pkdb_server.db.models.measurements import (
        Measurement,
        Scatter,
        Subset,
    )
    from pkdb_server.db.models.studies import Study

    study = session.scalar(select(Study).where(Study.sid == "FRONTEND_SCOPE"))
    points = list(
        session.scalars(
            select(Measurement)
            .where(Measurement.study_id == study.id, Measurement.origin == "normalized")
            .order_by(Measurement.time)
        )
    )
    for kind, width in [("timecourse", 1), ("scatter", 2)]:
        chart = Scatter(
            study_id=study.id,
            key=f"chart-{kind}",
            name=f"Fixture {kind}",
            data_type=kind,
        )
        session.add(chart)
        session.flush()
        subset = Subset(
            study_id=study.id,
            key=f"subset-{kind}",
            scatter_id=chart.id,
            name=f"Fixture {kind}",
            position=0,
            dimension_labels=["Y"] if width == 1 else ["X", "Y"],
        )
        session.add(subset)
        session.flush()
        subset.measurement_ids = [point.id for point in points]
        subset.point_ids = list(
            session.scalars(
                select(func.nextval("dataset_row_id_seq")).select_from(
                    func.generate_series(1, len(points) // width)
                )
            )
        )
        session.flush()


def write_frontend_format2_study(
    root: Path,
    sid: str = FORMAT2_SID,
    *,
    pkdb_id: str = FORMAT2_PKDB_ID,
    issue: int = FORMAT2_ISSUE,
    pmid: str = FORMAT2_PMID,
    access: str = "private",
) -> Path:
    """The study format 2 folder `sid`, formatted as curators keep it.

    It is released as `pkdb_id`, under review with one open and one resolved item, has the
    issue `issue` and the access `access` with an open licence. Its interventions show a regular
    and an irregular schedule, its measurements and timecourses arithmetic and geometric
    statistics. It has a one-page paper, an image of each source (FORMAT2_IMAGES) and the raw
    table of Tab2.
    """
    from pkdb.studyformat.formatter import format_folder
    from pkdb.studyformat.jsonio import dump_json
    from pkdb.studyformat.tables import TABLES
    from pkdb.studyformat.text import render_tsv

    def tsv(kind, *rows):
        names = TABLES[kind].names
        return render_tsv(
            names, [tuple(row.get(name, "") for name in names) for row in rows]
        )

    name = sid.split("/")[1]
    folder = root / sid
    folder.mkdir(parents=True)
    item = {
        "kind": "question",
        "target": {"file": "outputs_Tab2.tsv", "column": "gmean"},
        "text": "Is the geometric mean read from the table?",
        "author": "curator",
        "created": "2026-10-05T10:12:00Z",
    }
    files = {
        "study.json": dump_json(
            {
                "format": 2,
                "reference": {"pmid": pmid},
                "creator": "curator",
                "curators": [{"user": "curator", "rating": 3}],
                "licence": "open",
                "access": access,
                "issue": issue,
                "release": {"pkdb_id": pkdb_id, "date": "2026-09-28"},
                "descriptions": ["Plasma levels in mg/l."],
            }
        ),
        "reference.json": dump_json(
            {
                "sid": pmid,
                "name": name,
                "pmid": pmid,
                "title": "Artificial study format 2 fixture",
            }
        ),
        "review.json": dump_json(
            {
                "status": "in_review",
                "reviewers": ["curator"],
                "items": [
                    {**item, "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2AB"},
                    {
                        **item,
                        "id": "01JA2XK7Q8M3R5T6V9W0Y1Z2AC",
                        "state": "resolved",
                        "resolved_by": "curator",
                        "resolved": "2026-10-05T11:00:00Z",
                    },
                ],
            }
        ),
        "subjects.tsv": tsv(
            "subjects", {"name": "all", "count": "4", "source": "Tab1"}
        ),
        "characteristica.tsv": tsv(
            "characteristica",
            *(
                {"source": "Tab1", "subjects": "all", "measurement": m, "choice": c}
                for m, c in (
                    ("species", "homo sapiens"),
                    ("sex", "NR"),
                    ("healthy", "Y"),
                )
            ),
        ),
        "interventions.tsv": tsv(
            "interventions",
            {
                "source": "Text",
                "name": "D1",
                "subjects": "all",
                "measurement": "dosing",
                "substance": "drug",
                "route": "oral",
                "form": "tablet",
                "application": "multiple dose",
                "time": "0",
                "interval": "24",
                "doses": "7",
                "time_unit": "h",
                "mean": "10",
                "sd": "1",
                "unit": "mg",
            },
            {
                "source": "Text",
                "name": "D2",
                "measurement": "dosing",
                "substance": "drug-b",
                "route": "oral",
                "form": "tablet",
                "application": "multiple dose",
                "time": "0;12;40",
                "time_unit": "h",
                "mean": "5",
                "unit": "mg",
            },
        ),
        "outputs_Tab2.tsv": tsv(
            "outputs",
            *(
                {
                    "subjects": "all",
                    "interventions": "D1",
                    "measurement": "concentration",
                    "substance": "drug",
                    "tissue": "plasma",
                    "time_unit": "h",
                    "unit": "mg/l",
                    **row,
                }
                for row in (
                    {"time": "1", "mean": "2"},
                    {"time": "2", "gmean": "4", "gsd": "1.5"},
                    {"time": "4", "gmean": "3", "gcv": "50", "interventions": "D1,D2"},
                )
            ),
        ),
        "timecourses_Fig1.tsv": tsv(
            "timecourses",
            *(
                {
                    "label": label,
                    "subjects": "all",
                    "interventions": "D1",
                    "measurement": "concentration",
                    "substance": "drug",
                    "tissue": "plasma",
                    "time_unit": "h",
                    "unit": "mg/l",
                    **row,
                }
                for label, rows in (
                    (
                        "Plasma after 10 mg daily (geometric)",
                        (
                            {"time": "1", "gmean": "8", "gsd": "2"},
                            {"time": "2", "gmean": "4", "gsd": "1.5"},
                            {"time": "4", "gmean": "2", "gsd": "1.25"},
                        ),
                    ),
                    (
                        "Plasma after 10 mg daily (arithmetic)",
                        (
                            {"time": "1", "mean": "9", "sd": "1"},
                            {"time": "2", "mean": "5", "sd": "0.5"},
                            {"time": "4", "mean": "2", "sd": "0.25"},
                        ),
                    ),
                )
                for row in rows
            ),
        ),
    }
    for file, text in files.items():
        (folder / file).write_text(text, encoding="utf-8", newline="")
    # The paper table Tab2 as printed, which only curators see.
    (folder / f"{name}_Tab2.tsv").write_text(
        "Time (h)\tConcentration (mg/l)\n1\t2\n2\t4\n4\t3\n",
        encoding="utf-8",
        newline="",
    )
    (folder / f"{name}.pdf").write_bytes(fixture_pdf(f"{name} paper"))
    for source, size in FORMAT2_IMAGES.items():
        (folder / f"{name}_{source}.png").write_bytes(fixture_png(size))
    assert format_folder(folder).ok
    return folder
