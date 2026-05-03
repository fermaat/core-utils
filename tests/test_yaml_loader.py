"""Unit tests for yaml_loader."""

import textwrap
from pathlib import Path

import pytest
from pydantic import BaseModel

from core_utils.yaml_loader import load_yaml_as, load_yaml_dir_as


class Cfg(BaseModel):
    name: str
    value: int


class Nested(BaseModel):
    inner: Cfg


class TestLoadYamlAs:
    def test_valid_yaml(self, tmp_path: Path) -> None:
        f = tmp_path / "cfg.yaml"
        f.write_text("name: hello\nvalue: 42\n")
        result = load_yaml_as(f, Cfg)
        assert result.name == "hello"
        assert result.value == 42

    def test_accepts_str_path(self, tmp_path: Path) -> None:
        f = tmp_path / "cfg.yaml"
        f.write_text("name: hi\nvalue: 1\n")
        result = load_yaml_as(str(f), Cfg)
        assert result.name == "hi"

    def test_invalid_yaml_syntax_raises_with_path(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.yaml"
        f.write_text("name: [unclosed\n")
        with pytest.raises(ValueError, match=str(f)):
            load_yaml_as(f, Cfg)

    def test_invalid_yaml_syntax_includes_line(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.yaml"
        f.write_text("name: [unclosed\n")
        with pytest.raises(ValueError, match=r":\d+:"):
            load_yaml_as(f, Cfg)

    def test_validation_error_raises_with_path(self, tmp_path: Path) -> None:
        f = tmp_path / "cfg.yaml"
        f.write_text("name: hello\nvalue: notanint\n")
        with pytest.raises(ValueError, match=str(f)):
            load_yaml_as(f, Cfg)

    def test_validation_error_includes_field_path(self, tmp_path: Path) -> None:
        f = tmp_path / "cfg.yaml"
        f.write_text("name: hello\nvalue: notanint\n")
        with pytest.raises(ValueError, match="value"):
            load_yaml_as(f, Cfg)

    def test_validation_error_includes_line_number(self, tmp_path: Path) -> None:
        f = tmp_path / "cfg.yaml"
        f.write_text("name: hello\nvalue: notanint\n")
        with pytest.raises(ValueError, match=r":\d+"):
            load_yaml_as(f, Cfg)

    def test_nested_validation_error_includes_field_path(self, tmp_path: Path) -> None:
        f = tmp_path / "nested.yaml"
        f.write_text(textwrap.dedent("""\
            inner:
              name: ok
              value: bad
        """))
        with pytest.raises(ValueError, match="inner"):
            load_yaml_as(f, Nested)


class TestLoadYamlDirAs:
    def test_loads_all_matching_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.yaml").write_text("name: a\nvalue: 1\n")
        (tmp_path / "b.yaml").write_text("name: b\nvalue: 2\n")
        results = load_yaml_dir_as(tmp_path, Cfg)
        assert len(results) == 2
        assert {r.name for r in results} == {"a", "b"}

    def test_returns_sorted_order(self, tmp_path: Path) -> None:
        (tmp_path / "z.yaml").write_text("name: z\nvalue: 3\n")
        (tmp_path / "a.yaml").write_text("name: a\nvalue: 1\n")
        results = load_yaml_dir_as(tmp_path, Cfg)
        assert results[0].name == "a"
        assert results[1].name == "z"

    def test_custom_glob(self, tmp_path: Path) -> None:
        (tmp_path / "a.yaml").write_text("name: a\nvalue: 1\n")
        (tmp_path / "b.yml").write_text("name: b\nvalue: 2\n")
        results = load_yaml_dir_as(tmp_path, Cfg, glob="*.yml")
        assert len(results) == 1
        assert results[0].name == "b"

    def test_empty_dir_returns_empty_list(self, tmp_path: Path) -> None:
        assert load_yaml_dir_as(tmp_path, Cfg) == []

    def test_fails_fast_on_first_invalid(self, tmp_path: Path) -> None:
        (tmp_path / "a.yaml").write_text("name: a\nvalue: bad\n")
        (tmp_path / "b.yaml").write_text("name: b\nvalue: 2\n")
        with pytest.raises(ValueError, match="a.yaml"):
            load_yaml_dir_as(tmp_path, Cfg)

    def test_accepts_str_dir(self, tmp_path: Path) -> None:
        (tmp_path / "x.yaml").write_text("name: x\nvalue: 9\n")
        results = load_yaml_dir_as(str(tmp_path), Cfg)
        assert len(results) == 1
