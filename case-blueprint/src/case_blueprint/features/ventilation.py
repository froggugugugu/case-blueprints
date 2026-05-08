"""features type = ventilation の実装。

通気孔(grid / slots / honeycomb)を指定 face に開ける。

パラメータ(features-catalog.md より):
- side: "+Z" 等(必須)
- pattern: grid / slots / honeycomb(既定 grid)
- density: 0.0-0.5(開口面積比、既定 0.3)
- hole_diameter: grid 用(既定 3.0 mm)
- slot_width / slot_length: slots 用
- cell_size: honeycomb 用

既定値は屋内ケース向け。屋外・防水ケースでは ventilation を入れない選択もある
(屋外ケースでパッキン併用が必要な場合は cable_port に flange を併設する想定)。
"""

from __future__ import annotations

from typing import Any

from ..feature_registry import register
from . import cq_face_selector, normalize_side


def validate_ventilation(feature: dict, case_config: dict) -> None:
    """side / density / 寸法の妥当性を検査。"""
    del case_config  # 未使用(将来の min_wall_thickness 連動で参照予定)
    if "side" not in feature:
        raise AssertionError("ventilation: side が必須")
    normalize_side(feature["side"])  # 未知 side で ValueError

    pattern = feature.get("pattern", "grid")
    if pattern not in ("grid", "slots", "honeycomb"):
        raise AssertionError(
            f"ventilation.pattern={pattern!r} は grid / slots / honeycomb のいずれか"
        )

    density = float(feature.get("density", 0.3))
    if not 0.0 < density <= 0.5:
        raise AssertionError(
            f"ventilation.density={density} は (0.0, 0.5] の範囲。"
            f"0.5 を超えると壁強度が落ちる(P3 関連)"
        )

    if pattern == "grid":
        hole_d = float(feature.get("hole_diameter", 3.0))
        if hole_d <= 0:
            raise AssertionError(f"ventilation.hole_diameter={hole_d} は正の値")
        if hole_d > 10.0:
            raise AssertionError(
                f"ventilation.hole_diameter={hole_d} > 10mm はブリッジ困難。"
                f"slots / honeycomb への切り替えを推奨"
            )

    if pattern == "slots":
        sw = float(feature.get("slot_width", 2.0))
        sl = float(feature.get("slot_length", 12.0))
        if sw <= 0 or sl <= 0:
            raise AssertionError(f"ventilation.slot_width / slot_length は正の値")


@register("ventilation")
def apply_ventilation(part: Any, feature: dict, case_config: dict) -> Any:
    """通気孔を part の指定 face に開ける。"""
    validate_ventilation(feature, case_config)
    pattern = feature.get("pattern", "grid")

    if pattern == "grid":
        return _apply_grid(part, feature, case_config)
    if pattern == "slots":
        return _apply_slots(part, feature, case_config)
    if pattern == "honeycomb":
        return _apply_honeycomb(part, feature, case_config)
    return part


def _apply_grid(part: Any, feature: dict, case_config: dict) -> Any:
    """格子配列の円穴。density から穴の本数を逆算。"""
    del case_config
    import cadquery as cq  # noqa: F401

    side = feature["side"]
    selector = cq_face_selector(side)
    hole_d = float(feature.get("hole_diameter", 3.0))
    density = float(feature.get("density", 0.3))
    margin = float(feature.get("margin", 5.0))  # 開口域の縁から内側の余白

    # 対象 face の bbox を内省して開口域を決める
    face = part.faces(selector).val()
    bb = face.BoundingBox()
    # face の局所 u/v 軸は CadQuery が workplane() で抽出するため、
    # ここでは対象 face の **2 本の長辺** を usable size に使う(正方形以外も対応)。
    if side in ("+Z", "-Z"):
        u_len, v_len = bb.xlen, bb.ylen
    elif side in ("+X", "-X"):
        u_len, v_len = bb.ylen, bb.zlen
    else:  # +Y / -Y
        u_len, v_len = bb.xlen, bb.zlen

    u_usable = max(0.0, u_len - 2 * margin)
    v_usable = max(0.0, v_len - 2 * margin)
    if u_usable <= 0 or v_usable <= 0:
        raise ValueError(
            f"ventilation grid: usable area が非正(face={side}, "
            f"u={u_usable}, v={v_usable})。margin を小さくしてください"
        )

    # 1 穴の面積
    import math
    hole_area = math.pi * (hole_d / 2) ** 2
    # 必要総開口面積
    total_open = density * (u_usable * v_usable)
    n_holes = max(1, int(total_open / hole_area))

    # n_holes を u/v 比に応じて分配
    aspect = u_usable / v_usable
    n_v = max(1, int(round((n_holes / aspect) ** 0.5)))
    n_u = max(1, int(round(n_holes / n_v)))

    pitch_u = u_usable / n_u
    pitch_v = v_usable / n_v

    # CadQuery で穴を開ける
    return (
        part.faces(selector).workplane(centerOption="CenterOfBoundBox")
        .rarray(pitch_u, pitch_v, n_u, n_v, center=True)
        .circle(hole_d / 2)
        .cutThruAll()
    )


def _apply_slots(part: Any, feature: dict, case_config: dict) -> Any:
    """平行スロット。"""
    del case_config
    import cadquery as cq  # noqa: F401

    side = feature["side"]
    selector = cq_face_selector(side)
    sw = float(feature.get("slot_width", 2.0))
    sl = float(feature.get("slot_length", 12.0))
    density = float(feature.get("density", 0.3))
    margin = float(feature.get("margin", 5.0))
    pitch = float(feature.get("pitch", sw * 3))  # 既定: スロット幅の 3 倍

    face = part.faces(selector).val()
    bb = face.BoundingBox()
    if side in ("+Z", "-Z"):
        u_len, v_len = bb.xlen, bb.ylen
    elif side in ("+X", "-X"):
        u_len, v_len = bb.ylen, bb.zlen
    else:
        u_len, v_len = bb.xlen, bb.zlen

    u_usable = max(0.0, u_len - 2 * margin)
    v_usable = max(0.0, v_len - 2 * margin)
    n_slots = max(1, int(v_usable / pitch))

    # density チェック(slots の総開口面積 vs usable area)
    actual_density = (n_slots * sw * sl) / (u_usable * v_usable)
    if actual_density > density * 1.5:
        # density を上回りすぎないよう n_slots を縮める
        n_slots = max(1, int(density * u_usable * v_usable / (sw * sl)))

    return (
        part.faces(selector).workplane(centerOption="CenterOfBoundBox")
        .rarray(1, pitch, 1, n_slots, center=True)
        .slot2D(length=sl, diameter=sw, angle=0)
        .cutThruAll()
    )


def _apply_honeycomb(part: Any, feature: dict, case_config: dict) -> Any:
    """六角形ハニカム。Phase 1 では grid と同等の挙動(将来 polygon に置換)。"""
    # 暫定: grid と同じ動作(P1 で先送り、専用実装は features 強化フェーズで)
    return _apply_grid(part, feature, case_config)
