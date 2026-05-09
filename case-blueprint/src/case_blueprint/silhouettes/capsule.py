"""silhouette = capsule(両端半円のカプセル形)。

長径 X / 短径 Y のカプセル形プリズム。柔らかく丸い印象、cute / fancy
テーマと相性が良い。

CadQuery の `Sketch().slot(length, height)` は:
- length: 直線部の長さ(両端半円の中心間距離)
- height: 全幅(短径 = 半円の直径 × 2)
- 全長: length + height

したがって内寸 (w, d) を内包するには:
- 短径(全幅) = min(w, d)
- 全長 = max(w, d)
- length = max(w, d) - min(w, d)(0 以下なら円形に退化、最小 1mm にクリップ)

closure / features は body / lid の **外接矩形 bbox** を内省するので、
矩形ベースのリップ・ボス配置がカプセル外形の中に「内接」する形になる。
両端の半円部分にはスペースが余るので、用途次第では features を端に
寄せる(side: "+X" 等)と意匠的に綺麗に収まる。

長軸を Y にしたい場合は generator 側で rotate(0, 0, 90)してから渡す。
本実装は **長軸 X 前提**。
"""

from __future__ import annotations

from typing import Any

from . import register


def _capsule_dims(internal_w: float, internal_d: float, wall_t: float) -> tuple[float, float, float, float]:
    """内寸 (w, d) と壁厚から、内側 (length, height) と外側 (length, height) を算出。

    length = 直線部、height = 全幅。slot(length, height) の引数仕様に合わせる。
    """
    long_dim = max(internal_w, internal_d)
    short_dim = min(internal_w, internal_d)

    inner_length = max(0.0, long_dim - short_dim)
    inner_height = short_dim

    outer_length = max(0.0, (long_dim + 2 * wall_t) - (short_dim + 2 * wall_t))
    outer_height = short_dim + 2 * wall_t
    return inner_length, inner_height, outer_length, outer_height


def _make_capsule_sketch(length: float, height: float):
    """capsule sketch(length=直線部, height=全幅)。length=0 で円形。"""
    import cadquery as cq

    # length >= 0 が前提、length=0 でも slot は動く(直線 0 = 円)
    return cq.Sketch().slot(length, height)


@register("capsule")
def build_capsule(
    internal: Any, walls: dict, lid_cfg: dict, style_cfg: dict
) -> dict[str, Any]:
    del style_cfg  # capsule は theme 由来の追加調整なし(将来の orientation 対応で利用)
    import cadquery as cq

    wall_t = float(walls.get("thickness", 2.0))
    bottom_t = float(walls.get("bottom_thickness", wall_t))

    inner_l, inner_h, outer_l, outer_h = _capsule_dims(
        internal.width, internal.depth, wall_t
    )
    body_height = internal.height + bottom_t

    outer_sk = _make_capsule_sketch(outer_l, outer_h)
    inner_sk = _make_capsule_sketch(inner_l, inner_h)

    outer = cq.Workplane("XY").placeSketch(outer_sk).extrude(body_height)
    inner = (
        cq.Workplane("XY")
        .workplane(offset=bottom_t)
        .placeSketch(inner_sk)
        .extrude(internal.height)
    )
    body = outer.cut(inner).translate((0, 0, -body_height / 2))

    lid = (
        cq.Workplane("XY")
        .placeSketch(outer_sk)
        .extrude(lid_cfg.get("thickness", 2.0))
        .translate((0, 0, -lid_cfg.get("thickness", 2.0) / 2))
    )
    return {"body_blank": body, "lid_blank": lid}
