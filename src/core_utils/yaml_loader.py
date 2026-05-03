"""YAML loading with pydantic validation and structured error messages."""

from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


def _yaml_line_for_loc(node: yaml.Node, loc: tuple[object, ...]) -> int | None:
    """Walk a composed YAML node tree to find the 1-indexed start line of a loc path."""
    current: yaml.Node = node
    for key in loc:
        if isinstance(current, yaml.MappingNode):
            for k, v in current.value:
                if isinstance(k, yaml.ScalarNode) and k.value == str(key):
                    current = v
                    break
            else:
                return None
        elif isinstance(current, yaml.SequenceNode):
            if isinstance(key, int) and key < len(current.value):
                current = current.value[key]
            else:
                return None
        else:
            return None
    return int(current.start_mark.line) + 1


def load_yaml_as(path: Path | str, model: type[T]) -> T:
    """Load a YAML file and validate it into a pydantic model.

    Raises ValueError with file path and line number on parse or validation failure.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")

    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        location = f"{path}:{mark.line + 1}:{mark.column + 1}" if mark else str(path)
        raise ValueError(
            f"{location}: YAML parse error — {exc.problem if hasattr(exc, 'problem') else exc}"
        ) from exc

    try:
        return model.model_validate(raw)
    except ValidationError as exc:
        try:
            root_node = yaml.compose(text)
        except Exception:
            root_node = None

        lines: list[str] = [f"{path}: validation failed"]
        for err in exc.errors():
            loc = err["loc"]
            line_num = _yaml_line_for_loc(root_node, loc) if root_node is not None else None
            field_path = " → ".join(str(l) for l in loc)
            location = f"{path}:{line_num}" if line_num is not None else str(path)
            lines.append(f"  {location}: {field_path}: {err['msg']}")

        raise ValueError("\n".join(lines)) from exc


def load_yaml_dir_as(dir: Path | str, model: type[T], glob: str = "*.yaml") -> list[T]:
    """Load all YAML files matching glob in dir and validate each into model.

    Raises on the first file that fails; files are processed in sorted order.
    """
    return [load_yaml_as(p, model) for p in sorted(Path(dir).glob(glob))]
