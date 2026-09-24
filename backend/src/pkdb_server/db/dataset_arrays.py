"""Read projections of ordered dataset arrays; no persisted point entities."""

from sqlalchemy import BigInteger, Integer, column, func, select, true
from sqlalchemy.orm import aliased

from pkdb_server.db.models.measurements import Scatter, Subset


def dataset_type():
    parent = aliased(Scatter)
    return (
        select(parent.data_type)
        .where(parent.id == Subset.scatter_id)
        .correlate(Subset)
        .scalar_subquery()
    )


def dataset_cells():
    """Expand series cells only for relational analysis filtering and pagination."""
    series = aliased(Subset)
    indices = (
        func.generate_subscripts(series.measurement_ids, 1)
        .table_valued(column("ordinal", Integer))
        .render_derived()
        .lateral()
    )
    position = indices.c.ordinal - 1
    width = func.nullif(func.jsonb_array_length(series.dimension_labels), 0)
    row_index = (position // width).cast(Integer)
    dimension_index = (position % width).cast(Integer)
    return (
        select(
            series.study_id.label("study_id"),
            series.id.label("subset_id"),
            position.label("position"),
            dimension_index.label("dimension"),
            series.point_ids[row_index + 1].cast(BigInteger).label("point_id"),
            series.measurement_ids[indices.c.ordinal].label("measurement_id"),
        )
        .select_from(series)
        .join(indices, true())
        .cte("dataset_cells")
    )
