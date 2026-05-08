"""features type = mounting_bracket の実装。

オブジェクトの内部マウント、または外部マウント(車載・吊り下げ等)。
style ごとに別関数で分岐し、新規 style は本モジュール内に build_<style>()
を追加して MOUNTING_STYLES に登録する形で拡張。

サポート style(2026-05 時点):
- ribs: 矩形リブで内側からオブジェクトを挟む(target = object id)
- m5_screw_holes: 底面 / 背面に M5 ねじ穴を 4 点(square)等配置
- ram_ball_b: RAM ボール B サイズ(1 インチ径)用ベース + ねじ穴
- (Phase 2 以降) clip / screw_post / heatset_insert

外部マウント側のプリセットは hardware-catalog.md の `mount_*` プリセットと
連動する想定。
"""

from __future__ import annotations

from typing import Any, Callable

from ..feature_registry import register
from . import cq_face_selector, normalize_side


# ----- validators -----


def _validate_m5_screw_holes(feature: dict) -> None:
    pattern = feature.get("pattern", "square")
    if pattern not in ("square", "linear"):
        raise AssertionError(
            f"mounting_bracket(m5_screw_holes).pattern={pattern!r} は square / linear"
        )
    pitch = float(feature.get("pitch", 38.0))
    if pitch <= 0:
        raise AssertionError(f"pitch={pitch} は正の値")
    d = float(feature.get("diameter", 5.0))
    if d <= 0:
        raise AssertionError(f"diameter={d} は正の値")
    cb = feature.get("counterbore")
    if cb is not None:
        cb_d = float(cb.get("diameter", 0))
        cb_h = float(cb.get("depth", 0))
        if cb_d <= d:
            raise AssertionError(
                f"counterbore.diameter={cb_d} は穴径 {d} より大きく"
            )
        if cb_h <= 0:
            raise AssertionError(f"counterbore.depth={cb_h} は正の値")


def _validate_ribs(feature: dict) -> None:
    if "target" not in feature:
        raise AssertionError("mounting_bracket(ribs): target(object id)が必須")
    h = float(feature.get("height", 5.0))
    w = float(feature.get("width", 3.0))
    if h <= 0 or w <= 0:
        raise AssertionError("mounting_bracket(ribs): height / width は正の値")


def _validate_ram_ball_b(feature: dict) -> None:
    base_d = float(feature.get("base_diameter", 30.0))
    base_t = float(feature.get("base_thickness", 4.0))
    if base_d <= 25.4:
        raise AssertionError(
            f"ram_ball_b: base_diameter={base_d} はボール径 25.4mm より大きく"
        )
    if base_t < 3.0:
        raise AssertionError(
            f"ram_ball_b: base_thickness={base_t} < 3mm。引張強度不足の恐れ"
        )


def validate_mounting_bracket(feature: dict, case_config: dict) -> None:
    del case_config
    if "style" not in feature:
        raise AssertionError("mounting_bracket: style が必須")
    style = feature["style"]
    if style not in MOUNTING_STYLES:
        raise AssertionError(
            f"mounting_bracket.style={style!r} は未登録。"
            f"許容: {sorted(MOUNTING_STYLES.keys())}"
        )

    if style == "m5_screw_holes":
        if "side" not in feature:
            raise AssertionError("mounting_bracket(m5_screw_holes): side が必須")
        normalize_side(feature["side"])
        _validate_m5_screw_holes(feature)
    elif style == "ribs":
        _validate_ribs(feature)
    elif style == "ram_ball_b":
        if "side" not in feature:
            raise AssertionError("mounting_bracket(ram_ball_b): side が必須")
        normalize_side(feature["side"])
        _validate_ram_ball_b(feature)


# ----- builders(各 style)-----


