"""Instrumentation and diagnostic nodes ATLAS."""

from pymetadata.core.miriam import BQB

from pkdb_data.atlas.units_atlas import (
    CLEARANCE_UNITS,
    PERCENTAGE,
)
from pkdb_data.info_nodes.node import (
    DType,
    InfoNode,
    MeasurementType,
)

# TODO reference values?
# TODO names?
# TODO synonyms

INSTRUM_DIAGN_ATLAS_NODES: list[InfoNode] = [
    MeasurementType(
        "ICG‐R15",
        label="Indocyanine Green 15 Minutes Retention Test",
        description="The determination of ICG retention rate at "
        "15 min after intravenous injection. ",
        synonyms=["Indocyanine green 15-minute retention"],
        dtype=DType.NUMERIC,
        units=[PERCENTAGE],
        annotations=[],
        parents=["instrumental-diagnostics", "liver-status"],
    ),
    MeasurementType(
        "ICG‐cl",
        label="Indocyanine Green Clearance",
        description="The determination of the amount of the volume of serum or plasma "
        "that would be cleared of indocyanine green by excretion for a "
        "specified unit of time (e.g. one minute). ",
        synonyms=[],
        dtype=DType.NUMERIC,
        units=CLEARANCE_UNITS,
        annotations=[
            (BQB.IS, "ncit/C184513"),
        ],
        parents=["instrumental-diagnostics", "liver-status"],
    ),
]
