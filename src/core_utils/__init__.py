"""core-utils: generic utilities for Python projects."""

__version__ = "1.1.0"

from core_utils.logger import configure_logger, logger
from core_utils.profiler import NullProfiler, Profiler, Step, profiler
from core_utils.settings import CoreSettings
from core_utils.token_counter import TokenCounter
from core_utils.yaml_loader import load_yaml_as, load_yaml_dir_as

__all__ = [
    "CoreSettings",
    "configure_logger",
    "load_yaml_as",
    "load_yaml_dir_as",
    "logger",
    "profiler",
    "Profiler",
    "NullProfiler",
    "Step",
    "TokenCounter",
]
