"""Information related to demographics.

Examples are income, education and other social factors.
"""

from ..node import Choice, DType, InfoNode, MeasurementType
from ..units import NO_UNIT

DEMOGRAPHICS_NODES: list[InfoNode] = [
    MeasurementType(
        sid="demographics-measurement",
        name="demographics measurement",
        description="Demographics measurement. Information related to education, "
        "income and social factors.",
        parents=["measurement"],
        dtype=DType.ABSTRACT,
    ),
    MeasurementType(
        sid="education-measurement",
        name="education measurement",
        description="Education measurement. Information related to education status or "
        "duration.",
        parents=["demographics measurement"],
        dtype=DType.ABSTRACT,
    ),
    MeasurementType(
        sid="education-duration",
        name="education duration",
        description="Duration of education in years.",
        parents=["education-measurement"],
        dtype=DType.NUMERIC,
        units=["year", NO_UNIT],
    ),
    MeasurementType(
        sid="work-measurement",
        name="work measurement",
        description="Work measurement. Information related to work status or duration.",
        parents=["demographics measurement"],
        dtype=DType.ABSTRACT,
    ),
    MeasurementType(
        sid="work-hours-categorial",
        name="work hours (categorial)",
        description="Work hours categorical.",
        parents=["work-measurement"],
        dtype=DType.CATEGORICAL,
    ),
    Choice(
        sid="work-fulltime",
        name="work fulltime",
        description="Fulltime work.",
        parents=["work hours (categorial)"],
        annotations=[],
        synonyms=[],
    ),
    Choice(
        sid="work-no-fulltime",
        name="work no fulltime",
        description="No fulltime work, i.e., part-time or no work.",
        parents=["work hours (categorial)"],
        annotations=[],
        synonyms=[],
    ),
    Choice(
        sid="work-parttime",
        name="work parttime",
        description="Parttime work.",
        parents=["work hours (categorial)"],
        annotations=[],
        synonyms=[],
    ),
    Choice(
        sid="work-notime",
        name="work notime",
        description="Not working any hours.",
        parents=["work hours (categorial)"],
        annotations=[],
        synonyms=[],
    ),
]
