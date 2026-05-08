"""スキーマ検証の smoke test。

jsonschema が無い環境でもスキップせずに「ロード成功」だけは確認する。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from case_blueprint import loader

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_object():
    obj = loader.load_object(FIXTURES / "sample-object.yaml")
    assert obj["id"] == "sample-device"
    assert obj["shape"] == "rectangular"
    assert obj["dimensions"]["width"] == 80.0


def test_load_case_spec():
    spec = loader.load_case_spec(FIXTURES / "sample-case-spec.yaml")
    assert spec["case"]["name"] == "sample-case"
    assert spec["case"]["closure"]["method"] == "snap_fit"
    assert len(spec["objects"]) == 1


def test_load_case_config():
    cfg = loader.load_case_config(FIXTURES / "sample-case-config.yaml")
    assert cfg["walls"]["thickness"] == 2.4
    assert cfg["lid"]["fit_clearance"] == 0.3


def test_load_project_config():
    pc = loader.load_project_config(FIXTURES / "sample-project-config.yaml")
    assert pc["project"]["name"] == "sample-project"
    assert pc["print_settings"]["printer_bed"] == [220, 220, 250]


def test_object_invalid_id_rejected():
    if not loader._HAS_JSONSCHEMA:
        pytest.skip("jsonschema 未インストール")
    bad = {
        "id": "Invalid ID With Space",  # pattern 違反
        "name": "x",
        "shape": "rectangular",
        "dimensions": {"width": 10, "depth": 10, "height": 10},
        "tolerance": 0.5,
    }
    import yaml
    tmp = FIXTURES / "_tmp_invalid.yaml"
    tmp.write_text(yaml.dump(bad))
    try:
        with pytest.raises(loader.ValidationError):
            loader.load_object(tmp)
    finally:
        tmp.unlink()


def test_object_negative_dimension_rejected():
    if not loader._HAS_JSONSCHEMA:
        pytest.skip("jsonschema 未インストール")
    bad = {
        "id": "neg-dim",
        "name": "x",
        "shape": "rectangular",
        "dimensions": {"width": -5, "depth": 10, "height": 10},
        "tolerance": 0.5,
    }
    import yaml
    tmp = FIXTURES / "_tmp_neg.yaml"
    tmp.write_text(yaml.dump(bad))
    try:
        with pytest.raises(loader.ValidationError):
            loader.load_object(tmp)
    finally:
        tmp.unlink()
