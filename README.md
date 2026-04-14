# core-utils

Generic Python utilities designed to be shared across projects.

## Installation

```bash
# from GitHub
pip install git+https://github.com/fermaat/core-utils.git

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

Hierarchical step profiler for instrumenting pipelines (LLM, ML, ETL, etc.).

**Activation** — the profiler is completely inert unless `PROFILER_ENABLED` is set.
No logging, no processing, zero overhead:

```bash
PROFILER_ENABLED=true python main.py   # active
python main.py                          # NullProfiler, no-op
```

**Session context** — set once, appears in every report and JSON export:

```python
from core_utils.profiler import profiler

profiler.set_context(pipeline="de_pipeline", env="production")
```

**Context manager** — for arbitrary code blocks:

```python
with profiler.step("full_run") as root:
    root.tag(dataset="customers_v3")

    with profiler.step("load_data") as s:
        records = load()
        s.tag(count=len(records))

    with profiler.step("inference") as s:
        s.tag(model="gpt-4o", temperature=0.7)

        with profiler.step("llm_call") as llm_s:
            response = call_llm(prompt)
            llm_s.tag(tokens=1500)

# Report is logged automatically when the root step closes:
# [profiler | pipeline=de_pipeline  env=production]  full_run — 1.823s
#   1. load_data                        0.082s  ✓  {'count': 120}
#   2. inference                        1.710s  ✓  {'model': 'gpt-4o', ...}
#     2.1. llm_call                     1.680s  ✓  {'tokens': 1500}
```

**Decorator** — for function-level steps, sync and async:

```python
@profiler.measure("embed_text")
def embed(text: str) -> list[float]:
    ...

@profiler.measure("call_llm")
async def call_llm(prompt: str) -> str:
    ...
```

**Multiple runs** — executes N times, reports mean / min / max:

```python
@profiler.measure("embed_text", runs=10)
def embed(text: str) -> list[float]:
    ...
# step metadata: {runs_planned: 10, runs_completed: 10, mean_s: 0.012, min_s: 0.010, max_s: 0.015}
```

**JSON export:**

```python
print(profiler.to_json())
# {
#   "context": {"pipeline": "de_pipeline", "env": "production"},
#   "runs": [{"name": "full_run", "step_id": "1", "duration": 1.823, ...}]
# }
```

**Cross-repo usage** — the `profiler` singleton is shared across all imports.
Set context and open the root step in your entry point; instrument functions
in any downstream repo transparently:

```python
# entry point (main repo)
from core_utils.profiler import profiler

profiler.set_context(pipeline="de_pipeline")
with profiler.step("pipeline"):
    actor.run()   # calls profiler.step() internally — same tree

# actor repo
from core_utils.profiler import profiler

def run():
    with profiler.step("actor_step"):
        ...
```

See [`scripts/example_profiler.py`](scripts/example_profiler.py) for a full runnable example.

---

## Adding core-utils to a project's pyproject.toml

```toml
[project]
dependencies = [
    "core-utils @ git+https://github.com/fermaat/core-utils.git",
]
```

Or for local development:

```toml
[tool.pdm.dev-dependencies]
dev = [
    "core-utils @ file:///path/to/core-utils",
]
```
