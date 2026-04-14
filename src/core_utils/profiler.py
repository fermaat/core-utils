"""
Hierarchical profiler for instrumenting Python pipelines.

Active only when PROFILER_ENABLED env var is set to a truthy value
("1", "true", "yes"). Otherwise a NullProfiler is used — zero overhead,
no logging, no processing of any kind.

Basic usage:
    PROFILER_ENABLED=true python main.py

    from core_utils.profiler import profiler

    profiler.set_context(pipeline="de_pipeline", env="production")

    with profiler.step("full_run") as root:
        root.tag(dataset="customers_v3")

        with profiler.step("load_data") as s:
            records = load()
            s.tag(count=len(records))

        with profiler.step("inference") as s:
            s.tag(model="gpt-4o", temperature=0.7)
            result = call_llm(...)

    # Report is logged automatically when the root step closes.
    print(profiler.to_json())
"""

import asyncio
import json
import os
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Generator

from loguru import logger

_ENABLED: bool = os.getenv("PROFILER_ENABLED", "").lower() in ("1", "true", "yes")


# ── Data model ────────────────────────────────────────────────────────────────


@dataclass
class Step:
    """A single timed section within a profiling run."""

    name: str
    step_id: str
    start: float
    end: float | None = None
    status: str = "running"  # "running" | "ok" | "error"
    error_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    children: list["Step"] = field(default_factory=list)

    @property
    def duration(self) -> float | None:
        if self.end is None:
            return None
        return self.end - self.start

    def tag(self, **kwargs: Any) -> None:
        """Attach key-value metadata to this step."""
        self.metadata.update(kwargs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "step_id": self.step_id,
            "duration": round(self.duration, 6) if self.duration is not None else None,
            "status": self.status,
            "error_type": self.error_type,
            "metadata": self.metadata,
            "children": [c.to_dict() for c in self.children],
        }


class _NullStep:
    """No-op step returned by NullProfiler. Safe to call .tag() on."""

    def tag(self, **kwargs: Any) -> None:
        pass


# ── Active profiler ───────────────────────────────────────────────────────────


