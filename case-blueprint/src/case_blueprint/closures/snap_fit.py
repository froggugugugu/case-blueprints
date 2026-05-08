"""closure.method = snap_fit のリファレンス実装。

リップ(凸)+ 受け溝(凹)による嵌合。最もシンプルな closure で、ヒンジも
ラッチも持たない。蓋は完全分離型。

設計:
- 蓋下面に矩形リング状のリップを下方向に押し出す
- リップ外寸 = 本体外寸 − 2 × (壁厚 + fit_clearance)
- 本体上端内側の角を任意で面取り(挿入を楽にする、`lip_groove_chamfer`)

座標規約: `case-spec.closure.lid_axis = "+Z"` を既定とする。蓋は part の bbox
で **zmin** が嵌合面、**xy 中心**を蓋中心と解釈。他軸の場合は generator.py
で primitives を直接呼ぶか、適切に rotate してから渡す。

CadQuery は遅延 import(exporter.py と同じ規約)。validate のみ走る経路では
cadquery 非依存で動く。
"""

from __future__ import annotations

from typing import Any

from . import assert_lid_axis_supported, register


def validate_snap_fit(case_config: dict) -> None:
    """P5 対策: fit_clearance / lip_height の最小値ガード。"""
    lid = case_config.get("lid", {})
    fit_clearance = float(lid.get("fit_clearance", 0))
    lip_height = float(lid.get("lip_height", 0))
    assert fit_clearance > 0, (
        f"lid.fit_clearance={fit_clearance} は正の値である必要がある(P5 参照)"
    )
    assert lip_height >= 1.0, (
        f"lid.lip_height={lip_height} は 1.0mm 以上を推奨"
    )


# ----- primitives(パラメータベース、generator.py から直接呼べる) -----


def make_lip_ring(
    *,
    outer_x: float,
    outer_y: float,
    lip_height: float,
    lip_thickness: float,
    tip_fillet_radius: float = 0.0,
    corner_fillet_radius: float = 0.0,
):
    """蓋下面に貼る矩形リップ(中空角柱)。原点中心、Z=0 から下へ押し出す。

    Returns:
        cq.Workplane: リップ solid。蓋への貼り付けは呼び出し側で translate + union。
    """
    import cadquery as cq

    inner_x = outer_x - 2 * lip_thickness
    inner_y = outer_y - 2 * lip_thickness
    if inner_x <= 0 or inner_y <= 0:
        raise ValueError(
            f"lip 内寸が非正: outer=({outer_x}, {outer_y}) "
            f"thickness={lip_thickness} → inner=({inner_x}, {inner_y})。"
            f"lip_thickness を見直すか外寸を増やしてください"
        )

    sk = cq.Workplane("XY").rect(outer_x, outer_y).rect(inner_x, inner_y)
    if corner_fillet_radius > 0:
        # 外周角を fillet(蓋本体側との見切りを柔らかく)
        sk = sk.vertices(">XY").fillet2D(corner_fillet_radius)
    ring = sk.extrude(-lip_height)
    if tip_fillet_radius > 0:
        # リップ先端(下端)を fillet(挿入を楽に)
        ring = ring.edges("<Z").fillet(tip_fillet_radius)
    return ring


def make_groove_chamfer_cutter(
    *,
    body_outer_x: float,
    body_outer_y: float,
    wall_thickness: float,
    chamfer_size: float,
    body_top_z: float,
):
    """本体上端内側に挿入ガイドの面取りを作るための切削ボリューム。

    body_top_z は本体の上端 Z(蓋が乗る面)。chamfer_size は 45° 面取り高さ。
    Returns: cq.Workplane(body から subtract して使う)
    """
    import cadquery as cq

    inner_x = body_outer_x - 2 * wall_thickness
    inner_y = body_outer_y - 2 * wall_thickness
    if inner_x <= 0 or inner_y <= 0:
        raise ValueError(
            f"本体内寸が非正: outer=({body_outer_x}, {body_outer_y}) "
            f"wall={wall_thickness} → inner=({inner_x}, {inner_y})"
        )

    # 上端から chamfer_size 下まで、内寸は inner、上端で inner + 2*chamfer_size に広げる
    cutter = (
        cq.Workplane("XY")
        .workplane(offset=body_top_z - chamfer_size)
        .rect(inner_x, inner_y)
        .workplane(offset=chamfer_size)
        .rect(inner_x + 2 * chamfer_size, inner_y + 2 * chamfer_size)
        .loft(combine=True)
    )
    return cutter


