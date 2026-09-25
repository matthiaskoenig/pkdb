"""Permission-scoped coverage metrics grouped by study date, not ingestion date."""

from datetime import UTC, datetime

from pydantic import BaseModel
from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from pkdb.schemas.security import Principal
from pkdb_server.db.models.measurements import Measurement, Timecourse
from pkdb_server.db.models.studies import Study
from pkdb_server.db.models.vocabulary import VocabularyEdge, VocabularyNode
from pkdb_server.db.queries import visibility


class Coverage(BaseModel):
    year: int | None
    study_count: int = 0
    timecourse_count: int = 0
    substance_count: int = 0
    pk_count: int = 0
    pk_calculated_count: int = 0
    cumulative_study_count: int = 0
    cumulative_substance_count: int = 0


class ParameterCount(BaseModel):
    sid: str
    name: str
    year: int | None
    reported: int
    calculated: int


class SubstanceCount(BaseModel):
    sid: str
    name: str
    timecourse_count: int


class StatisticsOverview(BaseModel):
    generated_at: datetime
    date_basis: str = "study.date"
    counts: dict[str, int]
    years: list[Coverage]
    undated: Coverage
    substances: list[SubstanceCount]
    parameters: list[ParameterCount]


def overview(
    session: Session, principal: Principal, counts: dict[str, int]
) -> StatisticsOverview:
    """Aggregate in SQL; only yearly/category totals leave PostgreSQL.

    A substance is covered when a normalized observation belongs to a timecourse.
    PK types are descendants of the vocabulary's pharmacokinetic-measurement node.
    Count normalized values once, distinguishing curated from calculated values.
    """
    visible = (
        select(Study.id, func.extract("year", Study.date).cast(Integer).label("year"))
        .where(visibility(principal))
        .cte("visible_studies")
    )
    buckets: dict[int | None, Coverage] = {None: Coverage(year=None)}
    for year, count in session.execute(
        select(visible.c.year, func.count()).group_by(visible.c.year)
    ):
        buckets[year] = Coverage(year=year, study_count=count)

    course_members = (
        select(Measurement.id)
        .where(
            Measurement.study_id == Timecourse.study_id,
            Measurement.id == Timecourse.measurement_ids.any_(),
            Measurement.origin == "normalized",
        )
        .exists()
    )
    for year, count in session.execute(
        select(visible.c.year, func.count())
        .select_from(Timecourse)
        .join(visible, visible.c.id == Timecourse.study_id)
        .where(course_members)
        .group_by(visible.c.year)
    ):
        buckets[year].timecourse_count = count

    substances: dict[str, SubstanceCount] = {}
    year_substances: dict[int | None, set[str]] = {}
    for year, sid, name, count in session.execute(
        select(
            visible.c.year,
            VocabularyNode.sid,
            VocabularyNode.name,
            func.count(func.distinct(Timecourse.id)),
        )
        .select_from(Timecourse)
        .join(visible, visible.c.id == Timecourse.study_id)
        .join(
            Measurement,
            (Measurement.id == Timecourse.measurement_ids.any_())
            & (Measurement.study_id == Timecourse.study_id),
        )
        .join(VocabularyNode, VocabularyNode.sid == Measurement.substance)
        .where(Measurement.origin == "normalized")
        .group_by(visible.c.year, VocabularyNode.sid, VocabularyNode.name)
    ):
        year_substances.setdefault(year, set()).add(sid)
        item = substances.setdefault(
            sid, SubstanceCount(sid=sid, name=name, timecourse_count=0)
        )
        item.timecourse_count += count

    descendants = (
        select(VocabularyNode.sid)
        .where(VocabularyNode.sid == "pharmacokinetic-measurement")
        .cte("pk_types", recursive=True)
    )
    descendants = descendants.union(
        select(VocabularyEdge.child).join(
            descendants, VocabularyEdge.parent == descendants.c.sid
        )
    )
    parameters = []
    for year, sid, name, reported, calculated in session.execute(
        select(
            visible.c.year,
            VocabularyNode.sid,
            VocabularyNode.name,
            func.count().filter(Measurement.calculated.is_(False)),
            func.count().filter(Measurement.calculated.is_(True)),
        )
        .select_from(Measurement)
        .join(visible, visible.c.id == Measurement.study_id)
        .join(VocabularyNode, VocabularyNode.sid == Measurement.measurement_type)
        .where(
            Measurement.origin == "normalized",
            Measurement.measurement_type.in_(select(descendants.c.sid)),
        )
        .group_by(visible.c.year, VocabularyNode.sid, VocabularyNode.name)
        .order_by(visible.c.year, VocabularyNode.sid)
    ):
        parameters.append(
            ParameterCount(
                year=year, sid=sid, name=name, reported=reported, calculated=calculated
            )
        )
        buckets[year].pk_count += reported + calculated
        buckets[year].pk_calculated_count += calculated

    dated = [year for year in buckets if year is not None]
    years = []
    seen: set[str] = set()
    study_total = 0
    if dated:
        for year in range(min(dated), max(dated) + 1):
            bucket = buckets.get(year, Coverage(year=year))
            seen.update(year_substances.get(year, set()))
            study_total += bucket.study_count
            bucket.substance_count = len(year_substances.get(year, set()))
            bucket.cumulative_study_count = study_total
            bucket.cumulative_substance_count = len(seen)
            years.append(bucket)
    buckets[None].substance_count = len(year_substances.get(None, set()))
    sorted_substances = sorted(
        substances.values(), key=lambda item: (-item.timecourse_count, item.sid)
    )
    return StatisticsOverview(
        generated_at=datetime.now(UTC),
        counts={
            **counts,
            "substance_count": len(substances),
            "pk_count": sum(bucket.pk_count for bucket in buckets.values()),
            "pk_calculated_count": sum(
                bucket.pk_calculated_count for bucket in buckets.values()
            ),
        },
        years=years,
        undated=buckets[None],
        substances=sorted_substances,
        parameters=parameters,
    )
