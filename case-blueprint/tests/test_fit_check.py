"""src/case_blueprint/fit_check.py のテスト。

利用者プロジェクトの fit_check.py が薄い shim になる前提で、本体ロジックを
ここで網羅する。CAD 干渉解析は CadQuery が必要なので importorskip。
"""

from __future__ import annotations

import pytest

from case_blueprint import fit_check
from case_blueprint.fit_check import (
    Issue, FitCheckReport, run_all, write_report,
    _features_bbox_2d, _features_bbox_overlap,
)


# ===== fixture: 最小サンプル設定 =====


@pytest.fixture
def cfg_snap_fit():
    """snap_fit / 1 オブジェクト / PLA。"""
    return {
        "project": {
            "name": "test",
            "print_settings": {"printer_bed": [220, 220, 250],
                               "default_material": "pla",
                               "nozzle_diameter": 0.4},
            "design_rules": {"min_wall_thickness": 1.6},
        },
        "case_spec": {
            "case": {
                "name": "test-case",
                "type": "lidded_box",
                "closure": {"method": "snap_fit", "lid_axis": "+Z"},
                "print_orientation": {"body": "bottom_down", "lid": "top_down"},
                "layout": {"arrangement": "stacked"},
                "features": [],
            },
            "objects": [{"id": "x", "position": [0, 0, 0], "rotation": 0}],
        },
        "case_config": {
            "walls": {"thickness": 2.4},
            "lid": {"fit_clearance": 0.25, "lip_height": 3.0},
            "internal": {"object_clearance": 1.0},
        },
        "objects": [
            {"id": "x", "shape": "rectangular",
             "dimensions": {"width": 50, "depth": 30, "height": 15},
             "tolerance": 0.5},
        ],
    }


# ===== Issue / Report の基本 =====


def test_report_counters():
    r = FitCheckReport(issues=[
        Issue("A", "pass", "ok"),
        Issue("A", "warn", "w"),
        Issue("B", "fail", "f"),
    ])
    assert r.n_pass == 1
    assert r.n_warn == 1
    assert r.n_fail == 1


# ===== 標準チェッカー =====


def test_run_internal_clearance_pass(cfg_snap_fit):
    rep = run_all(cfg_snap_fit)
    assert any(i.category == "A" and i.level == "pass" for i in rep.issues)


def test_run_internal_clearance_fail():
    cfg = {
        "project": {"name": "x",
                    "print_settings": {"printer_bed": [200, 200, 200],
                                       "default_material": "pla"},
                    "design_rules": {"min_wall_thickness": 1.6}},
        "case_spec": {"case": {"closure": {"method": "snap_fit"},
                               "layout": {"arrangement": "stacked"},
                               "print_orientation": {"body": "bottom_down", "lid": "top_down"},
                               "features": []},
                      "objects": []},
        "case_config": {"walls": {"thickness": 2.4},
                        "lid": {"fit_clearance": 0.25},
                        "internal": {"object_clearance": 0.2}},
        "objects": [],
    }
    rep = run_all(cfg)
    assert any(i.category == "A" and i.level == "fail" for i in rep.issues)


def test_run_unknown_closure():
    cfg = {
        "project": {"name": "x",
                    "print_settings": {"printer_bed": [200, 200, 200],
                                       "default_material": "pla"},
                    "design_rules": {"min_wall_thickness": 1.6}},
        "case_spec": {"case": {"closure": {"method": "totally_unknown"},
                               "layout": {"arrangement": "stacked"},
                               "print_orientation": {"body": "x", "lid": "y"},
                               "features": []},
                      "objects": []},
        "case_config": {"walls": {"thickness": 2.4},
                        "lid": {"fit_clearance": 0.25},
                        "internal": {"object_clearance": 1.0}},
        "objects": [],
    }
    rep = run_all(cfg)
    assert any(i.category == "B" and i.level == "fail" for i in rep.issues)


def test_run_hinge_check_skipped_for_snap_fit(cfg_snap_fit):
    """snap_fit のとき C カテゴリは出ないこと。"""
    rep = run_all(cfg_snap_fit)
    assert not any(i.category == "C" for i in rep.issues)


