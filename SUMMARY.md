# core-utils — Claude reference summary

## Purpose

Generic Python utilities designed to be shared across personal and work projects.
Currently provides: settings base class, logger configuration, and a hierarchical profiler
for instrumenting LLM/ML pipelines. Installable as a library via pip/pdm.

## Architecture

```
src/core_utils/
├── __init__.py         # Public exports: CoreSettings, configure_logger, logger, profiler, Profiler, Step
├── settings.py         # CoreSettings — pydantic-settings base class for consumer projects
├── logger.py           # configure_logger() — loguru setup with file + console sinks
├── profiler.py         # Full profiler: hierarchical steps, metadata, JSON export, env var guard
└── simple_profiler.py  # Work version: flat CM + decorator only, no tree/JSON

scripts/
└── example_profiler.py # Runnable demo — simulated LLM pipeline with nested steps and benchmark
```

## Key classes / functions

**`CoreSettings`** (`settings.py`)
- `pydantic-settings` base class; subclass to add project-specific fields
- Fields: `environment`, `log_level`, `log_folder`, `log_console`
- Property: `logs_dir` → resolved Path, auto-created

**`configure_logger`** (`logger.py`)
- `configure_logger(settings=None, *, level=None, log_file=None, console=None)`
- Priority: explicit kwarg > settings field > default
- Sets up loguru file sink (rotation 10MB, retention 30d) + optional console sink

**`Profiler`** (`profiler.py`)
- `profiler.set_context(**kwargs)` — session-level metadata (pipeline name, env, etc.)
- `with profiler.step("name") as s:` — context manager; `s.tag(**kwargs)` attaches metadata
- `@profiler.measure("name", runs=N)` — decorator; `runs>1` reports mean/min/max
- Auto-logs the full step tree when the root step closes
- `profiler.to_dict()` / `profiler.to_json()` — export completed runs
- `profiler.reset()` — clear all state

**`NullProfiler`** (`profiler.py`)
- Drop-in replacement when `PROFILER_ENABLED` is not set
- All methods are no-ops; zero runtime overhead

**`SimpleProfiler`** (`simple_profiler.py`)
- Stripped-down version for work repos: CM + decorator, flat log output
- No session context, no JSON, no step tree

## Main entry points

**Installing in another repo:**
```bash
pip install git+https://github.com/fermaat/core-utils.git
# or in pyproject.toml:
# "core-utils @ git+https://github.com/fermaat/core-utils.git"
```

**Settings + logger:**
```python
from core_utils.settings import CoreSettings
from core_utils.logger import configure_logger

class Settings(CoreSettings):
    api_key: str = ""

settings = Settings()
configure_logger(settings)
```

**Profiler:**
```python
from core_utils.profiler import profiler

profiler.set_context(pipeline="de_pipeline", env="prod")

with profiler.step("full_run") as root:
    root.tag(dataset="v3")
    with profiler.step("llm_call") as s:
        s.tag(model="gpt-4o")
        result = call_llm(...)

print(profiler.to_json())
```

**Work profiler:**
```python
from core_utils.simple_profiler import profiler

with profiler.step("pipeline"):
    ...

@profiler.measure("my_function")
def my_function(): ...
```

**Running the example:**
```bash
pdm run example      # PROFILER_ENABLED=true already set in pdm script
```

## Configuration

| Env var | Default | Effect |
|---|---|---|
| `PROFILER_ENABLED` | unset | Set to `1`/`true`/`yes` to activate the profiler |
| `LOG_LEVEL` | `INFO` | Log level for configure_logger |
| `LOG_FOLDER` | `logs` | Directory for log files |
| `LOG_CONSOLE` | `true` | Whether to print logs to stderr |
| `ENVIRONMENT` | `development` | App environment label |

## Dependencies

- Runtime: `loguru>=0.7`, `pydantic-settings>=2.0`
- Dev: `black`, `ruff`, `mypy`, `isort`, `pytest`

## Phase status

- Phase 1 ✓ — settings base, logger configuration, hierarchical profiler, simple profiler, example script
- Phase 2 (pending) — `MemoryProfiler` subclass (tracemalloc per step)
- Phase 3 (pending) — `profiler.benchmark(fn, runs, warmup)` with warmup support
- Out of scope — thread-safety, async-safe context (contextvars), distributed tracing

## Consumers / upstream

- **Used by:** any personal or work Python repo that needs shared settings/logging/profiling
- **Uses:** nothing from other personal repos — intentionally standalone
