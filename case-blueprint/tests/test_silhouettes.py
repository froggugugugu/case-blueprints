"""silhouettes/* のテスト。

L2: silhouette ディスパッチ + rectangular / rounded の素体生成。
hex / capsule は将来追加予定で、未登録時は rectangular にフォールバック。
"""

from __future__ import annotations

import pytest

from case_blueprint import silhouettes
from case_blueprint.geometry import BoundingBox


# ===== レジストリの基本 =====


class TestSilhouetteRegistry:
    def test_rectangular_registered(self):
        assert "rectangular" in silhouettes.SILHOUETTES

    def test_rounded_registered(self):
        assert "rounded" in silhouettes.SILHOUETTES

    def test_registered_silhouettes_sorted(self):
        names = silhouettes.registered_silhouettes()
        assert names == sorted(names)

    def test_unknown_falls_back_to_rectangular(self, capsys):
        """未知 silhouette は警告 print + rectangular で動く"""
        cq = pytest.importorskip("cadquery")
        del cq
        internal = BoundingBox(width=50, depth=40, height=20)
        out = silhouettes.build(
            "totally_unknown", internal,
            walls={"thickness": 2.0},
            lid_cfg={"thickness": 2.0},
        )
        assert "body_blank" in out and "lid_blank" in out
        captured = capsys.readouterr()
        assert "未実装" in captured.out


# ===== CadQuery 必須テスト =====


cq = pytest.importorskip("cadquery")


@pytest.fixture
def small_internal():
    return BoundingBox(width=50, depth=40, height=20)


@pytest.fixture
def common_walls():
    return {"thickness": 2.0}


@pytest.fixture
def common_lid():
    return {"thickness": 2.0}


# ===== rectangular =====


class TestRectangular:
    def test_returns_body_and_lid(self, small_internal, common_walls, common_lid):
        out = silhouettes.build("rectangular", small_internal, common_walls, common_lid)
        assert out["body_blank"].val().Volume() > 0
        assert out["lid_blank"].val().Volume() > 0

    def test_body_outer_dimensions(self, small_internal, common_walls, common_lid):
        """外寸 = 内寸 + 壁厚 × 2(rectangular の検証)"""
        out = silhouettes.build("rectangular", small_internal, common_walls, common_lid)
        bb = out["body_blank"].val().BoundingBox()
        assert bb.xlen == pytest.approx(54.0, abs=0.01)  # 50 + 2*2
        assert bb.ylen == pytest.approx(44.0, abs=0.01)


# ===== rounded =====


class TestRounded:
    def test_corner_radius_from_style(self, small_internal, common_walls, common_lid):
        """style.fillet_radius.outer から R が反映される"""
        out_sharp = silhouettes.build(
            "rounded", small_internal, common_walls, common_lid,
            style_cfg={"fillet_radius": {"outer": 0.5}},
        )
        out_round = silhouettes.build(
            "rounded", small_internal, common_walls, common_lid,
            style_cfg={"fillet_radius": {"outer": 8.0}},
        )
        v_sharp = out_sharp["body_blank"].val().Volume()
        v_round = out_round["body_blank"].val().Volume()
        # R が大きい方が角が削れて体積が小さい
        assert v_round < v_sharp

    def test_default_radius_5mm(self, small_internal, common_walls, common_lid):
        """style 未指定でも既定 5mm で動く"""
        out = silhouettes.build("rounded", small_internal, common_walls, common_lid,
                                 style_cfg={})
        assert out["body_blank"].val().Volume() > 0

    def test_radius_clamped_to_safety(self, small_internal, common_walls, common_lid):
        """過大な R は安全範囲(短辺/2 - 0.5)にクリップされる"""
        out = silhouettes.build(
            "rounded", small_internal, common_walls, common_lid,
            style_cfg={"fillet_radius": {"outer": 100.0}},  # 短辺 40 / 2 = 20 を超える
        )
        # クリップされて成立する(40/2 - 0.5 = 19.5 が上限)
        v = out["body_blank"].val().Volume()
        assert v > 0
        # 角丸が極限近くまで効いて、矩形より小さい
        out_rect = silhouettes.build("rectangular", small_internal, common_walls, common_lid)
        assert v < out_rect["body_blank"].val().Volume()

    def test_lid_also_rounded(self, small_internal, common_walls, common_lid):
        """蓋も同じ R で角丸になる"""
        out_round = silhouettes.build(
            "rounded", small_internal, common_walls, common_lid,
            style_cfg={"fillet_radius": {"outer": 5.0}},
        )
        out_rect = silhouettes.build("rectangular", small_internal, common_walls, common_lid)
        # rounded の lid は rectangular の lid より体積が小さい(角削れ分)
        assert out_round["lid_blank"].val().Volume() < out_rect["lid_blank"].val().Volume()


