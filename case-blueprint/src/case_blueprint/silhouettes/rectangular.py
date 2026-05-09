"""silhouette = rectangular(既定の矩形 box)。

generator.py に直接書かれていた素体生成ロジックを silhouettes に切り出した
形。挙動は完全に同一で、後方互換を保つ。

外寸 = internal + 壁厚 × 2(底厚は walls.bottom_thickness、未指定なら
walls.thickness)。
"""

from __future__ import annotations

from typing import Any

from . import register
from ..geometry import external_bbox


@register("rectangular")
def build_rectangular(
    internal: Any, walls: dict, lid_cfg: dict, style_cfg: dict
) -> dict[str, Any]:
    del style_cfg  # rectangular では使わない
    import cadquery as cq

    eb = external_bbox(internal, wall_thickness=walls.get("thickness", 2.0))
    outer = cq.Workplane("XY").box(eb.width, eb.depth, eb.height)
    inner = cq.Workplane("XY").box(internal.width, internal.depth, internal.height)
    body = outer.cut(inner)
    lid = cq.Workplane("XY").box(eb.width, eb.depth, lid_cfg.get("thickness", 2.0))
    return {"body_blank": body, "lid_blank": lid}
