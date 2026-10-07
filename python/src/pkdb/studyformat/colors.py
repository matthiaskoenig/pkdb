"""The colors of the series of a figure, shared by `pkdb plot` and the curation app.

Eight hues in a fixed order, each in a step for white paper and the light theme and a step for
the dark surface of the app (#192b31). Every step has at least 3:1 contrast against its
background, and neighbors in the order stay apart for the common color vision deficiencies
(protan, deutan, tritan). Past eight series the colors repeat; the legend, the hover label and
the data table name each series.
"""

SERIES_COLORS = (
    "#2a78d6",  # blue
    "#d65a24",  # orange
    "#14876a",  # aqua
    "#a87400",  # yellow
    "#c94a83",  # magenta
    "#3c8a00",  # green
    "#6750c6",  # violet
    "#d63c3c",  # red
)

SERIES_DARK_COLORS = (
    "#3987e5",
    "#d95926",
    "#199e70",
    "#c98500",
    "#d55181",
    "#2f9a2f",
    "#9085e9",
    "#e66767",
)

# A ring around a digitized point; it has contrast against the paper of the figure.
POINT_RING = "#1f1f1f"


def series_color(index: int) -> tuple[str, str]:
    """The light and the dark color of the series at `index` of the order."""
    return (
        SERIES_COLORS[index % len(SERIES_COLORS)],
        SERIES_DARK_COLORS[index % len(SERIES_DARK_COLORS)],
    )
