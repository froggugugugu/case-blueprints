"""closures/* のジオメトリ・検証テスト。

純 Python ロジック(validate / plan_knuckle_chain / corner_positions)は
cadquery 非依存で常時実行。実ジオメトリは pytest.importorskip("cadquery") で
cadquery が無い環境ではスキップ。
"""

from __future__ import annotations

import pytest

from case_blueprint.closures import (
    snap_fit,
    screws,
    magnetic,
    hinge_lever,
    snap_lip_with_hinge,
)


# ===== 純 Python 検証ロジック =====


class TestSnapFitValidate:
    def test_fit_clearance_must_be_positive(self):
        with pytest.raises(AssertionError, match="fit_clearance"):
            snap_fit.validate_snap_fit({"lid": {"fit_clearance": 0, "lip_height": 3}})

    def test_lip_height_minimum(self):
        with pytest.raises(AssertionError, match="lip_height"):
            snap_fit.validate_snap_fit({"lid": {"fit_clearance": 0.2, "lip_height": 0.5}})

    def test_valid_config_passes(self):
        snap_fit.validate_snap_fit({"lid": {"fit_clearance": 0.2, "lip_height": 3.0}})


class TestScrewsValidate:
    def test_count_minimum(self):
        with pytest.raises(AssertionError, match="count"):
            screws.validate_screws(
                {"closure": {"screws": {"count": 1}}},
                {"closure": {"fastener": {"diameter": 3}}},
            )

    def test_boss_wall_thickness(self):
        # boss_outer_d=4, pilot_d=2.55(M3 default 0.85x): wall = (4-2.55)/2 = 0.725 < 1.5
        with pytest.raises(AssertionError, match="ボス肉厚"):
            screws.validate_screws(
                {"closure": {"screws": {
                    "count": 4, "boss_outer_diameter": 4.0, "pilot_diameter": 2.55,
                }}},
                {"closure": {"fastener": {"diameter": 3.0}}},
            )

    def test_positions_count_mismatch(self):
        with pytest.raises(AssertionError, match="positions 数"):
            screws.validate_screws(
                {"closure": {"screws": {
                    "count": 4, "positions": [[0, 0], [1, 1]],
                    "boss_outer_diameter": 6.0, "pilot_diameter": 2.55,
                }}},
                {"closure": {"fastener": {"diameter": 3.0}}},
            )

    def test_valid_passes(self):
        screws.validate_screws(
            {"closure": {"screws": {
                "count": 4, "boss_outer_diameter": 6.0, "pilot_diameter": 2.55,
            }}},
            {"closure": {"fastener": {"diameter": 3.0}}},
        )


class TestScrewsCornerPositions:
    def test_count_2_diagonal(self):
        pos = screws.corner_positions(100, 60, 5, 2)
        assert pos == [(-45.0, -25.0), (45.0, 25.0)]

    def test_count_4_corners(self):
        pos = screws.corner_positions(100, 60, 5, 4)
        assert len(pos) == 4
        # 4 隅は ±45, ±25
        xs = sorted(set(p[0] for p in pos))
        ys = sorted(set(p[1] for p in pos))
        assert xs == [-45.0, 45.0]
        assert ys == [-25.0, 25.0]

    def test_count_6(self):
        pos = screws.corner_positions(100, 60, 5, 6)
        assert len(pos) == 6
        # 中央2本(y=0)を含む
        assert (-45.0, 0.0) in pos
        assert (45.0, 0.0) in pos

    def test_inset_too_large_raises(self):
        with pytest.raises(ValueError, match="inset"):
            screws.corner_positions(20, 10, 15, 4)

    def test_unsupported_count(self):
        with pytest.raises(ValueError, match="2/4/6"):
            screws.corner_positions(100, 60, 5, 3)


