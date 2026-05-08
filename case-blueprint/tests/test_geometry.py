from __future__ import annotations

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
