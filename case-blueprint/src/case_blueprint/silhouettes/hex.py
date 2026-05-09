"""silhouette = hex(六角プリズム)。

未来感・ガジェット感のある外形。CadQuery の `polygon(6, diameter)` は
**X 方向に頂点**(pointy_top を寝かせた向き)で生成されるので、
**長辺 X / 短辺 Y** の矩形オブジェクトを内包するのに適している。

寸法計算:
- 内寸矩形 (w, d) を内包する六角形の **外接円半径 R**:
    - 長軸方向の頂点距離: 2R = max(w, d)
    - 短軸方向の対辺距離: R*sqrt(3) = min(w, d)
    - よって R = max(max/2, min/sqrt(3))
- 壁厚を加算して外側 R を決定

closure / features との整合(L2-B 段階):
- closure は body / lid の **外接矩形 bbox** を内省するので、矩形ベースの
  リップ・ボス配置が hex 外形の中に「内接」する形になる。意匠的に合うかは
  個別確認だが、機能(嵌合・締結)は概ね動く。
- features の grid 配置は flat 面では矩形 face の bbox に従う。pointy 方向
  の usable area は六角形の幅で頭打ち(自然と狭くなる)。

長軸を Y にしたい場合は generator 側で rotate(0, 0, 90)してから渡す。
本実装は **長軸 X 前提**。
"""

from __future__ import annotations

import math
from typing import Any

from . import register


def _hex_outer_circle_radius(internal_w: float, internal_d: float) -> float:
    """内寸 (w, d) を内包する六角形の外接円半径(壁厚は呼び出し側で加算)。"""
    long_half = max(internal_w, internal_d) / 2
    short_half = min(internal_w, internal_d) / 2
    # 長軸 = 2R、短軸 = R * sqrt(3) → R = max(long_half, short_half / (sqrt(3)/2))
    return max(long_half, short_half / (math.sqrt(3) / 2))


def _make_hex_prism(diameter: float, height: float):
    """X 方向に頂点を持つ pointy_top 六角プリズム(原点中心、Z=0 中央)。"""
    import cadquery as cq

    prism = cq.Workplane("XY").polygon(6, diameter).extrude(height)
    # extrude は z=0..height、原点中心化のため Z 方向に translate
    return prism.translate((0, 0, -height / 2))


@register("hex")
def build_hex(
    internal: Any, walls: dict, lid_cfg: dict, style_cfg: dict
) -> dict[str, Any]:
    del style_cfg  # 既定の pointy_top X 配向のみ実装(orientation オプションは将来)
    import cadquery as cq  # noqa: F401

    inner_R = _hex_outer_circle_radius(internal.width, internal.depth)
    wall_t = float(walls.get("thickness", 2.0))
    outer_R = inner_R + wall_t
    bottom_t = float(walls.get("bottom_thickness", wall_t))

    body_height = internal.height + bottom_t  # 上面は開放(蓋が乗る)

    outer = _make_hex_prism(outer_R * 2, body_height)
    # 内寸も六角形にして壁厚を維持(底厚 bottom_t だけ持ち上げて配置)
    inner = _make_hex_prism(inner_R * 2, internal.height).translate(
        (0, 0, bottom_t / 2)  # 底に厚みを残す
    )
    body = outer.cut(inner)

    lid = _make_hex_prism(outer_R * 2, lid_cfg.get("thickness", 2.0))
    return {"body_blank": body, "lid_blank": lid}
