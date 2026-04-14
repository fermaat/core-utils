"""
Logger configuration for core-utils and consumer projects.

Usage in a consumer project:

    from core_utils.logger import configure_logger
    from myproject.config import settings  # your CoreSettings subclass

    configure_logger(settings)

    from loguru import logger
    logger.info("Ready")

If called without arguments, falls back to sensible defaults.
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core_utils.settings import CoreSettings

from loguru import logger


def configure_logger(
    settings: "CoreSettings | None" = None,
    *,
    level: str | None = None,
    log_file: str | None = None,
    console: bool | None = None,
) -> None:
    """
    Configure loguru with file and optional console sinks.

    Priority for each option: explicit kwarg > settings field > default.

    Args:
        settings: A CoreSettings (or subclass) instance.
        level:    Override log level (e.g. "DEBUG").
        log_file: Override log file path.
        console:  Override whether to enable console output.
    """
    resolved_level = level or (settings.log_level if settings else "INFO")
    resolved_console = (
        console if console is not None else (settings.log_console if settings else True)
    )

    if log_file is None and settings is not None:
        log_file = str(settings.logs_dir / "app.log")
    elif log_file is None:
        log_file = "logs/app.log"

    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    logger.remove()

    logger.add(
        log_file,
        level=resolved_level,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        ),
        rotation="10 MB",
        retention="30 days",
        enqueue=False,
    )

    if resolved_console:
        logger.add(
            sys.stderr,
            level=resolved_level,
            format=(
                "<green>{time:HH:mm:ss}</green> | " "<level>{level: <8}</level> | " "{message}"
            ),
            colorize=True,
        )


__all__ = ["configure_logger", "logger"]