# ----- compose(body / lid bbox を内省して既定動作で貼る) -----


def build_lip(lid: Any, lid_cfg: dict, walls_cfg: dict) -> Any:
    """蓋 Workplane に snap_fit のリップを足す。

    既定: lid_axis="+Z"、蓋外形 = 本体外形と同じ寸法。
    リップ外寸 = 蓋外寸 − 2 × (wall_t + fit_clearance)。
    """
    bb = lid.val().BoundingBox()

    wall_t = float(walls_cfg.get("thickness", 2.0))
    lip_h = float(lid_cfg.get("lip_height", 3.0))
    fit_c = float(lid_cfg.get("fit_clearance", 0.2))
    lip_t = float(lid_cfg.get("lip_thickness", wall_t))
    tip_r = float(lid_cfg.get("lip_tip_fillet_radius", 0.0))
    corner_r = float(lid_cfg.get("lip_corner_fillet_radius", 0.0))

    lid_x = bb.xlen
    lid_y = bb.ylen
    lip_outer_x = lid_x - 2 * (wall_t + fit_c)
    lip_outer_y = lid_y - 2 * (wall_t + fit_c)

    ring = make_lip_ring(
        outer_x=lip_outer_x,
        outer_y=lip_outer_y,
        lip_height=lip_h,
        lip_thickness=lip_t,
        tip_fillet_radius=tip_r,
        corner_fillet_radius=corner_r,
    )
    cx = (bb.xmin + bb.xmax) / 2
    cy = (bb.ymin + bb.ymax) / 2
    ring = ring.translate((cx, cy, bb.zmin))
    return lid.union(ring)


def build_lip_groove(body: Any, lid_cfg: dict, walls_cfg: dict) -> Any:
    """本体上端内側に挿入ガイドの面取りを足す(任意)。

    `lid.lip_groove_chamfer` が指定されていなければ no-op。基本的な snap_fit は
    本体側の追加加工なしで動くため、これは「挿入を楽にする」最終仕上げに当たる。
    """
    chamfer = float(lid_cfg.get("lip_groove_chamfer", 0.0))
    if chamfer <= 0:
        return body

    bb = body.val().BoundingBox()
    wall_t = float(walls_cfg.get("thickness", 2.0))

    cutter = make_groove_chamfer_cutter(
        body_outer_x=bb.xlen,
        body_outer_y=bb.ylen,
        wall_thickness=wall_t,
        chamfer_size=chamfer,
        body_top_z=bb.zmax,
    )
    cx = (bb.xmin + bb.xmax) / 2
    cy = (bb.ymin + bb.ymax) / 2
    cutter = cutter.translate((cx, cy, 0))
    return body.cut(cutter)


@register("snap_fit")
def build_snap_fit_closure(
    body: Any, lid: Any, case_spec: dict, case_config: dict
) -> dict[str, Any]:
    """closure dispatcher エントリ: 本体 + 蓋 の 2 部品を返す。"""
    assert_lid_axis_supported(case_spec)
    validate_snap_fit(case_config)
    lid_cfg = case_config.get("lid", {})
    walls_cfg = case_config.get("walls", {})
    body = build_lip_groove(body, lid_cfg, walls_cfg)
    lid = build_lip(lid, lid_cfg, walls_cfg)
    return {
        "case-body": body,
        "case-lid": lid,
    }
