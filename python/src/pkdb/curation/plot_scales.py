"""The scales that the curator chose for the plot of mapped rows of a figure.

The server keeps them with its settings in state.json, like the theme: the browser forgets
what it stores, as `pkdb curate` starts on another port, and so another origin, every time.
The key is the figure, `<substance>/<study>/<source>`; only the figures whose scales the
curator changed have an entry, with both axes. The other figures follow the digitization.
"""

from pkdb.studyformat.tables import SOURCE_PATTERN

#: The scales of an axis, as Plotly names them.
AXIS_SCALES = ("linear", "log")
#: At most this many figures keep their scales; the oldest choice goes first.
MAX_FIGURES = 10_000


def _is_figure(value: object) -> bool:
    if not isinstance(value, str) or len(value) > 512:
        return False
    parts = value.split("/")
    return (
        len(parts) == 3
        and all(part and part == part.strip() for part in parts)
        and SOURCE_PATTERN.fullmatch(parts[2]) is not None
    )


def figure_scales(value: object) -> tuple[str, dict[str, str]]:
    """The figure and the scales of a `plot_scale` setting; ValueError for anything else."""
    if not isinstance(value, dict) or set(value) != {"figure", "x", "y"}:
        raise ValueError("A plot scale names its figure and the scales of x and y")
    if not _is_figure(value["figure"]):
        raise ValueError("The figure of a plot scale is <substance>/<study>/<source>")
    if value["x"] not in AXIS_SCALES or value["y"] not in AXIS_SCALES:
        raise ValueError("The scale of an axis must be linear or log")
    return value["figure"], {"x": value["x"], "y": value["y"]}


def saved_plot_scales(value: object) -> dict[str, dict[str, str]]:
    """The valid entries of saved plot scales; a damaged state.json keeps the defaults."""
    if not isinstance(value, dict):
        return {}
    result: dict[str, dict[str, str]] = {}
    for figure, scales in value.items():
        if not isinstance(scales, dict):
            continue
        try:
            key, kept = figure_scales({**scales, "figure": figure})
        except ValueError:
            continue
        result[key] = kept
    return result


def keep_plot_scales(
    saved: dict[str, dict[str, str]], figure: str, scales: dict[str, str]
) -> None:
    """Keep the scales of `figure` as the latest choice; beyond MAX_FIGURES the oldest go."""
    saved.pop(figure, None)
    saved[figure] = scales
    for old in list(saved)[: max(0, len(saved) - MAX_FIGURES)]:
        del saved[old]
