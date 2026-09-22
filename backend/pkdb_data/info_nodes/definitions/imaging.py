"""Definition of MRI measurements."""

from ..node import DType, InfoNode, MeasurementType
from ..units import (
    DIMENSIONLESS,
)

IMAGING_MEASUREMENT_NODES: list[InfoNode] = [
    MeasurementType(
        sid="mri-measurement",
        name="MRI measurement",
        description="measurement via MRI",
        parents=["measurement"],
        dtype=DType.ABSTRACT,
        annotations=[],
    ),
    MeasurementType(
        sid="ct-measurement",
        name="CT measurement",
        description="measurement via CT",
        parents=["measurement"],
        dtype=DType.ABSTRACT,
        annotations=[],
    ),
    MeasurementType(
        sid="relative-signal-intensity",
        name="relative signal intensity",
        description="Relative signal intensity normalized to zero time point before"
        "tracer injection",
        parents=["mri measurement"],
        dtype=DType.NUMERIC,
        units=[DIMENSIONLESS],
        annotations=[],
    ),
    MeasurementType(
        sid="maximum-relative-signal-intensity",
        name="maximum relative signal intensity",
        description="Maximum of relative signal intensity normalized to zero time point before"
        "tracer injection",
        parents=["mri measurement"],
        dtype=DType.NUMERIC,
        units=[DIMENSIONLESS],
        annotations=[],
    ),
    MeasurementType(
        sid="attenuation",
        name="attenuation",
        description="Attenuation",
        parents=["ct measurement"],
        dtype=DType.NUMERIC,
        units=[DIMENSIONLESS],
        annotations=[],
    ),
]
