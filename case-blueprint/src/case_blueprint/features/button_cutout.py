"""features type = button_cutout の実装。

物理スイッチ用の開口。round(タクト・押しボタン)、square(ロッカー)、
rounded_square(トグル等) の 3 形状をサポート。

バイクナビ等の **手袋越し操作** が想定される場合、`gloves_compatible: true`
フラグで最小寸法ガードを強制する(round: 直径 ≥ 12mm、square: 短辺 ≥ 10mm)。

パラメータ:
- side: 配置面(必須)
- position: [u, v] 面中心からのオフセット
- shape: round / square / rounded_square(既定 round)
- diameter: round 用
- size: [w, h] square / rounded_square 用
- corner_radius: rounded_square 用(既定 1.0)
- chamfer: ボタン縁の面取り(任意)
- gloves_compatible: 手袋越し操作前提なら true(寸法下限を強制)
"""

from __future__ import annotations

from typing import Any

from ..feature_registry import register
from . import cq_face_selector, normalize_side

GLOVES_MIN_ROUND_DIAMETER = 12.0  # mm
GLOVES_MIN_SQUARE_SHORT = 10.0    # mm


def validate_button_cutout(feature: dict, case_config: dict) -> None:
    del case_config
    if "side" not in feature:
        raise AssertionError("button_cutout: side が必須")
    normalize_side(feature["side"])

    shape = feature.get("shape", "round")
    if shape not in ("round", "square", "rounded_square"):
        raise AssertionError(
            f"button_cutout.shape={shape!r} は round / square / rounded_square のいずれか"
        )

    gloves = bool(feature.get("gloves_compatible", False))

    if shape == "round":
        if "diameter" not in feature:
            raise AssertionError("button_cutout(round): diameter が必須")
        d = float(feature["diameter"])
        if d <= 0:
            raise AssertionError(f"button_cutout.diameter={d} は正の値")
        if gloves and d < GLOVES_MIN_ROUND_DIAMETER:
            raise AssertionError(
                f"button_cutout.gloves_compatible=true で diameter={d}mm < "
                f"{GLOVES_MIN_ROUND_DIAMETER}mm。手袋越しでは押しにくい"
            )
    else:
        if "size" not in feature:
            raise AssertionError(f"button_cutout({shape}): size [w, h] が必須")
        w, h = feature["size"]
        if float(w) <= 0 or float(h) <= 0:
            raise AssertionError(
                f"button_cutout.size={feature['size']} は両方正の値"
            )
        if gloves and min(float(w), float(h)) < GLOVES_MIN_SQUARE_SHORT:
            raise AssertionError(
                f"button_cutout.gloves_compatible=true で短辺={min(float(w), float(h))}mm < "
                f"{GLOVES_MIN_SQUARE_SHORT}mm。手袋越しでは押しにくい"
            )

    if shape == "rounded_square":
        cr = float(feature.get("corner_radius", 1.0))
        if cr < 0:
            raise AssertionError(f"button_cutout.corner_radius={cr} は 0 以上")
        w, h = float(feature["size"][0]), float(feature["size"][1])
        if cr > min(w, h) / 2:
            raise AssertionError(
                f"button_cutout.corner_radius={cr} が短辺の半分を超える"
            )


@register("button_cutout")
def apply_button_cutout(part: Any, feature: dict, case_config: dict) -> Any:
    validate_button_cutout(feature, case_config)
    import cadquery as cq  # noqa: F401

    side = feature["side"]
    selector = cq_face_selector(side)
    pos = feature.get("position", [0.0, 0.0])
    u, v = float(pos[0]), float(pos[1])
    shape = feature.get("shape", "round")

    wp = part.faces(selector).workplane(centerOption="CenterOfBoundBox").center(u, v)

    if shape == "round":
        part = wp.circle(float(feature["diameter"]) / 2).cutThruAll()
    elif shape == "square":
        w, h = feature["size"]
        part = wp.rect(float(w), float(h)).cutThruAll()
    else:  # rounded_square
        w, h = feature["size"]
        cr = float(feature.get("corner_radius", 1.0))
        if cr > 0:
            sk = cq.Sketch().rect(float(w), float(h)).vertices().fillet(cr)
            part = wp.placeSketch(sk).cutThruAll()
        else:
            part = wp.rect(float(w), float(h)).cutThruAll()

    chamfer = float(feature.get("chamfer", 0))
    if chamfer > 0 and shape == "round":
        part = (
            part.faces(selector)
            .edges("%CIRCLE")
            .chamfer(chamfer)
        )
    return part
