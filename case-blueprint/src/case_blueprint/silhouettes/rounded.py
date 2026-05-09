"""silhouette = rounded(角丸矩形)。

box の **垂直エッジ**(Z 方向の 4 本)に fillet を入れて柔らかい印象に。
水平エッジ(底面・上面の角)はそのまま — 印刷時に sagging しないため。

R 値の決定順:
1. `style.fillet_radius.outer` が指定されていれば優先
2. なければ既定 5.0 mm
3. 短辺の半分 - 0.5mm を超える R は自動的にクリップ(box が破綻するため)

closure / features は body / lid の bbox を内省するが、`rounded` でも bbox は
依然外接矩形を返すため、矩形ベースの closure(snap_fit / screws / magnetic)
はそのまま動く。snap_fit のリップは外接矩形に貼られるので、本体外形の
角丸とリップ外形の角丸が **段差** となって見える点に留意(意匠的には許容、
追従させたい場合は L2-B で closure 拡張)。
"""

from __future__ import annotations

from typing import Any

from . import register
from ..geometry import external_bbox


def _resolve_corner_radius(style_cfg: dict, walls: dict, eb) -> float:
    """style.fillet_radius.outer から R を決定、安全範囲にクリップ。"""
    r = float(style_cfg.get("fillet_radius", {}).get("outer", 5.0))
    # 短辺の半分 - 0.5mm を超えないように
    safety_max = min(eb.width, eb.depth) / 2 - 0.5
    return max(0.0, min(r, safety_max))


@register("rounded")
def build_rounded(
    internal: Any, walls: dict, lid_cfg: dict, style_cfg: dict
) -> dict[str, Any]:
    import cadquery as cq

    eb = external_bbox(internal, wall_thickness=walls.get("thickness", 2.0))
    corner_r = _resolve_corner_radius(style_cfg, walls, eb)

    outer = cq.Workplane("XY").box(eb.width, eb.depth, eb.height)
    if corner_r > 0:
        outer = outer.edges("|Z").fillet(corner_r)

    # 内寸も角丸にする(壁厚を維持)。inner_r = outer_r - wall_thickness、最低 0.5
    inner = cq.Workplane("XY").box(internal.width, internal.depth, internal.height)
    if corner_r > 0:
        wall_t = float(walls.get("thickness", 2.0))
        inner_r = max(0.5, corner_r - wall_t)
        # inner も短辺超過しないように
        inner_safety = min(internal.width, internal.depth) / 2 - 0.5
        inner_r = min(inner_r, inner_safety)
        if inner_r > 0:
            inner = inner.edges("|Z").fillet(inner_r)

    body = outer.cut(inner)

    lid = cq.Workplane("XY").box(eb.width, eb.depth, lid_cfg.get("thickness", 2.0))
    if corner_r > 0:
        lid = lid.edges("|Z").fillet(corner_r)

    return {"body_blank": body, "lid_blank": lid}
