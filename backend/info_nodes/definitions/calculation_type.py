"""Info nodes with calculation types."""

from pymetadata.core.miriam import BQB

from ..node import CalculationType, DType, InfoNode

CALCULATION_NODES: list[InfoNode] = [
    CalculationType(
        "calculation",
        description="Calculated value.",
        parents=[],
        dtype=DType.ABSTRACT,
        annotations=[],
    ),
    CalculationType(
        "geometric mean",
        description="The geometric mean is defined as the nth root of the product of n "
        "numbers.",
        parents=["calculation"],
        dtype=DType.CATEGORICAL,
        annotations=[
            (BQB.IS, "stato/STATO:0000396"),
        ],
    ),
    CalculationType(
        "sample mean",
        description="The sample mean of sample of size n with n observations is an "
        "arithmetic mean computed over n number of observations on a "
        "statistical sample.",
        parents=["calculation"],
        dtype=DType.CATEGORICAL,
        annotations=[
            (BQB.IS, "stato/STATO:0000401"),
        ],
    ),
]
