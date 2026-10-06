"""Info nodes with calculation types."""

from pymetadata.core.miriam import BQB

from ..node import CalculationType, DType, InfoNode

CALCULATION_NODES: list[InfoNode] = [
    CalculationType(
        "calculation",
        description="Calculated value.",
        parents=[],
        dtype=DType.ABSTRACT,
    ),
    CalculationType(
        "geometric mean",
        description="The geometric mean is defined as the nth root of the product of n "
        "numbers.",
        parents=["calculation"],
        dtype=DType.CATEGORICAL,
        annotations=[
            (BQB.IS, "STATO:0000396"),
        ],
    ),
    CalculationType(
        "unspecified summary",
        description="A reported central value whose summary statistic the "
        "publication does not state. It is stored in mean and never completed "
        "with derived statistics.",
        parents=["calculation"],
        dtype=DType.CATEGORICAL,
    ),
    CalculationType(
        "sample mean",
        description="The sample mean of sample of size n with n observations is an "
        "arithmetic mean computed over n number of observations on a "
        "statistical sample.",
        parents=["calculation"],
        dtype=DType.CATEGORICAL,
        annotations=[
            (BQB.IS, "STATO:0000401"),
        ],
    ),
]
