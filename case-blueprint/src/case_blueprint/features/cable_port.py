"""features type = cable_port の実装。

ケーブル/コネクタ通し穴。円(diameter)または長穴(oblong: [w, h])を選択。
屋外用には flange(防水パッキン用フランジ凹み)を任意で追加できる。

パラメータ(features-catalog.md より):
- side: 配置面(必須)
- position: [u, v] 面中心からのオフセット(既定 [0, 0] = 面中心)
- diameter: 円(これと oblong の片方を指定)
- oblong: [w, h] 長穴(横 × 縦)
- chamfer: ケーブル擦れ防止の面取り(既定 0)
- flange: 防水パッキン用フランジ深さ(既定 0、屋外/車載で 1.0-2.0 mm 推奨)
- flange_outer_diameter: フランジ外径(diameter > 0 のときのみ有効)
"""

from __future__ import annotations

from typing import Any

from ..feature_registry import register
from . import cq_face_selector, normalize_side


def validate_cable_port(feature: dict, case_config: dict) -> None:
    del case_config
    if "side" not in feature:
        raise AssertionError("cable_port: side が必須")
    normalize_side(feature["side"])

    has_d = "diameter" in feature
    has_oblong = "oblong" in feature
    if has_d == has_oblong:
        raise AssertionError(
            "cable_port: diameter と oblong のいずれか一方を指定すること"
        )
    if has_d:
        d = float(feature["diameter"])
        if d <= 0:
            raise AssertionError(f"cable_port.diameter={d} は正の値")
    if has_oblong:
        w, h = feature["oblong"]
        if float(w) <= 0 or float(h) <= 0:
            raise AssertionError(f"cable_port.oblong={feature['oblong']} は両方正の値")

    flange = float(feature.get("flange", 0))
    if flange < 0:
        raise AssertionError(f"cable_port.flange={flange} は 0 以上")
    if flange > 0 and has_d:
        outer = float(feature.get("flange_outer_diameter", 0))
        if outer <= float(feature["diameter"]):
            raise AssertionError(
                "cable_port.flange > 0 のとき flange_outer_diameter > diameter が必要"
            )


@register("cable_port")
def apply_cable_port(part: Any, feature: dict, case_config: dict) -> Any:
    validate_cable_port(feature, case_config)
    import cadquery as cq  # noqa: F401

    side = feature["side"]
    selector = cq_face_selector(side)
    pos = feature.get("position", [0.0, 0.0])
    u, v = float(pos[0]), float(pos[1])

    wp = part.faces(selector).workplane(centerOption="CenterOfBoundBox").center(u, v)

    # 主開口
    if "diameter" in feature:
        d = float(feature["diameter"])
        wp_cut = wp.circle(d / 2)
    else:
        w, h = feature["oblong"]
        wp_cut = wp.slot2D(length=max(w, h), diameter=min(w, h),
                           angle=0 if float(w) >= float(h) else 90)
    part = wp_cut.cutThruAll()

    # 面取り(任意)
    chamfer = float(feature.get("chamfer", 0))
    if chamfer > 0:
        part = (
            part.faces(selector)
            .edges("%CIRCLE" if "diameter" in feature else None)
            .chamfer(chamfer)
        )

    # フランジ(防水パッキン用、circle のみ)
    flange = float(feature.get("flange", 0))
    if flange > 0 and "diameter" in feature:
        outer = float(feature["flange_outer_diameter"])
        d = float(feature["diameter"])
        part = (
            part.faces(selector).workplane(centerOption="CenterOfBoundBox")
            .center(u, v)
            .circle(outer / 2).circle(d / 2)
            .cutBlind(-flange)
        )

    return part