def test_run_hinge_thin_wall_fail():
    cfg = {
        "project": {"name": "x",
                    "print_settings": {"printer_bed": [200, 200, 200],
                                       "default_material": "pla"},
                    "design_rules": {"min_wall_thickness": 1.6}},
        "case_spec": {"case": {"closure": {"method": "hinge_lever"},
                               "layout": {"arrangement": "stacked"},
                               "print_orientation": {"body": "x", "lid": "y"},
                               "features": []},
                      "objects": []},
        "case_config": {"walls": {"thickness": 2.4},
                        "lid": {"fit_clearance": 0.25},
                        "internal": {"object_clearance": 1.0},
                        "hinge": {"knuckle": {"outer_diameter": 4.0,
                                              "pin_clearance": 0.2}},
                        "hardware": {"hinge": {"fastener": {"diameter": 2.0}}}},
        "objects": [],
    }
    rep = run_all(cfg)
    # ナックル肉厚 = (4 - (2 + 0.2)) / 2 = 0.9 < 1.0 → fail
    assert any(i.category == "C" and i.level == "fail" and "肉厚" in i.message
               for i in rep.issues)


def test_run_print_feasibility_bed_overflow():
    cfg = {
        "project": {"name": "x",
                    "print_settings": {"printer_bed": [50, 50, 50],
                                       "default_material": "pla"},
                    "design_rules": {"min_wall_thickness": 1.6}},
        "case_spec": {"case": {"closure": {"method": "snap_fit"},
                               "layout": {"arrangement": "stacked"},
                               "print_orientation": {"body": "x", "lid": "y"},
                               "features": []},
                      "objects": [{"id": "huge", "position": [0, 0, 0]}]},
        "case_config": {"walls": {"thickness": 2.4},
                        "lid": {"fit_clearance": 0.25},
                        "internal": {"object_clearance": 1.0}},
        "objects": [
            {"id": "huge", "shape": "rectangular",
             "dimensions": {"width": 200, "depth": 200, "height": 100},
             "tolerance": 0.5},
        ],
    }
    rep = run_all(cfg)
    assert any(i.category == "E" and i.level == "fail" and "bed" in i.message
               for i in rep.issues)


# ===== features 同士の bbox 干渉 =====


class TestFeaturesBboxOverlap:
    def test_circle_and_rect_disjoint(self):
        a = {"side": "+Z", "diameter": 10, "position": [0, 0]}
        b = {"side": "+Z", "size": [10, 10], "position": [30, 0]}
        assert _features_bbox_overlap(a, b) is False

    def test_circle_and_rect_overlap(self):
        a = {"side": "+Z", "diameter": 10, "position": [0, 0]}
        b = {"side": "+Z", "size": [10, 10], "position": [5, 0]}
        assert _features_bbox_overlap(a, b) is True

    def test_no_dim_returns_false(self):
        a = {"side": "+Z", "position": [0, 0]}  # 寸法不明
        b = {"side": "+Z", "diameter": 10, "position": [0, 0]}
        assert _features_bbox_overlap(a, b) is False  # bbox 取れないので skip

    def test_oblong_bbox(self):
        a = {"side": "+Y", "oblong": [12, 4], "position": [0, 0]}
        bb = _features_bbox_2d(a)
        assert bb == (-6.0, 6.0, -2.0, 2.0)


def test_run_objects_collision_manual_layout():
    """layout=manual で objects が重なっているとき D カテゴリで fail"""
    cfg = {
        "project": {"name": "x",
                    "print_settings": {"printer_bed": [200, 200, 200],
                                       "default_material": "pla"},
                    "design_rules": {"min_wall_thickness": 1.6}},
        "case_spec": {"case": {
            "closure": {"method": "snap_fit"},
            "layout": {"arrangement": "manual"},
            "print_orientation": {"body": "x", "lid": "y"},
            "features": [],
        }, "objects": [
            {"id": "a", "position": [0, 0, 0]},
            {"id": "b", "position": [3, 0, 0]},  # 半分重なる
        ]},
        "case_config": {"walls": {"thickness": 2.4},
                        "lid": {"fit_clearance": 0.25},
                        "internal": {"object_clearance": 1.0}},
        "objects": [
            {"id": "a", "shape": "rectangular",
             "dimensions": {"width": 10, "depth": 10, "height": 10}, "tolerance": 0},
            {"id": "b", "shape": "rectangular",
             "dimensions": {"width": 10, "depth": 10, "height": 10}, "tolerance": 0},
        ],
    }
    rep = run_all(cfg)
    assert any(i.category == "D" and i.level == "fail" and "objects" in i.message
               for i in rep.issues)


