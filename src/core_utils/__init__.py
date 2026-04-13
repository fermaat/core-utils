"""core-utils: generic utilities for Python projects."""

__version__ = "0.1.0"

from core_utils.logger import configure_logger, logger
from core_utils.settings import CoreSettings

__all__ = [
    "CoreSettings",
    "configure_logger",
    "logger",
]