class TestHex:
    """L2-B: 六角プリズム外形。"""

    def test_registered(self):
        assert "hex" in silhouettes.SILHOUETTES

    def test_returns_body_and_lid(self, small_internal, common_walls, common_lid):
        out = silhouettes.build("hex", small_internal, common_walls, common_lid)
        assert out["body_blank"].val().Volume() > 0
        assert out["lid_blank"].val().Volume() > 0

    def test_body_contains_internal(self, small_internal, common_walls, common_lid):
        """内寸矩形 (50, 40, 20) が外接 hex の中に収まる(寸法面での包含)"""
        out = silhouettes.build("hex", small_internal, common_walls, common_lid)
        bb = out["body_blank"].val().BoundingBox()
        # 内寸 50×40 を pointy_top 六角形(長軸 X)で内包 →
        # outer R = max(25, 20 / (sqrt(3)/2)) ≒ max(25, 23.09) = 25
        # 壁 +2 → outer R = 27 → 直径 54
        # 短軸方向(Y)= 27 * sqrt(3) ≒ 46.77
        assert bb.xlen == pytest.approx(54.0, abs=0.01)
        assert bb.ylen == pytest.approx(46.77, abs=0.05)

    def test_smaller_than_rectangular(self, small_internal, common_walls, common_lid):
        """六角の体積は同じ外接円の矩形より小さい(角が削れる)"""
        out_hex = silhouettes.build("hex", small_internal, common_walls, common_lid)
        # 同じ外径の矩形(54×46.77×外寸高)と比較
        bb = out_hex["body_blank"].val().BoundingBox()
        rect_volume_outer_box = bb.xlen * bb.ylen * bb.zlen
        # 六角プリズムは六角形 sketch なので、外接矩形より小さい
        assert out_hex["body_blank"].val().Volume() < rect_volume_outer_box

    def test_snap_fit_works_on_hex_body(self, small_internal, common_walls, common_lid):
        """hex body に snap_fit closure が適用できる(bbox 内省で動く)"""
        from case_blueprint import closures
        out = silhouettes.build("hex", small_internal, common_walls, common_lid)
        body = out["body_blank"]
        lid = out["lid_blank"]
        lid = lid.translate((0, 0, body.val().BoundingBox().zmax + lid.val().BoundingBox().zlen / 2))
        case_spec = {"case": {"closure": {"method": "snap_fit", "lid_axis": "+Z"}}}
        case_config = {
            "lid": {"thickness": 2.0, "fit_clearance": 0.2, "lip_height": 3.0},
            "walls": {"thickness": 2.0},
        }
        parts = closures.build("snap_fit", body, lid, case_spec, case_config)
        assert "case-body" in parts and parts["case-body"].val().Volume() > 0

    def test_screws_works_on_hex_body(self, small_internal, common_walls, common_lid):
        """hex body に screws closure が適用できる(bbox ベースの 4 隅配置)"""
        from case_blueprint import closures
        out = silhouettes.build("hex", small_internal, common_walls, common_lid)
        body = out["body_blank"]
        lid = out["lid_blank"]
        lid = lid.translate((0, 0, body.val().BoundingBox().zmax + lid.val().BoundingBox().zlen / 2))
        case_spec = {"case": {"closure": {"method": "screws", "lid_axis": "+Z"}}}
        case_config = {
            "lid": {"thickness": 2.0, "fit_clearance": 0.2, "lip_height": 3.0},
            "walls": {"thickness": 2.0},
            "closure": {"screws": {"count": 4, "boss_outer_diameter": 6.0,
                                    "pilot_diameter": 2.55}},
            "hardware": {"closure": {"fastener": {"diameter": 3.0, "length": 8.0,
                                                   "head_diameter": 5.6, "head_height": 1.86}}},
        }
        parts = closures.build("screws", body, lid, case_spec, case_config)
        assert "case-body" in parts and parts["case-body"].val().Volume() > 0