class TestMagneticValidate:
    def test_pocket_depth_vs_magnet_thickness(self):
        with pytest.raises(AssertionError, match="pocket_depth"):
            magnetic.validate_magnetic(
                {"closure": {"magnetic": {
                    "count": 4, "pocket_depth": 3.0, "air_gap": 0.15,
                }}},
                {"closure": {"magnet": {"thickness": 3.0}}},
            )

    def test_air_gap_range(self):
        with pytest.raises(AssertionError, match="air_gap"):
            magnetic.validate_magnetic(
                {"closure": {"magnetic": {
                    "count": 4, "pocket_depth": 3.5, "air_gap": 0.5,
                }}},
                {"closure": {"magnet": {"thickness": 3.0}}},
            )

    def test_count_minimum(self):
        with pytest.raises(AssertionError, match="count"):
            magnetic.validate_magnetic(
                {"closure": {"magnetic": {
                    "count": 1, "pocket_depth": 3.5, "air_gap": 0.15,
                }}},
                {"closure": {"magnet": {"thickness": 3.0}}},
            )


class TestPlanKnuckleChain:
    def test_basic_3_knuckle(self):
        slots = hinge_lever.plan_knuckle_chain(
            total_length=30.0,
            pattern=["body", "lid", "body"],
            z_clearance=0.4,
        )
        assert len(slots) == 3
        assert slots[0].owner == "body"
        assert slots[1].owner == "lid"
        # 全長 = end_clear*2 + n*knuckle + (n-1)*gap = 0.8 + 3K + 0.8 = 30 → K = 28.4/3 ≈ 9.467
        assert slots[0].length == pytest.approx(28.4 / 3, rel=1e-3)
        # 隙間チェック: slot[0].axis_end + 0.4 == slot[1].axis_start
        assert slots[1].axis_start == pytest.approx(slots[0].axis_end + 0.4, rel=1e-6)

    def test_too_short_raises(self):
        with pytest.raises(ValueError, match="ナックル長"):
            hinge_lever.plan_knuckle_chain(
                total_length=2.0,
                pattern=["body", "lid", "body"],
                z_clearance=0.4,
            )

    def test_invalid_owner_raises(self):
        with pytest.raises(ValueError, match="pattern 要素"):
            hinge_lever.plan_knuckle_chain(
                total_length=30.0,
                pattern=["body", "wrong"],
                z_clearance=0.4,
            )

    def test_min_length_pattern(self):
        with pytest.raises(ValueError, match="2 個以上"):
            hinge_lever.plan_knuckle_chain(
                total_length=30.0,
                pattern=["body"],
                z_clearance=0.4,
            )

    def test_axis_origin_offset(self):
        slots = hinge_lever.plan_knuckle_chain(
            total_length=10.0,
            pattern=["body", "lid"],
            z_clearance=0.4,
            axis_origin=100.0,
        )
        assert slots[0].axis_start >= 100.4


class TestScaleConstraints:
    def test_pin_length_too_short(self):
        # pattern=5, z=0.4, pin=12: thickness=(12-0.8-4*0.4)/5=1.92mm<2.0 → P17 検出
        with pytest.raises(AssertionError, match="P17"):
            hinge_lever.validate_scale_constraints(
                {"knuckle": {"pattern": ["body", "lid", "body", "lid", "body"], "z_clearance": 0.4}},
                {"hinge": {"fastener": {"length": 12.0}}},
            )

    def test_skip_when_no_hardware(self):
        # pin_length=0 ならスキップ
        hinge_lever.validate_scale_constraints(
            {"knuckle": {"pattern": ["body", "lid", "body"]}},
            {},
        )

    def test_valid_passes(self):
        hinge_lever.validate_scale_constraints(
            {"knuckle": {"pattern": ["body", "lid", "body"], "z_clearance": 0.4}},
            {"hinge": {"fastener": {"length": 28.0}}},
        )


