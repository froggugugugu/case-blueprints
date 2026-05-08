"""YAML loader + JSON-Schema 検証。

constitution §1: input/ は人間管理。loader は読み取りのみ、書き換えない。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

try:
    import jsonschema
    _HAS_JSONSCHEMA = True
except ImportError:
    _HAS_JSONSCHEMA = False


SCHEMA_DIR = Path(__file__).resolve().parent.parent.parent / "schemas"


class ValidationError(Exception):
    """スキーマ違反"""


def _load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_schema(name: str) -> dict[str, Any]:
    schema_path = SCHEMA_DIR / f"{name}.schema.yaml"
    if not schema_path.exists():
        raise FileNotFoundError(f"スキーマが見つかりません: {schema_path}")
    return _load_yaml(schema_path)


def _validate(data: Any, schema_name: str) -> None:
    if not _HAS_JSONSCHEMA:
        return
    schema = _load_schema(schema_name)
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as e:
        raise ValidationError(
            f"{schema_name} 違反: {e.message} (path: {'/'.join(map(str, e.absolute_path)) or '<root>'})"
        ) from e


def load_object(path: str | Path) -> dict[str, Any]:
    """input/objects/<id>.yaml を読む"""
    data = _load_yaml(Path(path))
    _validate(data, "object")
    return data


def load_objects(objects_dir: str | Path = "input/objects") -> list[dict[str, Any]]:
    """input/objects/*.yaml を全件読む(.gitkeep 等は除外)"""
    paths = sorted(Path(objects_dir).glob("*.yaml"))
    return [load_object(p) for p in paths]


def load_case_spec(path: str | Path = "input/requirements/case-spec.yaml") -> dict[str, Any]:
    data = _load_yaml(Path(path))
    _validate(data, "case-spec")
    return data


def load_case_config(path: str | Path = "input/design-params/case-config.yaml") -> dict[str, Any]:
    data = _load_yaml(Path(path))
    _validate(data, "case-config")
    return data


def load_project_config(path: str | Path = "project-config.yaml") -> dict[str, Any]:
    data = _load_yaml(Path(path))
    _validate(data, "project-config")
    return data


def load_all(root: str | Path = ".") -> dict[str, Any]:
    """4 種を一括ロードして辞書で返す"""
    root = Path(root)
    return {
        "project": load_project_config(root / "project-config.yaml"),
        "case_spec": load_case_spec(root / "input/requirements/case-spec.yaml"),
        "case_config": load_case_config(root / "input/design-params/case-config.yaml"),
        "objects": load_objects(root / "input/objects"),
    }