def _build_m5_screw_holes(part: Any, feature: dict, case_config: dict) -> Any:
    del case_config
    import cadquery as cq  # noqa: F401

    side = feature["side"]
    selector = cq_face_selector(side)
    pattern = feature.get("pattern", "square")
    pitch = float(feature.get("pitch", 38.0))
    d = float(feature.get("diameter", 5.0))

    wp = part.faces(selector).workplane(centerOption="CenterOfBoundBox")

    if pattern == "square":
        # 4 点(±pitch/2 の正方形)
        positions = [
            (pitch / 2, pitch / 2), (-pitch / 2, pitch / 2),
            (pitch / 2, -pitch / 2), (-pitch / 2, -pitch / 2),
        ]
    else:  # linear
        count = int(feature.get("count", 4))
        positions = [
            ((i - (count - 1) / 2) * pitch, 0.0) for i in range(count)
        ]

    sketch = wp.pushPoints(positions).circle(d / 2)
    part = sketch.cutThruAll()

    cb = feature.get("counterbore")
    if cb is not None:
        cb_d = float(cb["diameter"])
        cb_h = float(cb["depth"])
        cb_sketch = (
            part.faces(selector).workplane(centerOption="CenterOfBoundBox")
            .pushPoints(positions).circle(cb_d / 2)
        )
        part = cb_sketch.cutBlind(-cb_h)
    return part


def _build_ribs(part: Any, feature: dict, case_config: dict) -> Any:
    """target object の bounding box を内側から挟む 4 リブ。

    target object の寸法情報は case_config から引かない(yaml 構造に依存しないため)。
    呼び出し側(generator.py)が `feature["computed"]` に内寸基準の bbox を入れて
    渡すか、既定で `length` / `width` / `height` を直接指定する形を採る。
    """
    del case_config
    import cadquery as cq  # noqa: F401

    rib_h = float(feature.get("height", 5.0))
    rib_w = float(feature.get("width", 3.0))
    target_l = float(feature.get("length", 50.0))   # リブの長さ(Y)
    target_t = float(feature.get("target_width", 50.0))  # 対象 X 寸法
    base_z = float(feature.get("base_z", 0.0))      # 内側底面 Z

    # 4 隅にリブ柱(rib_w × rib_w × rib_h)を立てる例(簡易実装)
    half_x = target_t / 2
    half_y = target_l / 2
    rib_positions = [
        (half_x - rib_w / 2, half_y - rib_w / 2),
        (-half_x + rib_w / 2, half_y - rib_w / 2),
        (half_x - rib_w / 2, -half_y + rib_w / 2),
        (-half_x + rib_w / 2, -half_y + rib_w / 2),
    ]

    for x, y in rib_positions:
        rib = (
            cq.Workplane("XY")
            .center(x, y)
            .rect(rib_w, rib_w)
            .extrude(rib_h)
            .translate((0, 0, base_z))
        )
        part = part.union(rib)
    return part


def _build_ram_ball_b(part: Any, feature: dict, case_config: dict) -> Any:
    """RAM ボール B サイズ用ベース。本体外側に円盤を貼り、4 点 M5 穴を切る。"""
    del case_config
    import cadquery as cq  # noqa: F401

    side = feature["side"]
    selector = cq_face_selector(side)
    base_d = float(feature.get("base_diameter", 30.0))
    base_t = float(feature.get("base_thickness", 4.0))
    pitch = float(feature.get("pitch", 38.1))  # RAM B の標準 PCD
    screw_d = float(feature.get("screw_diameter", 5.0))

    # 外側に円盤を貼る
    disk = (
        part.faces(selector).workplane(centerOption="CenterOfBoundBox")
        .circle(base_d / 2).extrude(base_t)
    )
    # 4 点 M5 穴(square pattern、PCD pitch)
    positions = [
        (pitch / 2, pitch / 2), (-pitch / 2, pitch / 2),
        (pitch / 2, -pitch / 2), (-pitch / 2, -pitch / 2),
    ]
    return (
        disk.faces(selector).workplane(centerOption="CenterOfBoundBox")
        .pushPoints(positions).circle(screw_d / 2)
        .cutThruAll()
    )


# style -> builder 関数のレジストリ(拡張ポイント)
MOUNTING_STYLES: dict[str, Callable[[Any, dict, dict], Any]] = {
    "ribs": _build_ribs,
    "m5_screw_holes": _build_m5_screw_holes,
    "ram_ball_b": _build_ram_ball_b,
}


@register("mounting_bracket")
def apply_mounting_bracket(part: Any, feature: dict, case_config: dict) -> Any:
    validate_mounting_bracket(feature, case_config)
    style = feature["style"]
    builder = MOUNTING_STYLES[style]
    return builder(part, feature, case_config)
