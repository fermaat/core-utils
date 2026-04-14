"""
Minimal profiler

Provides a context manager and decorator that log step timing via loguru.
No step tree, no JSON export, no session context — just named timings.

Active only when PROFILER_ENABLED env var is set to a truthy value
("1", "true", "yes"). Otherwise a no-op is used with zero overhead.

Usage:
    PROFILER_ENABLED=true python main.py

    from core_utils.simple_profiler import profiler

    with profiler.step("pipeline"):
        run_pipeline()

    @profiler.measure("my_function")
    def my_function():
        ...
"""

import os
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Generator

from loguru import logger

_ENABLED: bool = os.getenv("PROFILER_ENABLED", "").lower() in ("1", "true", "yes")


class SimpleProfiler:
    """Minimal profiler: context manager + decorator, flat log output."""

    @contextmanager
    def step(self, name: str) -> Generator[None, None, None]:
        """Time a named block and log the result."""
        start = time.perf_counter()
        try:
            yield
            elapsed = time.perf_counter() - start
            logger.info(f"[profiler] {name} — {elapsed:.3f}s ✓")
        except Exception as e:
            elapsed = time.perf_counter() - start
            logger.info(f"[profiler] {name} — {elapsed:.3f}s ✗  {type(e).__name__}")
            raise

    def measure(self, name: str) -> Callable[..., Any]:
        """Decorator that times a function call. Works with sync and async."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            import asyncio

            if asyncio.iscoroutinefunction(func):

                @wraps(func)
                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    with self.step(name):
                        return await func(*args, **kwargs)

                return async_wrapper

            else:

                @wraps(func)
                def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                    with self.step(name):
                        return func(*args, **kwargs)

                return sync_wrapper

        return decorator


class _NullSimpleProfiler:
    """Inert profiler used when PROFILER_ENABLED is not set. Zero overhead."""

    @contextmanager
    def step(self, name: str) -> Generator[None, None, None]:
        yield

    def measure(self, name: str) -> Callable[..., Any]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return func

        return decorator


profiler: SimpleProfiler | _NullSimpleProfiler = (
    SimpleProfiler() if _ENABLED else _NullSimpleProfiler()
)

__all__ = ["profiler", "SimpleProfiler"]
