# core-utils

Generic Python utilities designed to be shared across projects.

## Installation

```bash
# from GitHub
pip install git+https://github.com/ferveloz/core-utils.git

# local development (editable)
pip install -e /path/to/core-utils
```

## Utilities

### Settings

`CoreSettings` is a base class built on [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/).
Subclass it in your project and add your own fields. It automatically loads values from `.env` and `.env.local`.

**Fields included in `CoreSettings`:**

| Field | Default | Description |
|---|---|---|
| `environment` | `"development"` | `development`, `staging`, `production` |
| `log_level` | `"INFO"` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `log_folder` | `"logs"` | Directory for log files |
| `log_console` | `True` | Whether to also print logs to stderr |

**Usage:**

```python
# myproject/config.py
from core_utils.settings import CoreSettings

class Settings(CoreSettings):
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    max_retries: int = 3

settings = Settings()  # reads from .env automatically
```

---

### Logger

`configure_logger` sets up [loguru](https://github.com/Delgan/loguru) with a file sink and an optional console sink.
Call it once at startup, then use `loguru.logger` anywhere.

```python
# myproject/config.py
from core_utils.logger import configure_logger
from myproject.config import settings

configure_logger(settings)
```

After that, import `logger` from loguru directly in any module:

```python
from loguru import logger

logger.info("Pipeline started")
logger.debug("Calling LLM...")
```

**Explicit overrides** (skip settings):

```python
configure_logger(level="DEBUG", log_file="logs/dev.log", console=False)
```

**Log format:**

- File: `2026-04-13 10:23:01 | INFO     | mymodule:my_func:42 | message`
- Console: `10:23:01 | INFO     | message`

---

### Profiler

Coming soon.

---

## Adding core-utils to a project's pyproject.toml

```toml
[project]
dependencies = [
    "core-utils @ git+https://github.com/ferveloz/core-utils.git",
]
```

Or for local development:

```toml
[tool.pdm.dev-dependencies]
dev = [
    "core-utils @ file:///path/to/core-utils",
]
```
