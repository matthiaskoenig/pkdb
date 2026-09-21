"""Test the unit registry."""

import pytest

from pkdb_app.info_nodes.units import ureg


@pytest.mark.parametrize("unit", ["cups", "beverages", "none"])
def test_count_units(unit: str) -> None:
    """The custom count units convert to count."""
    assert ureg.Quantity(2, unit).to("count").magnitude == pytest.approx(2)


def test_percent() -> None:
    """Percent is a hundredth of a count."""
    assert ureg.Quantity(50, "percent").to("count").magnitude == pytest.approx(0.5)


@pytest.mark.parametrize("unit", ["IU", "NO_UNIT", "arbitrary_unit"])
def test_own_dimension(unit: str) -> None:
    """The units with an own dimension do not convert to count or mass."""
    quantity = ureg.Quantity(1, unit)
    assert not quantity.check("[mass]")
    assert not quantity.dimensionless


def test_pharmacokinetic_conversion() -> None:
    """A typical conversion of a concentration."""
    assert ureg.Quantity(1, "mg/l").to("µg/ml").magnitude == pytest.approx(1)