class TestCapsule:
    """L2-C: 両端半円のカプセル形外形。"""

    def test_registered(self):
        assert "capsule" in silhouettes.SILHOUETTES

    def test_returns_body_and_lid(self, small_internal, common_walls, common_lid):
        out = silhouettes.build("capsule", small_internal, common_walls, common_lid)
        assert out["body_blank"].val().Volume() > 0
        assert out["lid_blank"].val().Volume() > 0

    def test_outer_dimensions(self, small_internal, common_walls, common_lid):
        """内寸 (50, 40, 20) + 壁 2 → 全長 54、全幅 44(短径)"""
        out = silhouettes.build("capsule", small_internal, common_walls, common_lid)
        bb = out["body_blank"].val().BoundingBox()
        # 全長 X = max(w, d) + 2*wall = 50 + 4 = 54
        # 全幅 Y = min(w, d) + 2*wall = 40 + 4 = 44
        assert bb.xlen == pytest.approx(54.0, abs=0.01)
        assert bb.ylen == pytest.approx(44.0, abs=0.01)

    def test_smaller_than_rectangular(self, small_internal, common_walls, common_lid):
        """capsule は同じ外接矩形より体積が小さい(両端の角が丸い)"""
        out_caps = silhouettes.build("capsule", small_internal, common_walls, common_lid)
        out_rect = silhouettes.build("rectangular", small_internal, common_walls, common_lid)
        assert out_caps["body_blank"].val().Volume() < out_rect["body_blank"].val().Volume()

    def test_snap_fit_works_on_capsule_body(self, small_internal, common_walls, common_lid):
        """capsule body に snap_fit closure が適用できる(bbox 内省で動く)"""
        from case_blueprint import closures
        out = silhouettes.build("capsule", small_internal, common_walls, common_lid)
        body = out["body_blank"]
        lid = out["lid_blank"]
        lid = lid.translate((0, 0, body.val().BoundingBox().zmax + lid.val().BoundingBox().zlen / 2))
        case_spec = {"case": {"closure": {"method": "snap_fit", "lid_axis": "+Z"}}}
        case_config = {
            "lid": {"thickness": 2.0, "fit_clearance": 0.2, "lip_height": 3.0},
            "walls": {"thickness": 2.0},
        }
        parts = closures.build("snap_fit", body, lid, case_spec, case_config)
        assert "case-body" in parts and parts["case-body"].val().Volume() > 0


# ===== closure との整合(rectangular / rounded で snap_fit が動くか)=====


class TestSilhouetteCompatibilityWithClosure:
    def test_snap_fit_works_on_rounded_body(self, small_internal, common_walls, common_lid):
        """rounded body に snap_fit closure が適用できる(bbox 内省で動く)"""
        from case_blueprint import closures
        out = silhouettes.build(
            "rounded", small_internal, common_walls, common_lid,
            style_cfg={"fillet_radius": {"outer": 3.0}},
        )
        body = out["body_blank"]
        lid = out["lid_blank"]
        # lid を body 上に乗せる
        lid = lid.translate((0, 0, body.val().BoundingBox().zmax + lid.val().BoundingBox().zlen / 2))
        case_spec = {"case": {"closure": {"method": "snap_fit", "lid_axis": "+Z"}}}
        case_config = {
            "lid": {"thickness": 2.0, "fit_clearance": 0.2, "lip_height": 3.0},
            "walls": {"thickness": 2.0},
        }
        parts = closures.build("snap_fit", body, lid, case_spec, case_config)
        assert "case-body" in parts
        assert "case-lid" in parts
        assert parts["case-body"].val().Volume() > 0
        assert parts["case-lid"].val().Volume() > 0
