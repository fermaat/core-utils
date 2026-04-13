"""
Base settings class for core-utils and consumer projects.

Consumer projects should subclass CoreSettings and add their own fields:

    from core_utils.settings import CoreSettings

    class Settings(CoreSettings):
        api_key: str = ""
        model_name: str = "gpt-4o"

    settings = Settings()
"""

from pathlib import Path

from pydantic_settings import BaseSettings


class CoreSettings(BaseSettings):
    """
    Base settings with fields required by core-utils utilities.

    Loads from .env and .env.local files at the project root.
    Consumer projects subclass this and add their own fields.
    """

    model_config = {
        "case_sensitive": False,
        "extra": "allow",
        "env_file": [".env", ".env.local"],
        "env_file_encoding": "utf-8",
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