class TestSnapLipWithHingeValidate:
    def test_extra_clearance_minimum(self):
        with pytest.raises(AssertionError, match="P14"):
            snap_lip_with_hinge.validate_snap_lip_with_hinge(
                {"lid": {"fit_clearance": 0.2, "lip_hinge_side_extra_clearance": 0.1},
                 "hinge": {"knuckle": {"pattern": ["body", "lid", "body"]}}},
                {},
            )

    def test_valid_passes(self):
        snap_lip_with_hinge.validate_snap_lip_with_hinge(
            {"lid": {"fit_clearance": 0.2, "lip_hinge_side_extra_clearance": 1.1},
             "hinge": {"knuckle": {"pattern": ["body", "lid", "body"]}}},
            {},
        )


# ===== ジオメトリ実行(cadquery 必須)=====

try:
    import cadquery as cq  # noqa: F401
    HAS_CADQUERY = True
except ImportError:
    HAS_CADQUERY = False

requires_cadquery = pytest.mark.skipif(not HAS_CADQUERY, reason="cadquery 未インストール")


def _make_body(*, x=80.0, y=50.0, z=20.0, wall_t=2.4, bottom_t=2.4):
    """テスト用: 上面開放のシェル。中心は原点、底面 z=0。"""
    import cadquery as cq
    return (
        cq.Workplane("XY")
        .box(x, y, z, centered=(True, True, False))
        .faces(">Z")
        .shell(-wall_t)
    )


def _make_lid(*, x=80.0, y=50.0, z=3.0):
    """テスト用: 単純な板。中心は原点、底面 z=0。"""
    import cadquery as cq
    return cq.Workplane("XY").box(x, y, z, centered=(True, True, False))


def _bbox(part):
    return part.val().BoundingBox()


@requires_cadquery
class TestSnapFitGeometry:
    def test_lip_increases_lid_volume(self):
        lid = _make_lid()
        v0 = lid.val().Volume()
        lid2 = snap_fit.build_lip(
            lid,
            lid_cfg={"lip_height": 3.0, "fit_clearance": 0.2},
            walls_cfg={"thickness": 2.4},
        )
        assert lid2.val().Volume() > v0

    def test_lip_extends_below_lid(self):
        lid = _make_lid(z=3.0)
        bb_before = _bbox(lid)
        lid2 = snap_fit.build_lip(
            lid,
            lid_cfg={"lip_height": 3.0, "fit_clearance": 0.2},
            walls_cfg={"thickness": 2.4},
        )
        bb_after = _bbox(lid2)
        # リップは下に伸びるので zmin が小さくなる
        assert bb_after.zmin < bb_before.zmin
        assert bb_after.zmin == pytest.approx(bb_before.zmin - 3.0, rel=1e-3)

    def test_groove_chamfer_no_op_when_disabled(self):
        body = _make_body()
        body2 = snap_fit.build_lip_groove(
            body,
            lid_cfg={"lip_height": 3.0, "fit_clearance": 0.2},
            walls_cfg={"thickness": 2.4},
        )
        assert body2.val().Volume() == pytest.approx(body.val().Volume(), rel=1e-9)

    def test_full_closure_returns_2_parts(self):
        body = _make_body()
        lid = _make_lid()
        result = snap_fit.build_snap_fit_closure(
            body, lid,
            case_spec={},
            case_config={
                "walls": {"thickness": 2.4},
                "lid": {"fit_clearance": 0.2, "lip_height": 3.0},
            },
        )
        assert set(result.keys()) == {"case-body", "case-lid"}