class Profiler:
    """
    Hierarchical profiler that builds a step tree and reports via loguru.

    Use the module-level `profiler` singleton rather than instantiating directly.
    """

    def __init__(self) -> None:
        self._stack: list[Step] = []
        self._roots: list[Step] = []
        self._context: dict[str, Any] = {}

    # ── Session context ───────────────────────────────────────────────────────

    def set_context(self, **kwargs: Any) -> None:
        """Set session-level metadata (e.g., pipeline name, environment).

        Appears in every report header and in the JSON export.
        Persists until reset() is called.
        """
        self._context.update(kwargs)

    def reset(self) -> None:
        """Clear all state: stack, completed roots, and session context."""
        self._stack.clear()
        self._roots.clear()
        self._context.clear()

    # ── Step management ───────────────────────────────────────────────────────

    def _next_id(self) -> str:
        if not self._stack:
            return str(len(self._roots) + 1)
        parent = self._stack[-1]
        return f"{parent.step_id}.{len(parent.children) + 1}"

    def _push(self, name: str) -> Step:
        """Create a step, attach it to parent if any, and push onto the stack."""
        s = Step(name=name, step_id=self._next_id(), start=time.perf_counter())
        if self._stack:
            self._stack[-1].children.append(s)
        self._stack.append(s)
        return s

    def _pop(self, s: Step, exc: BaseException | None) -> None:
        """Close a step, pop the stack, and log report if it was the root."""
        s.end = time.perf_counter()
        s.status = "ok" if exc is None else "error"
        if exc is not None:
            s.error_type = type(exc).__name__
        self._stack.pop()
        if not self._stack:
            self._roots.append(s)
            self._log_report(s)

    @contextmanager
    def step(self, name: str) -> Generator[Step, None, None]:
        """Context manager that times a named block.

        Yields the Step so callers can attach metadata via .tag().
        The report is logged automatically when the root step closes.

        Example:
            with profiler.step("load_data") as s:
                records = load()
                s.tag(count=len(records))
        """
        s = self._push(name)
        exc: BaseException | None = None
        try:
            yield s
        except BaseException as e:
            exc = e
            raise
        finally:
            self._pop(s, exc)

    # ── Decorator ─────────────────────────────────────────────────────────────

    def measure(self, name: str, runs: int = 1) -> Callable[..., Any]:
        """Decorator that wraps a function in a profiler step.

        Works with both sync and async functions.
        When runs > 1, the function is executed N times and timing stats
        (mean, min, max) are attached as step metadata.

        Example:
            @profiler.measure("embed_text", runs=5)
            def embed(text: str) -> list[float]:
                ...
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            if asyncio.iscoroutinefunction(func):

                @wraps(func)
                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    if runs > 1:
                        return await self._benchmark_async(name, func, runs, args, kwargs)
                    with self.step(name):
                        return await func(*args, **kwargs)

                return async_wrapper

            else:

                @wraps(func)
                def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                    if runs > 1:
                        return self._benchmark_sync(name, func, runs, args, kwargs)
                    with self.step(name):
                        return func(*args, **kwargs)

                return sync_wrapper

        return decorator

    # ── Benchmark helpers ─────────────────────────────────────────────────────

    def _benchmark_sync(
        self,
        name: str,
        func: Callable[..., Any],
        runs: int,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Any:
        durations: list[float] = []
        result: Any = None
        s = self._push(name)
        exc: BaseException | None = None
        try:
            for _ in range(runs):
                t0 = time.perf_counter()
                result = func(*args, **kwargs)
                durations.append(time.perf_counter() - t0)
        except BaseException as e:
            exc = e
            raise
        finally:
            s.tag(**_benchmark_stats(runs, durations))
            self._pop(s, exc)
        return result

    async def _benchmark_async(
        self,
        name: str,
        func: Callable[..., Any],
        runs: int,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> Any:
        durations: list[float] = []
        result: Any = None
        s = self._push(name)
        exc: BaseException | None = None
        try:
            for _ in range(runs):
                t0 = time.perf_counter()
                result = await func(*args, **kwargs)
                durations.append(time.perf_counter() - t0)
        except BaseException as e:
            exc = e
            raise
        finally:
            s.tag(**_benchmark_stats(runs, durations))
            self._pop(s, exc)
        return result

    # ── Reporting ─────────────────────────────────────────────────────────────

    def _log_report(self, root: Step) -> None:
        ctx_str = "  ".join(f"{k}={v}" for k, v in self._context.items())
        header = "[profiler]"
        if ctx_str:
            header += f" | {ctx_str}"
        dur = root.duration or 0.0
        meta = f"  {root.metadata}" if root.metadata else ""
        header += f"  {root.name} — {dur:.3f}s{meta}"

        lines = [header]
        for child in root.children:
            lines.extend(self._format_step(child, indent=1))

        logger.info("\n" + "\n".join(lines))

    def _format_step(self, s: Step, indent: int) -> list[str]:
        pad = "  " * indent
        icon = "✓" if s.status == "ok" else "✗"
        dur = f"{s.duration:.3f}s" if s.duration is not None else "—"
        err = f"  {s.error_type}" if s.error_type else ""
        meta = f"  {s.metadata}" if s.metadata else ""
        line = f"{pad}{s.step_id}. {s.name:<35} {dur:>8}  {icon}{err}{meta}"
        lines = [line]
        for child in s.children:
            lines.extend(self._format_step(child, indent + 1))
        return lines

    # ── Export ────────────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Return all completed runs and session context as a dict."""
        return {
            "context": self._context,
            "runs": [r.to_dict() for r in self._roots],
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


# ── Null profiler (disabled) ──────────────────────────────────────────────────


class NullProfiler:
    """Inert profiler used when PROFILER_ENABLED is not set.

    All methods are no-ops. The decorator returns the original function
    unchanged. Zero runtime overhead.
    """

    _null_step = _NullStep()

    @contextmanager
    def step(self, name: str) -> Generator[_NullStep, None, None]:
        yield self._null_step

    def measure(self, name: str, runs: int = 1) -> Callable[..., Any]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return func

        return decorator

    def set_context(self, **kwargs: Any) -> None:
        pass

    def reset(self) -> None:
        pass

    def to_dict(self) -> dict[str, Any]:
        return {}

    def to_json(self, indent: int = 2) -> str:
        return "{}"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _benchmark_stats(runs: int, durations: list[float]) -> dict[str, Any]:
    stats: dict[str, Any] = {"runs_planned": runs, "runs_completed": len(durations)}
    if durations:
        stats["mean_s"] = round(sum(durations) / len(durations), 6)
        stats["min_s"] = round(min(durations), 6)
        stats["max_s"] = round(max(durations), 6)
    return stats


# ── Singleton ─────────────────────────────────────────────────────────────────

profiler: Profiler | NullProfiler = Profiler() if _ENABLED else NullProfiler()

__all__ = ["profiler", "Profiler", "NullProfiler", "Step"]
