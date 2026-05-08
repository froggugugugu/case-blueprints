"""features/* の検証 + ジオメトリテスト。

純 Python validate ロジックは常時実行、CadQuery 依存の apply は
pytest.importorskip("cadquery") でスキップ可能。
"""

from __future__ import annotations

import pytest

from case_blueprint import features as _features  # noqa: F401  (副作用 import で register)
from case_blueprint.feature_registry import HANDLERS, apply_all
from case_blueprint.features import (
    cq_face_selector,
    normalize_side,
    ventilation,
    cable_port,
    display_window,
)


# ===== 共通: side 正規化 =====


class TestSideNormalization:
    @pytest.mark.parametrize("alias,axis", [
        ("+X", "+X"), ("-X", "-X"),
        ("top", "+Z"), ("bottom", "-Z"),
        ("front", "-Y"), ("back", "+Y"),
        ("left", "-X"), ("right", "+X"),
    ])
    def test_normalize(self, alias, axis):
        assert normalize_side(alias) == axis

    def test_unknown_side_raises(self):
        with pytest.raises(ValueError, match="未知の side"):
            normalize_side("forward")

    def test_cq_face_selector(self):
        assert cq_face_selector("+Z") == ">Z"
        assert cq_face_selector("top") == ">Z"
        assert cq_face_selector("front") == "<Y"


# ===== registry に乗っていることの確認 =====


class TestRegistry:
    @pytest.mark.parametrize("ftype", ["ventilation", "cable_port", "display_window"])
    def test_registered(self, ftype):
        assert ftype in HANDLERS


# ===== ventilation validate =====


class TestVentilationValidate:
    def test_side_required(self):
        with pytest.raises(AssertionError, match="side が必須"):
            ventilation.validate_ventilation({}, {})

    def test_density_range(self):
        with pytest.raises(AssertionError, match="density"):
            ventilation.validate_ventilation(
                {"side": "+Z", "density": 0.6}, {}
            )

    def test_pattern_unknown(self):
        with pytest.raises(AssertionError, match="pattern"):
            ventilation.validate_ventilation(
                {"side": "+Z", "pattern": "xyz"}, {}
            )

    def test_hole_too_large(self):
        with pytest.raises(AssertionError, match="ブリッジ困難"):
            ventilation.validate_ventilation(
                {"side": "+Z", "hole_diameter": 12}, {}
            )

    def test_valid(self):
        ventilation.validate_ventilation(
            {"side": "+Z", "pattern": "grid", "density": 0.3, "hole_diameter": 3.0}, {}
        )


# ===== cable_port validate =====


class TestCablePortValidate:
    def test_side_required(self):
        with pytest.raises(AssertionError, match="side が必須"):
            cable_port.validate_cable_port({"diameter": 8}, {})

    def test_diameter_xor_oblong(self):
        with pytest.raises(AssertionError, match="diameter と oblong"):
            cable_port.validate_cable_port(
                {"side": "+Y", "diameter": 8, "oblong": [10, 4]}, {}
            )
        with pytest.raises(AssertionError, match="diameter と oblong"):
            cable_port.validate_cable_port({"side": "+Y"}, {})

    def test_flange_requires_outer(self):
        with pytest.raises(AssertionError, match="flange_outer_diameter"):
            cable_port.validate_cable_port(
                {"side": "+Y", "diameter": 8, "flange": 1.5}, {}
            )

    def test_valid_diameter(self):
        cable_port.validate_cable_port({"side": "+Y", "diameter": 8.0}, {})

    def test_valid_oblong(self):
        cable_port.validate_cable_port({"side": "+Y", "oblong": [10, 4]}, {})

    def test_valid_with_flange(self):
        cable_port.validate_cable_port(
            {"side": "+Y", "diameter": 8.0, "flange": 1.5, "flange_outer_diameter": 14.0}, {}
        )


# ===== display_window validate =====


class TestDisplayWindowValidate:
    def test_size_required(self):
        with pytest.raises(AssertionError, match="size"):
            display_window.validate_display_window({"side": "+Z"}, {})

    def test_corner_radius_too_large(self):
        with pytest.raises(AssertionError, match="corner_radius"):
            display_window.validate_display_window(
                {"side": "+Z", "size": [40, 20], "corner_radius": 25}, {}
            )

    def test_bezel_requires_margin(self):
        with pytest.raises(AssertionError, match="margin"):
            display_window.validate_display_window(
                {"side": "+Z", "size": [40, 20], "bezel": {"depth": 1.0, "margin": 0}}, {}
            )

    def test_valid_with_bezel(self):
        display_window.validate_display_window(
            {"side": "+Z", "size": [40, 20], "corner_radius": 1.0,
             "bezel": {"depth": 1.0, "margin": 1.5}}, {}
        )


# ===== CadQuery 実体テスト(オプショナル)=====


cq = pytest.importorskip("cadquery")


@pytest.fixture
def box():
    """80 × 60 × 30 mm の箱(原点中心)"""
    return cq.Workplane("XY").box(80, 60, 30)


@pytest.fixture
def box_volume_initial():
    return 80 * 60 * 30


class TestVentilationGeometry:
    def test_grid_reduces_volume(self, box, box_volume_initial):
        result = apply_all(box, [
            {"type": "ventilation", "side": "+Z", "pattern": "grid",
             "density": 0.2, "hole_diameter": 3.0}
        ], {})
        v = result.val().Volume()
        assert v < box_volume_initial
        # 開口面積比 0.2 程度で、貫通深さ 30mm。理論上限は 0.2 * 80 * 60 * 30 = 28800
        assert (box_volume_initial - v) > 0


class TestCablePortGeometry:
    def test_diameter_cuts_through(self, box, box_volume_initial):
        result = apply_all(box, [
            {"type": "cable_port", "side": "+Y", "position": [0, 0],
             "diameter": 8.0}
        ], {})
        v = result.val().Volume()
        # 8mm 円が 60mm 貫通(Y 方向)
        # 削れた体積 ≒ π * 4^2 * 60 = 約 3015 mm³
        diff = box_volume_initial - v
        assert 2500 < diff < 3500

    def test_oblong_cuts_through(self, box):
        result = apply_all(box, [
            {"type": "cable_port", "side": "+X", "position": [0, 0],
             "oblong": [12, 4]}
        ], {})
        # 削れていることだけ確認
        assert result.val().Volume() < 80 * 60 * 30


class TestDisplayWindowGeometry:
    def test_window_cuts_through(self, box, box_volume_initial):
        result = apply_all(box, [
            {"type": "display_window", "side": "+Z", "size": [40, 20],
             "position": [0, 0]}
        ], {})
        v = result.val().Volume()
        # 40 * 20 が 30mm 貫通 = 24000
        diff = box_volume_initial - v
        assert 23500 < diff < 24500

    def test_bezel_creates_step(self, box, box_volume_initial):
        """ベゼル付きはベゼルなしより削れ量が多い。"""
        plain = apply_all(box, [
            {"type": "display_window", "side": "+Z", "size": [40, 20]}
        ], {}).val().Volume()
        with_bezel = apply_all(box, [
            {"type": "display_window", "side": "+Z", "size": [40, 20],
             "bezel": {"depth": 1.0, "margin": 1.5}}
        ], {}).val().Volume()
        assert with_bezel < plain
