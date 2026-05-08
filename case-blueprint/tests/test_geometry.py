from __future__ import annotations

import pytest

from case_blueprint import geometry


def _obj(width=10.0, depth=10.0, height=10.0, tol=0.5, shape="rectangular"):
    return {
        "id": "x",
        "name": "x",
        "shape": shape,
        "dimensions": {"width": width, "depth": depth, "height": height},
        "tolerance": tol,
    }


def test_object_bbox_rectangular_includes_tolerance():
    bb = geometry.object_bbox(_obj(width=10, depth=10, height=10, tol=0.5))
    assert bb.width == 11.0
    assert bb.depth == 11.0
    assert bb.height == 11.0


def test_object_bbox_cylindrical():
    obj = {
        "id": "c",
        "name": "c",
        "shape": "cylindrical",
        "dimensions": {"diameter": 20.0, "height": 30.0},
        "tolerance": 1.0,
    }
    bb = geometry.object_bbox(obj)
    assert bb.width == 22.0
    assert bb.depth == 22.0
    assert bb.height == 32.0


def test_internal_bbox_stacked():
    objs = [_obj(10, 10, 10, 0), _obj(20, 20, 5, 0)]
    bb = geometry.internal_bbox_stacked(objs, object_clearance=1.0)
    assert bb.width == 22.0   # max(10,20) + 2*1.0
    assert bb.depth == 22.0
    assert bb.height == 17.0  # 10 + 5 + 2*1.0


def test_external_bbox():
    internal = geometry.BoundingBox(width=20, depth=20, height=20)
    ext = geometry.external_bbox(internal, wall_thickness=2.0)
    assert ext.width == 24.0
    assert ext.depth == 24.0
    assert ext.height == 24.0


def test_fits_in_bed_pass():
    ext = geometry.BoundingBox(width=200, depth=200, height=200)
    assert geometry.fits_in_bed(ext, [220, 220, 250])


def test_fits_in_bed_fail():
    ext = geometry.BoundingBox(width=300, depth=200, height=200)
    assert not geometry.fits_in_bed(ext, [220, 220, 250])


def test_fits_in_bed_orientation_aware():
    """長軸を bed 長辺に揃えれば収まる(辺長ソートで判定)"""
    ext = geometry.BoundingBox(width=240, depth=100, height=100)  # 長軸 240
    assert geometry.fits_in_bed(ext, [250, 220, 220])  # bed 長辺 250


# ===== 3D 配置(layout=manual)+ 干渉検出 =====


def _named(id_, **kwargs):
    o = _obj(**kwargs)
    o["id"] = id_
    o["name"] = id_
    return o


def test_detect_collisions_no_overlap():
    """十分離れた position なら衝突なし"""
    objects = [_named("a", width=10, depth=10, height=10, tol=0),
               _named("b", width=10, depth=10, height=10, tol=0)]
    placements = [
        {"id": "a", "position": [0, 0, 0]},
        {"id": "b", "position": [20, 0, 0]},   # X 方向に 20mm 離す
    ]
    assert geometry.detect_collisions(objects, placements) == []


def test_detect_collisions_overlap_detected():
    objects = [_named("a", width=10, depth=10, height=10, tol=0),
               _named("b", width=10, depth=10, height=10, tol=0)]
    placements = [
        {"id": "a", "position": [0, 0, 0]},
        {"id": "b", "position": [5, 0, 0]},    # 半分重なる
    ]
    pairs = geometry.detect_collisions(objects, placements)
    assert pairs == [("a", "b")]


def test_detect_collisions_3d_z_separation():
    """X-Y は重なるが Z で離れていれば衝突なし(縦積み配置の確認)"""
    objects = [_named("a", width=10, depth=10, height=10, tol=0),
               _named("b", width=10, depth=10, height=10, tol=0)]
    placements = [
        {"id": "a", "position": [0, 0, 0]},
        {"id": "b", "position": [0, 0, 11]},   # Z 方向に 11mm = 隙間 1mm
    ]
    assert geometry.detect_collisions(objects, placements) == []


def test_detect_collisions_skips_unknown_id():
    """placement に対応する object が無ければ静かに無視"""
    objects = [_named("a", width=10, depth=10, height=10, tol=0)]
    placements = [
        {"id": "a", "position": [0, 0, 0]},
        {"id": "ghost", "position": [0, 0, 0]},  # 寸法不明
    ]
    assert geometry.detect_collisions(objects, placements) == []


def test_internal_bbox_manual_aggregates():
    """3 オブジェクト 3D 配置時の内寸合成"""
    objects = [
        _named("display", width=160, depth=100, height=10, tol=0),
        _named("pi", width=85, depth=56, height=18, tol=0),
        _named("gps", width=35, depth=25, height=10, tol=0),
    ]
    placements = [
        {"id": "display", "position": [0, 0, 15]},  # +Z 側
        {"id": "pi", "position": [0, 0, 0]},        # 中央
        {"id": "gps", "position": [60, 0, 0]},      # +X 側
    ]
    bb = geometry.internal_bbox_manual(objects, placements,
                                       object_clearance=1.0, z_margin=0.5)
    # X: display は -80..+80、gps は 60-17.5..60+17.5 = 42.5..77.5 → max=80, min=-80 → width=160
    # +clearance 1.0 × 2 = 162
    assert bb.width == 162.0
    # Y: display は -50..+50 → depth=100 + 2 = 102
    assert bb.depth == 102.0
    # Z: display 10..20, pi -9..9, gps -5..5 → min=-9, max=20 → height=29 + 2 + 0.5 = 31.5
    assert bb.height == pytest.approx(31.5)


def test_internal_bbox_manual_no_placements_raises():
    with pytest.raises(ValueError, match="placements"):
        geometry.internal_bbox_manual([], [], object_clearance=1.0)


def test_internal_bbox_manual_unknown_ids_raises():
    with pytest.raises(ValueError, match="一致しない"):
        geometry.internal_bbox_manual(
            [_named("a", width=10, depth=10, height=10, tol=0)],
            [{"id": "ghost", "position": [0, 0, 0]}],
            object_clearance=1.0,
        )
