"""
Base settings schema for core-utils and consumer projects.

CoreSettings defines the fields that core-utils utilities (logger, profiler)
expect to find. It does NOT load any files — that is the responsibility of
the consumer application.

Consumer projects subclass CoreSettings, add their own fields, and configure
the env_file source to match their project layout:

    from core_utils.settings import CoreSettings

    class Settings(CoreSettings):
        model_config = {
            "env_file": [".env", ".env.local"],
            "env_file_encoding": "utf-8",
        }
        api_key: str = ""

    settings = Settings()
"""

from pathlib import Path

from pydantic_settings import BaseSettings


class CoreSettings(BaseSettings):
    """
    Base settings schema with fields required by core-utils utilities.

    Reads values from environment variables only (no file loading).
    Subclasses should add env_file to model_config if file loading is needed.
    """

    model_config = {
        "case_sensitive": False,
        "extra": "allow",
    }

    # Environment
    environment: str = "development"  # development, staging, production

    # Logging
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_folder: str = "logs"
    log_console: bool = True

    @property
    def logs_dir(self) -> Path:
        """Resolved logs directory. Creates it if it does not exist."""
        path = Path(self.log_folder)
        path.mkdir(parents=True, exist_ok=True)
        return path


__all__ = ["CoreSettings"]
