"""Logging of the package.

Modules only get their logger via `logging.getLogger(__name__)` and log to it,
importing `pkdb_data` does not configure logging. The command line commands and
scripts enable the rich output explicitly with `enable_rich_logging`.
"""

import logging

from pymetadata import log as pymetadata_log
from pymetadata.console import console
from rich.logging import RichHandler

#: name of the logger all loggers of the package are below
PACKAGE_LOGGER = "pkdb_data"


def enable_rich_logging(level: int = logging.INFO) -> logging.Logger:
    """Log the messages of `pkdb_data` and `pymetadata` on the rich console.

    Meant for the command line commands and scripts. Calling it repeatedly
    replaces the handler instead of adding a second one.

    Args:
        level: level from which messages are logged

    Returns:
        The `pkdb_data` logger.
    """
    pymetadata_log.enable_rich_logging(level=level)

    logger = logging.getLogger(PACKAGE_LOGGER)
    for handler in list(logger.handlers):
        if isinstance(handler, RichHandler):
            logger.removeHandler(handler)

    handler = RichHandler(
        markup=False,
        rich_tracebacks=True,
        show_time=False,
        console=console,
    )
    handler.setFormatter(logging.Formatter(fmt="%(message)s", datefmt="[%X]"))

    logger.addHandler(handler)
    logger.setLevel(level)
    return logger
