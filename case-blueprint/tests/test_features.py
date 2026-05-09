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
    button_cutout,
    mounting_bracket,
    body_text,
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
    @pytest.mark.parametrize("ftype", [
        "ventilation", "cable_port", "display_window",
        "button_cutout", "mounting_bracket", "body_text",
    ])
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


# ===== button_cutout validate =====


class TestButtonCutoutValidate:
    def test_round_requires_diameter(self):
        with pytest.raises(AssertionError, match="diameter"):
            button_cutout.validate_button_cutout({"side": "+Z", "shape": "round"}, {})

    def test_square_requires_size(self):
        with pytest.raises(AssertionError, match="size"):
            button_cutout.validate_button_cutout({"side": "+Z", "shape": "square"}, {})

    def test_gloves_round_minimum(self):
        with pytest.raises(AssertionError, match="手袋越し"):
            button_cutout.validate_button_cutout(
                {"side": "+Z", "shape": "round", "diameter": 8.0,
                 "gloves_compatible": True}, {}
            )

    def test_gloves_round_pass(self):
        button_cutout.validate_button_cutout(
            {"side": "+Z", "shape": "round", "diameter": 14.0,
             "gloves_compatible": True}, {}
        )

    def test_gloves_square_short_side(self):
        with pytest.raises(AssertionError, match="手袋越し"):
            button_cutout.validate_button_cutout(
                {"side": "+Z", "shape": "square", "size": [20, 6],
                 "gloves_compatible": True}, {}
            )

    def test_rounded_square_corner_too_large(self):
        with pytest.raises(AssertionError, match="corner_radius"):
            button_cutout.validate_button_cutout(
                {"side": "+Z", "shape": "rounded_square", "size": [10, 10],
                 "corner_radius": 6}, {}
            )


# ===== mounting_bracket validate =====


class TestMountingBracketValidate:
    def test_style_required(self):
        with pytest.raises(AssertionError, match="style"):
            mounting_bracket.validate_mounting_bracket({}, {})

    def test_unknown_style(self):
        with pytest.raises(AssertionError, match="未登録"):
            mounting_bracket.validate_mounting_bracket(
                {"style": "weird_thing"}, {}
            )

    def test_m5_screw_holes_pattern(self):
        with pytest.raises(AssertionError, match="pattern"):
            mounting_bracket.validate_mounting_bracket(
                {"style": "m5_screw_holes", "side": "-Z", "pattern": "diamond"}, {}
            )

    def test_m5_screw_holes_counterbore(self):
        with pytest.raises(AssertionError, match="counterbore"):
            mounting_bracket.validate_mounting_bracket(
                {"style": "m5_screw_holes", "side": "-Z",
                 "diameter": 5.0, "counterbore": {"diameter": 4.0, "depth": 3}}, {}
            )

    def test_m5_screw_holes_valid(self):
        mounting_bracket.validate_mounting_bracket(
            {"style": "m5_screw_holes", "side": "-Z",
             "pattern": "square", "pitch": 38.1, "diameter": 5.0,
             "counterbore": {"diameter": 9.0, "depth": 3.0}}, {}
        )

    def test_ribs_target_required(self):
        with pytest.raises(AssertionError, match="target"):
            mounting_bracket.validate_mounting_bracket({"style": "ribs"}, {})

    def test_ram_ball_b_base_too_small(self):
        with pytest.raises(AssertionError, match="base_diameter"):
            mounting_bracket.validate_mounting_bracket(
                {"style": "ram_ball_b", "side": "-Z",
                 "base_diameter": 22.0, "base_thickness": 4.0}, {}
            )

    def test_ram_ball_b_base_too_thin(self):
        with pytest.raises(AssertionError, match="base_thickness"):
            mounting_bracket.validate_mounting_bracket(
                {"style": "ram_ball_b", "side": "-Z",
                 "base_diameter": 30.0, "base_thickness": 2.0}, {}
            )


class TestMountingBracketResolveTargets:
    """ribs style の target id → bbox 自動解決(#10)。"""
    def _obj(self, id_, w, d, h):
        return {"id": id_, "name": id_, "shape": "rectangular",
                "dimensions": {"width": w, "depth": d, "height": h}, "tolerance": 0}

    def test_resolves_target_to_computed_bbox(self):
        objs = [self._obj("pi-main", 85, 56, 18)]
        feats = [{"type": "mounting_bracket", "style": "ribs",
                  "target": "pi-main", "height": 5.0, "width": 3.0}]
        out = mounting_bracket.resolve_targets(feats, objs)
        bb = out[0]["computed"]["target_bbox"]
        assert bb == {"width": 85.0, "depth": 56.0, "height": 18.0}

    def test_unknown_target_skipped(self):
        feats = [{"type": "mounting_bracket", "style": "ribs",
                  "target": "ghost", "height": 5.0}]
        out = mounting_bracket.resolve_targets(feats, [])
        assert "computed" not in out[0]

    def test_manual_length_takes_priority(self):
        """手動 length が指定されていれば computed は付与しない(後方互換)"""
        objs = [self._obj("x", 100, 80, 20)]
        feats = [{"type": "mounting_bracket", "style": "ribs",
                  "target": "x", "length": 50.0}]
        out = mounting_bracket.resolve_targets(feats, objs)
        assert "computed" not in out[0]

    def test_non_ribs_skipped(self):
        objs = [self._obj("x", 100, 80, 20)]
        feats = [{"type": "mounting_bracket", "style": "m5_screw_holes",
                  "target": "x", "side": "-Z"}]
        out = mounting_bracket.resolve_targets(feats, objs)
        assert "computed" not in out[0]

    def test_already_computed_not_overwritten(self):
        objs = [self._obj("x", 100, 80, 20)]
        feats = [{"type": "mounting_bracket", "style": "ribs",
                  "target": "x",
                  "computed": {"target_bbox": {"width": 999, "depth": 999, "height": 999}}}]
        out = mounting_bracket.resolve_targets(feats, objs)
        assert out[0]["computed"]["target_bbox"]["width"] == 999


