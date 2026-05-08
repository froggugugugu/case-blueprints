"""materials.py / data/materials/*.yaml のテスト。"""

from __future__ import annotations

import pytest

from case_blueprint import materials


EXPECTED_IDS = {"pla", "petg", "pla_plus", "tpu", "abs"}


def test_list_available_includes_standard_materials():
    available = set(materials.list_available())
    assert EXPECTED_IDS.issubset(available), f"missing: {EXPECTED_IDS - available}"


@pytest.mark.parametrize("mid", sorted(EXPECTED_IDS))
def test_load_returns_required_fields(mid: str):
    data = materials.load(mid)
    assert data["id"] == mid
    for required in ("display_name", "thermal", "mechanical", "shrinkage",
                     "environmental", "print_settings", "fit_clearance"):
        assert required in data, f"{mid} missing {required}"


@pytest.mark.parametrize("mid", sorted(EXPECTED_IDS))
def test_fit_clearance_ranges_well_ordered(mid: str):
    """min <= max かつ min >= 0 を全機構で保証。"""
    data = materials.load(mid)
    for mech in ("snap_fit", "hinge_pin", "magnet_pocket"):
        lo, hi = data["fit_clearance"][mech]
        assert 0 <= lo <= hi, f"{mid}/{mech}: [{lo}, {hi}] が不正"


def test_fit_clearance_range_api():
    lo, hi = materials.fit_clearance_range("pla", "snap_fit")
    assert lo == 0.15 and hi == 0.30


def test_check_fit_clearance_in_range():
    ok, msg = materials.check_fit_clearance("pla", "snap_fit", 0.20)
    assert ok
    assert "✅" in msg


def test_check_fit_clearance_out_of_range():
    ok, msg = materials.check_fit_clearance("pla", "snap_fit", 0.50)
    assert not ok
    assert "⚠" in msg
    assert "[0.15, 0.3]" in msg


def test_unknown_material_raises():
    with pytest.raises(materials.MaterialNotFound):
        materials.load("kryptonite")


def test_shrinkage_pct():
    assert materials.shrinkage_pct("pla") == 0.3
    assert materials.shrinkage_pct("abs") == 0.8


def test_outdoor_acceptable():
    assert not materials.is_outdoor_acceptable("pla")
    assert materials.is_outdoor_acceptable("petg")
    assert materials.is_outdoor_acceptable("abs")


def test_petg_has_higher_snap_fit_clearance_than_pla():
    """PETG は摩擦が大きいので snap_fit が PLA より大きめという pitfalls.md P5 規約。"""
    pla_min, _ = materials.fit_clearance_range("pla", "snap_fit")
    petg_min, _ = materials.fit_clearance_range("petg", "snap_fit")
    assert petg_min >= pla_min


# ===== slicer_recommendations =====


@pytest.mark.parametrize("mid", sorted(EXPECTED_IDS))
def test_slicer_recommendations_has_required_fields(mid: str):
    rec = materials.slicer_recommendations(mid)
    for key in ("material_id", "display_name", "nozzle_temp_c", "bed_temp_c",
                "enclosure_required", "layer_height_mm", "infill_pct",
                "print_speed_mm_s", "fan", "support_difficulty", "warnings"):
        assert key in rec, f"{mid} missing {key}"


def test_slicer_pla_typical_values():
    rec = materials.slicer_recommendations("pla")
    # PLA: nozzle 190-220 → recommended 205, first_layer 210
    assert rec["nozzle_temp_c"]["min"] == 190
    assert rec["nozzle_temp_c"]["recommended"] == 205
    assert rec["nozzle_temp_c"]["first_layer"] == 210
    # 0.20 mm は範囲内なのでそれが採用される
    assert rec["layer_height_mm"]["recommended"] == 0.20
    # ファン: PLA は full
    assert rec["fan"]["subsequent_pct"] == 100


def test_slicer_abs_warns_enclosure():
    rec = materials.slicer_recommendations("abs")
    assert rec["enclosure_required"] is True
    assert any("密閉" in w for w in rec["warnings"])


def test_slicer_abs_high_shrinkage_warning():
    rec = materials.slicer_recommendations("abs")
    assert any("線収縮率" in w or "反り" in w for w in rec["warnings"])


def test_slicer_pla_no_enclosure_warning():
    rec = materials.slicer_recommendations("pla")
    assert rec["enclosure_required"] is False
    assert not any("密閉" in w for w in rec["warnings"])


def test_slicer_tpu_low_stiffness_warning():
    rec = materials.slicer_recommendations("tpu")
    assert any("剛性が低い" in w for w in rec["warnings"])


def test_slicer_petg_high_shrinkage_warning():
    rec = materials.slicer_recommendations("petg")
    # 0.6% なので警告対象
    assert any("収縮率" in w or "反り" in w for w in rec["warnings"])
