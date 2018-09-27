"""
Helpers related to logging
"""

import coloredlogs
coloredlogs.install(
    level="INFO",
    fmt="%(module)s:%(lineno)s %(funcName)s %(levelname) -10s %(message)s"
    # fmt="%(levelname) -10s %(asctime)s %(module)s:%(lineno)s %(funcName)s %(message)s"
)