# ===== body_text validate =====


class TestBodyTextValidate:
    def test_text_required(self):
        with pytest.raises(AssertionError, match="text が空"):
            body_text.validate_body_text(
                {"side": "+Z", "text": "", "font_file": "x.ttf"}, {}
            )

    def test_font_file_required(self):
        with pytest.raises(AssertionError, match="font_file"):
            body_text.validate_body_text(
                {"side": "+Z", "text": "HELLO"}, {}
            )

    def test_emboss_depth_zero(self):
        with pytest.raises(AssertionError, match="emboss_depth"):
            body_text.validate_body_text(
                {"side": "+Z", "text": "X", "font_file": "x.ttf",
                 "emboss_depth": 0.0}, {}
            )

    def test_emboss_depth_too_thin(self):
        with pytest.raises(AssertionError, match="0.4mm"):
            body_text.validate_body_text(
                {"side": "+Z", "text": "X", "font_file": "x.ttf",
                 "emboss_depth": 0.2}, {}
            )

    def test_font_file_missing(self, tmp_path):
        with pytest.raises(AssertionError, match="フォント"):
            body_text.validate_body_text(
                {"side": "+Z", "text": "HELLO", "font_file": "nonexistent.ttf"},
                {},
                font_dir=str(tmp_path),
            )

    def test_font_file_present(self, tmp_path):
        f = tmp_path / "fake.ttf"
        f.write_bytes(b"fakefont")
        body_text.validate_body_text(
            {"side": "+Z", "text": "HELLO", "font_file": "fake.ttf",
             "emboss_depth": 0.6, "size": 8.0},
            {},
            font_dir=str(tmp_path),
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


class TestButtonCutoutGeometry:
    def test_round_cuts_through(self, box, box_volume_initial):
        result = apply_all(box, [
            {"type": "button_cutout", "side": "+Z", "shape": "round",
             "diameter": 14.0, "position": [0, -10]}
        ], {})
        diff = box_volume_initial - result.val().Volume()
        # π * 7^2 * 30 = 約 4618
        assert 4400 < diff < 4800

    def test_rounded_square_cuts(self, box, box_volume_initial):
        result = apply_all(box, [
            {"type": "button_cutout", "side": "+Z", "shape": "rounded_square",
             "size": [16, 10], "corner_radius": 1.5}
        ], {})
        # 16 * 10 - 角 R 控除 ≒ 158 程度の sketch 面積、深さ 30
        diff = box_volume_initial - result.val().Volume()
        assert 4500 < diff < 4900


class TestMountingBracketGeometry:
    def test_m5_screw_holes_4_points(self, box, box_volume_initial):
        result = apply_all(box, [
            {"type": "mounting_bracket", "style": "m5_screw_holes",
             "side": "-Z", "pattern": "square", "pitch": 30.0, "diameter": 5.0}
        ], {})
        # M5 (φ5) × 4 点が貫通(深さ 30)。π * 2.5^2 * 30 * 4 = 約 2356
        diff = box_volume_initial - result.val().Volume()
        assert 2200 < diff < 2500

    def test_ram_ball_b_adds_disk(self, box, box_volume_initial):
        result = apply_all(box, [
            {"type": "mounting_bracket", "style": "ram_ball_b",
             "side": "-Z", "base_diameter": 30.0, "base_thickness": 4.0,
             "pitch": 38.1, "screw_diameter": 5.0}
        ], {})
        # 円盤を貼って 4 穴を開ける。元体積より大きいはず(円盤の追加 > 4 穴の控除)
        v = result.val().Volume()
        assert v > box_volume_initial

    def test_ribs_built_from_resolved_target_bbox(self, box, box_volume_initial):
        """target → bbox 自動解決経由でも ribs が生成される。

        box は原点中心 80×60×30。base_z=15(box の zmax)を指定し、
        リブを上に立てて box 体積より増えることで union の発生を確認。
        """
        feats = [{"type": "mounting_bracket", "style": "ribs",
                  "target": "device", "height": 4.0, "width": 2.0,
                  "base_z": 15.0}]
        objs = [{"id": "device", "shape": "rectangular",
                 "dimensions": {"width": 40, "depth": 30, "height": 10},
                 "tolerance": 0}]
        feats = mounting_bracket.resolve_targets(feats, objs)
        # computed.target_bbox が詰まっていることを直接確認(自動解決の証拠)
        assert feats[0]["computed"]["target_bbox"]["width"] == 40.0
        result = apply_all(box, feats, {})
        # 4 リブが box の上に立つので volume が増える(2 × 2 × 4 × 4 リブ = 64 mm³)
        assert result.val().Volume() > box_volume_initial
