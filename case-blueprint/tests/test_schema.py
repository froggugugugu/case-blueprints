"""スキーマ検証の smoke test。

jsonschema が無い環境でもスキップせずに「ロード成功」だけは確認する。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from case_blueprint import loader

FIXTURES = Path(__file__).parent / "fixtures"
EXAMPLES = Path(__file__).parent.parent / "examples"


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


def test_examples_minimal_loads_clean():
    """examples/minimal/ の入力一式がスキーマ検証を通ることを保証。

    setup.sh で展開された利用者プロジェクトで `cp -R examples/minimal/input/. input/`
    した直後に /design が走る前提。ここが壊れると最小サンプルが動かなくなる。
    """
    obj = loader.load_object(EXAMPLES / "minimal/input/objects/business-cards.yaml")
    assert obj["id"] == "business-cards"
    assert obj["dimensions"]["width"] == 91.0

    spec = loader.load_case_spec(EXAMPLES / "minimal/input/requirements/case-spec.yaml")
    assert spec["case"]["closure"]["method"] == "snap_fit"
    assert spec["case"]["closure"]["lid_axis"] == "+Z"
    assert spec["case"]["layout"]["arrangement"] in ("stacked", "side_by_side")

    cfg = loader.load_case_config(EXAMPLES / "minimal/input/design-params/case-config.yaml")
    assert cfg["lid"]["fit_clearance"] > 0


def test_examples_bike_navi_mvp_loads_clean():
    """examples/bike-navi-mvp/ の入力一式が schema を通ること + features 7 種を含む。"""
    obj = loader.load_object(EXAMPLES / "bike-navi-mvp/input/objects/bike-navi-stack.yaml")
    assert obj["id"] == "bike-navi-stack"
    assert obj["thermal"]["requires_ventilation"] is True
    assert "+X" in obj["orientation_hint"]["forbidden_bottoms"]

    spec = loader.load_case_spec(
        EXAMPLES / "bike-navi-mvp/input/requirements/case-spec.yaml"
    )
    assert spec["case"]["closure"]["method"] == "screws"
    types = [f["type"] for f in spec["case"]["features"]]
    assert "display_window" in types
    assert "cable_port" in types
    assert "button_cutout" in types
    assert "ventilation" in types
    assert "mounting_bracket" in types
    assert "body_text" in types
    # cable_port は 2 つ(USB-C と GPS)
    assert types.count("cable_port") == 2
    # button_cutout は 2 つ
    assert types.count("button_cutout") == 2

    cfg = loader.load_case_config(
        EXAMPLES / "bike-navi-mvp/input/design-params/case-config.yaml"
    )
    assert cfg["closure"]["screws"]["count"] == 6  # P19 振動冗長
    assert cfg["lid"]["gasket_groove"]["depth"] == 1.5  # P18 防水ガスケット


def test_examples_bike_navi_features_validate():
    """各 features が src 側の validate を通ることを確認(font 以外)。"""
    from case_blueprint.features import (
        ventilation, cable_port, display_window, button_cutout, mounting_bracket,
    )
    spec = loader.load_case_spec(
        EXAMPLES / "bike-navi-mvp/input/requirements/case-spec.yaml"
    )
    cfg = loader.load_case_config(
        EXAMPLES / "bike-navi-mvp/input/design-params/case-config.yaml"
    )
    by_type = {}
    for f in spec["case"]["features"]:
        by_type.setdefault(f["type"], []).append(f)

    for f in by_type.get("ventilation", []):
        ventilation.validate_ventilation(f, cfg)
    for f in by_type.get("cable_port", []):
        cable_port.validate_cable_port(f, cfg)
    for f in by_type.get("display_window", []):
        display_window.validate_display_window(f, cfg)
    for f in by_type.get("button_cutout", []):
        button_cutout.validate_button_cutout(f, cfg)
    for f in by_type.get("mounting_bracket", []):
        mounting_bracket.validate_mounting_bracket(f, cfg)
    # body_text はフォントが無いとアサート失敗するので validate を直接呼ばない


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
