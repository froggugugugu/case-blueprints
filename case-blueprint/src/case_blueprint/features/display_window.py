"""features type = display_window の実装。

ディスプレイ用の矩形開口。ベゼル(外側の凹み)でフラッシュマウントを作れる。
バイクナビ等の屋外ケースでは bezel を必須化(透明アクリルや IPS パネルを
段差で保持するため)。

パラメータ(features-catalog.md より):
- side: 配置面(必須、通常 "+Z" / front)
- size: [w, h] 開口寸法(必須、ガラス領域基準)
- position: [u, v] 面中心からのオフセット(既定 [0, 0])
- corner_radius: 開口角の R(既定 0、IPS パネルなら 1-2 mm 推奨)
- bezel: { depth, margin } を指定するとフラッシュマウント用の凹みを作る
    - depth: 凹みの深さ(mm、パネル厚 + 0.2 程度)
    - margin: 凹みのサイズが開口より外側にどれだけ広がるか(mm)
"""

from __future__ import annotations

from typing import Any

from ..feature_registry import register
from . import cq_face_selector, normalize_side


def validate_display_window(feature: dict, case_config: dict) -> None:
    del case_config
    if "side" not in feature:
        raise AssertionError("display_window: side が必須")
    normalize_side(feature["side"])

    if "size" not in feature:
        raise AssertionError("display_window: size [w, h] が必須")
    w, h = feature["size"]
    if float(w) <= 0 or float(h) <= 0:
        raise AssertionError(f"display_window.size={feature['size']} は両方正の値")

    cr = float(feature.get("corner_radius", 0))
    if cr < 0:
        raise AssertionError(f"display_window.corner_radius={cr} は 0 以上")
    if cr > min(float(w), float(h)) / 2:
        raise AssertionError(
            f"display_window.corner_radius={cr} が開口寸法 min/2 を超える"
        )

    bezel = feature.get("bezel")
    if bezel is not None:
        bd = float(bezel.get("depth", 0))
        bm = float(bezel.get("margin", 0))
        if bd < 0 or bm < 0:
            raise AssertionError("display_window.bezel.depth / margin は 0 以上")
        if bd > 0 and bm <= 0:
            raise AssertionError(
                "bezel.depth > 0 のとき margin > 0 が必要(段差を作るため)"
            )


@register("display_window")
def apply_display_window(part: Any, feature: dict, case_config: dict) -> Any:
    validate_display_window(feature, case_config)
    import cadquery as cq  # noqa: F401

    side = feature["side"]
    selector = cq_face_selector(side)
    w, h = float(feature["size"][0]), float(feature["size"][1])
    pos = feature.get("position", [0.0, 0.0])
    u, v = float(pos[0]), float(pos[1])
    cr = float(feature.get("corner_radius", 0))

    # 主開口(矩形 cutThruAll)
    wp = part.faces(selector).workplane(centerOption="CenterOfBoundBox").center(u, v)
    sketch = wp.rect(w, h)
    if cr > 0:
        # 角を fillet
        sketch = sketch.vertices().fillet2D(cr)
    part = sketch.cutThruAll()

    # ベゼル(段差掘り込み)
    bezel = feature.get("bezel")
    if bezel and float(bezel.get("depth", 0)) > 0:
        bd = float(bezel["depth"])
        bm = float(bezel["margin"])
        bw, bh = w + 2 * bm, h + 2 * bm
        bezel_sketch = (
            part.faces(selector).workplane(centerOption="CenterOfBoundBox")
            .center(u, v).rect(bw, bh)
        )
        if cr > 0:
            bezel_sketch = bezel_sketch.vertices().fillet2D(cr + bm)
        part = bezel_sketch.cutBlind(-bd)

    return part