@requires_cadquery
class TestScrewsGeometry:
    def test_bosses_increase_body_volume(self):
        body = _make_body()
        v0 = body.val().Volume()
        body2 = screws.build_screw_bosses(
            body,
            closure_cfg={"count": 4, "boss_outer_diameter": 6.0, "pilot_diameter": 2.55},
            hardware={"closure": {"fastener": {"diameter": 3.0, "length": 8.0}}},
        )
        assert body2.val().Volume() > v0

    def test_lid_holes_decrease_volume(self):
        lid = _make_lid(z=3.0)
        v0 = lid.val().Volume()
        lid2 = screws.build_screw_holes(
            lid,
            closure_cfg={
                "count": 4,
                "boss_outer_diameter": 6.0,
                "countersink": {"enabled": True, "top_diameter": 6.0, "depth": 1.8},
            },
            hardware={"closure": {"fastener": {"diameter": 3.0, "head_diameter": 5.6, "head_height": 1.86}}},
        )
        assert lid2.val().Volume() < v0


@requires_cadquery
class TestMagneticGeometry:
    def test_lid_pockets_decrease_volume(self):
        lid = _make_lid(z=4.0)
        v0 = lid.val().Volume()
        lid2 = magnetic.build_magnet_pockets_lid(
            lid,
            closure_cfg={"count": 4, "pocket_depth": 3.2},
            hardware={"closure": {"magnet": {"outer_diameter": 6.0, "thickness": 3.0}}},
        )
        assert lid2.val().Volume() < v0

    def test_lid_too_thin_raises(self):
        lid = _make_lid(z=2.0)
        with pytest.raises(ValueError, match="蓋肉厚"):
            magnetic.build_magnet_pockets_lid(
                lid,
                closure_cfg={"count": 4, "pocket_depth": 3.2},
                hardware={"closure": {"magnet": {"outer_diameter": 6.0, "thickness": 3.0}}},
            )

    def test_body_bosses_increase_volume(self):
        body = _make_body(z=20.0)
        v0 = body.val().Volume()
        body2 = magnetic.build_steel_plate_pockets_body(
            body,
            closure_cfg={
                "count": 4, "air_gap": 0.15, "plate_pocket_depth": 1.2,
                "boss_outer_diameter": 9.0, "boss_height": 14.0,
            },
            walls_cfg={"thickness": 2.4, "bottom_thickness": 2.4},
            hardware={"closure": {"counter_plate": {"outer_diameter": 6.0, "thickness": 1.0}}},
        )
        assert body2.val().Volume() > v0


@requires_cadquery
class TestHingePrimitivesGeometry:
    def test_make_knuckle_volume_positive(self):
        k = hinge_lever.make_knuckle(
            outer_diameter=6.0, pin_diameter=2.0, length=10.0,
        )
        assert k.val().Volume() > 0

    def test_make_knuckle_pin_too_thick_raises(self):
        with pytest.raises(ValueError, match="ナックル肉厚不足"):
            hinge_lever.make_knuckle(
                outer_diameter=2.5, pin_diameter=2.0, length=10.0,
            )

    def test_attach_chain_unions_to_parts(self):
        body = _make_body()
        lid = _make_lid()
        v_body0 = body.val().Volume()
        v_lid0 = lid.val().Volume()
        slots = hinge_lever.plan_knuckle_chain(
            total_length=30.0,
            pattern=["body", "lid", "body"],
            z_clearance=0.4,
        )
        body2, lid2 = hinge_lever.attach_knuckle_chain(
            body, lid,
            slots=slots,
            knuckle_outer_diameter=6.0,
            pin_diameter=2.0,
            hinge_axis_y=-25.0,  # body の -Y 外面付近
            hinge_axis_z=20.0,
        )
        assert body2.val().Volume() > v_body0
        assert lid2.val().Volume() > v_lid0


@requires_cadquery
class TestLatchLeverGeometry:
    def test_lever_volume_positive(self):
        lever = hinge_lever.make_latch_lever(
            length=20.0, width=8.0, thickness=3.0,
            pivot_hole_diameter=2.0, pivot_offset_from_top=3.0,
            hook_hole_diameter=2.0, hook_offset_from_bottom=3.0,
        )
        assert lever.val().Volume() > 0
        # 元の板 = 20*8*3 = 480。ピン穴 + フック開口で減るはず
        assert lever.val().Volume() < 20 * 8 * 3