def test_run_objects_no_collision_manual_layout():
    """layout=manual で十分離れていれば pass"""
    cfg = {
        "project": {"name": "x",
                    "print_settings": {"printer_bed": [200, 200, 200],
                                       "default_material": "pla"},
                    "design_rules": {"min_wall_thickness": 1.6}},
        "case_spec": {"case": {
            "closure": {"method": "snap_fit"},
            "layout": {"arrangement": "manual"},
            "print_orientation": {"body": "x", "lid": "y"},
            "features": [],
        }, "objects": [
            {"id": "a", "position": [0, 0, 0]},
            {"id": "b", "position": [20, 0, 0]},
        ]},
        "case_config": {"walls": {"thickness": 2.4},
                        "lid": {"fit_clearance": 0.25},
                        "internal": {"object_clearance": 1.0}},
        "objects": [
            {"id": "a", "shape": "rectangular",
             "dimensions": {"width": 10, "depth": 10, "height": 10}, "tolerance": 0},
            {"id": "b", "shape": "rectangular",
             "dimensions": {"width": 10, "depth": 10, "height": 10}, "tolerance": 0},
        ],
    }
    rep = run_all(cfg)
    assert any(i.category == "D" and i.level == "pass" and "objects" in i.message
               for i in rep.issues)


def test_run_features_overlap_detected():
    cfg = {
        "project": {"name": "x",
                    "print_settings": {"printer_bed": [200, 200, 200],
                                       "default_material": "pla"},
                    "design_rules": {"min_wall_thickness": 1.6}},
        "case_spec": {"case": {
            "closure": {"method": "snap_fit"},
            "layout": {"arrangement": "stacked"},
            "print_orientation": {"body": "x", "lid": "y"},
            "features": [
                {"type": "cable_port", "side": "-Y",
                 "diameter": 8, "position": [0, 0]},
                {"type": "cable_port", "side": "-Y",
                 "diameter": 8, "position": [3, 0]},  # 5mm 重なり
            ],
        }, "objects": []},
        "case_config": {"walls": {"thickness": 2.4},
                        "lid": {"fit_clearance": 0.25},
                        "internal": {"object_clearance": 1.0}},
        "objects": [],
    }
    rep = run_all(cfg)
    assert any(i.category == "D" and i.level == "fail" for i in rep.issues)


# ===== CAD 干渉 =====


cq = pytest.importorskip("cadquery")


class TestCADOverlap:
    def test_compute_overlap_zero_when_disjoint(self):
        a = cq.Workplane("XY").box(10, 10, 10)
        b = cq.Workplane("XY").box(10, 10, 10).translate((20, 0, 0))
        assert fit_check.compute_part_overlap(a, b) == pytest.approx(0.0, abs=0.5)

    def test_compute_overlap_partial(self):
        a = cq.Workplane("XY").box(10, 10, 10)
        b = cq.Workplane("XY").box(10, 10, 10).translate((5, 0, 0))
        # 重なり = 5 × 10 × 10 = 500
        assert fit_check.compute_part_overlap(a, b) == pytest.approx(500.0, abs=1.0)

    def test_evaluate_with_allowlist(self):
        a = cq.Workplane("XY").box(10, 10, 10)
        b = cq.Workplane("XY").box(10, 10, 10).translate((9.9, 0, 0))
        # 重なり ≒ 0.1 * 10 * 10 = 10 mm³
        parts = {"case-body": a, "case-lid": b}
        issues, overlaps, unmatched = fit_check.evaluate_cad_overlap(
            parts, allowlist=[{"label": "tiny", "max_mm3": 50.0, "where": "test"}],
        )
        # 10 < 50 なので unmatched は 0
        assert unmatched == 0.0


# ===== レポート出力 =====


def test_write_report(tmp_path, cfg_snap_fit):
    rep = run_all(cfg_snap_fit)
    out = tmp_path / "fit-check.md"
    n_fail = write_report(rep, out)
    text = out.read_text()
    assert "# Fit-Check Report" in text
    assert "Pass:" in text
    assert n_fail == rep.n_fail
