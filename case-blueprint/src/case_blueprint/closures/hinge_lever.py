"""closure.method = hinge_lever のリファレンス実装。

軸ピン + レバー式ラッチの 3 部品構成(本体 / 蓋 / レバー)。
`/hinged-lid init` がこのモジュールを使い、`build_hinge_lever_closure` が
body / lid / latch-lever の 3 部品を返す。

本ファイルは **ヒンジ系全体で共有される primitives** も提供する:
- make_knuckle / plan_knuckle_chain / attach_knuckle_chain
- make_relief_cut_cylinder (P13)
- make_latch_lever

これらは `snap_lip_with_hinge.py` からも import される。

座標規約:
- hinge.side = "-Y" の場合、ヒンジ軸は X 方向に走る
- ナックルは X 軸方向の円筒(.circle().extrude() を YZ 平面で行う)
- ナックル中心 Z = 本体上端(蓋との境界面)
- ナックル中心 Y = 本体外側面 + offset(外付け型)、または壁面内(埋込型、P13 リリーフ要)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from . import register


def resolve_hardware(case_config: dict) -> dict:
    """hardware preset から具体値を解決。custom はそのまま返す。"""
    hw = case_config.get("hardware", {})
    preset = hw.get("preset", "custom")
    if preset == "custom":
        return hw
    return hw


def validate_scale_constraints(hinge_cfg: dict, hardware: dict) -> None:
    """P17 対策: ナックル厚下限を割らないかを事前検証。"""
    knuckle = hinge_cfg.get("knuckle", {})
    pattern = knuckle.get("pattern", ["body", "lid", "body"])
    z_clearance = knuckle.get("z_clearance", 0.4)

    fastener = hardware.get("hinge", {}).get("fastener", {})
    pin_length = float(fastener.get("length", 0))
    if pin_length <= 0:
        return  # hardware 未設定なら検証スキップ

    end_clear = z_clearance * 2
    n = len(pattern)
    gaps = n - 1
    usable = pin_length - end_clear
    thickness = (usable - gaps * z_clearance) / n
    assert thickness >= 2.0, (
        f"P17: ナックル厚 {thickness:.2f}mm < 2.0mm。"
        f"hardware.hinge.fastener.length を増やすか pattern のナックル数を増やしてください。"
    )


# ----- knuckle primitives -----


@dataclass
class KnuckleSlot:
    """ナックル 1 個の配置情報。"""
    owner: Literal["body", "lid"]
    axis_start: float  # ヒンジ軸方向(X)の開始位置
    axis_end: float    # ヒンジ軸方向(X)の終了位置

    @property
    def length(self) -> float:
        return self.axis_end - self.axis_start

    @property
    def axis_center(self) -> float:
        return (self.axis_start + self.axis_end) / 2


def plan_knuckle_chain(
    *,
    total_length: float,
    pattern: list[str],
    z_clearance: float,
    axis_origin: float = 0.0,
) -> list[KnuckleSlot]:
    """pattern と total_length から各ナックルの配置を返す。

    両端に z_clearance のクリア + ナックル間に z_clearance のクリア。
    `axis_origin` は最初のナックル開始位置(既定: 0、軸中央配置は呼び出し側で調整)。
    """
    n = len(pattern)
    if n < 2:
        raise ValueError(f"pattern は 2 個以上必要: {pattern}")
    end_clear = z_clearance * 2
    gaps = n - 1
    usable = total_length - end_clear
    knuckle_length = (usable - gaps * z_clearance) / n
    if knuckle_length < 1.0:
        raise ValueError(
            f"ナックル長 {knuckle_length:.2f}mm < 1mm。"
            f"total_length={total_length} を増やすか pattern={pattern} を短くしてください"
        )

    slots: list[KnuckleSlot] = []
    cur = axis_origin + z_clearance
    for owner in pattern:
        if owner not in ("body", "lid"):
            raise ValueError(f"pattern 要素は 'body' か 'lid': {owner}")
        slots.append(KnuckleSlot(
            owner=owner,  # type: ignore[arg-type]
            axis_start=cur,
            axis_end=cur + knuckle_length,
        ))
        cur += knuckle_length + z_clearance
    return slots


def make_knuckle(
    *,
    outer_diameter: float,
    pin_diameter: float,
    length: float,
    pin_clearance: float = 0.2,
    min_wall_thickness: float = 0.8,
):
    """ヒンジナックル(X 軸方向の円筒、ピン穴貫通)。

    原点中心、X=0 から +X 方向に length だけ伸ばす。配置は呼び出し側で translate。
    """
    import cadquery as cq

    wall = (outer_diameter - (pin_diameter + pin_clearance)) / 2
    if wall < min_wall_thickness:
        raise ValueError(
            f"ナックル肉厚不足: wall={wall:.2f}mm < min={min_wall_thickness}mm "
            f"(outer={outer_diameter}, pin+clearance={pin_diameter + pin_clearance})"
        )
    knuckle = (
        cq.Workplane("YZ")
        .circle(outer_diameter / 2)
        .extrude(length)
    )
    knuckle = (
        knuckle.faces(">X")
        .workplane()
        .circle((pin_diameter + pin_clearance) / 2)
        .cutThruAll()
    )
    return knuckle


def make_relief_cut_cylinder(
    *,
    knuckle_outer_diameter: float,
    body_relief_clearance: float,
    length: float,
):
    """P13: 蓋ナックル位置で本体壁を切り取るための円筒(X 軸方向)。"""
    import cadquery as cq

    cut_d = knuckle_outer_diameter + 2 * body_relief_clearance
    cut = (
        cq.Workplane("YZ")
        .circle(cut_d / 2)
        .extrude(length)
    )
    return cut


def attach_knuckle_chain(
    body: Any,
    lid: Any,
    *,
    slots: list[KnuckleSlot],
    knuckle_outer_diameter: float,
    pin_diameter: float,
    hinge_axis_y: float,
    hinge_axis_z: float,
    body_wall_outer_y: float | None = None,
    body_relief_clearance: float = 0.3,
    pin_clearance: float = 0.2,
) -> tuple[Any, Any]:
    """slots に従ってナックルを body / lid に追加し、必要なら本体壁にリリーフカット (P13) を入れる。

    Args:
        hinge_axis_y / hinge_axis_z: ヒンジ軸の Y/Z 座標
        body_wall_outer_y: 本体壁の外側 Y 座標(None なら埋込検出スキップ → リリーフカット入れない)
    """
    for slot in slots:
        knuckle = make_knuckle(
            outer_diameter=knuckle_outer_diameter,
            pin_diameter=pin_diameter,
            length=slot.length,
            pin_clearance=pin_clearance,
        )
        knuckle = knuckle.translate((slot.axis_start, hinge_axis_y, hinge_axis_z))
        if slot.owner == "body":
            body = body.union(knuckle)
        else:
            lid = lid.union(knuckle)

    # 埋込型(ナックル中心が本体壁内側)で蓋ナックル位置の本体壁にリリーフカット
    if body_wall_outer_y is not None:
        # 蓋ナックルが本体壁と重なる位置で本体を削る
        for slot in slots:
            if slot.owner != "lid":
                continue
            relief = make_relief_cut_cylinder(
                knuckle_outer_diameter=knuckle_outer_diameter,
                body_relief_clearance=body_relief_clearance,
                length=slot.length,
            )
            relief = relief.translate((slot.axis_start, hinge_axis_y, hinge_axis_z))
            body = body.cut(relief)
    return body, lid


# ----- latch lever primitive -----


def make_latch_lever(
    *,
    length: float,
    width: float,
    thickness: float,
    pivot_hole_diameter: float,
    pivot_offset_from_top: float,
    hook_hole_diameter: float,
    hook_offset_from_bottom: float,
    hook_open: bool = True,
    pin_clearance: float = 0.2,
):
    """レバー部品(平板 + 上端ピン穴 + 下端フック)。

    Y 軸が長手、X 軸が幅、Z 軸が厚さ。+Y 端側に pivot、-Y 端側に hook。
    hook_open=True なら hook_hole から -Y 端まで抜けるスリット(フック開口)。
    """
    import cadquery as cq

    plate = cq.Workplane("XY").rect(width, length).extrude(thickness)
    pivot_y = length / 2 - pivot_offset_from_top
    hook_y = -length / 2 + hook_offset_from_bottom

    plate = (
        plate.faces(">Z")
        .workplane()
        .moveTo(0, pivot_y)
        .circle((pivot_hole_diameter + pin_clearance) / 2)
        .cutThruAll()
    )
    plate = (
        plate.faces(">Z")
        .workplane()
        .moveTo(0, hook_y)
        .circle((hook_hole_diameter + pin_clearance) / 2)
        .cutThruAll()
    )
    if hook_open:
        slot_w = hook_hole_diameter * 0.8
        slot_y_start = hook_y
        slot_y_end = -length / 2
        slot_len = abs(slot_y_start - slot_y_end)
        plate = (
            plate.faces(">Z")
            .workplane()
            .center(0, (slot_y_start + slot_y_end) / 2)
            .rect(slot_w, slot_len)
            .cutThruAll()
        )
    return plate


# ----- compose -----


def build_hinge_assembly(
    body: Any,
    lid: Any,
    hinge_cfg: dict,
    hardware: dict,
) -> tuple[Any, Any]:
    """hinge_cfg / hardware からヒンジナックル列を組み立てる。

    `hinge.geometry.{axis_start, axis_end, axis_y, axis_z, body_wall_outer_y}` を
    指定すれば自動配置。未指定の場合はナックル primitives のみ提供して呼び出し側で配置。
    """
    validate_scale_constraints(hinge_cfg, hardware)

    knuckle = hinge_cfg.get("knuckle", {})
    pattern = list(knuckle.get("pattern", ["body", "lid", "body"]))
    z_clearance = float(knuckle.get("z_clearance", 0.4))
    knuckle_d = float(knuckle.get("outer_diameter", 6.0))
    pin_clearance = float(knuckle.get("pin_clearance", 0.2))
    body_relief_clearance = float(knuckle.get("body_relief_clearance", 0.3))

    fastener = hardware.get("hinge", {}).get("fastener", {})
    pin_d = float(fastener.get("diameter", 2.0))
    pin_l = float(fastener.get("length", 30.0))

    geom = hinge_cfg.get("geometry")
    if geom is None:
        # 自動配置情報なしなら、validate のみ行って素通し
        return body, lid

    axis_start = float(geom["axis_start"])
    axis_end = float(geom["axis_end"])
    axis_y = float(geom["axis_y"])
    axis_z = float(geom["axis_z"])
    body_wall_outer_y = geom.get("body_wall_outer_y")
    if body_wall_outer_y is not None:
        body_wall_outer_y = float(body_wall_outer_y)

    chain_length = axis_end - axis_start
    assert chain_length <= pin_l, (
        f"chain_length={chain_length} > pin_length={pin_l}。"
        f"hardware.hinge.fastener.length を増やすか軸長を縮めてください"
    )
    slots = plan_knuckle_chain(
        total_length=chain_length,
        pattern=pattern,
        z_clearance=z_clearance,
        axis_origin=axis_start,
    )
    return attach_knuckle_chain(
        body, lid,
        slots=slots,
        knuckle_outer_diameter=knuckle_d,
        pin_diameter=pin_d,
        hinge_axis_y=axis_y,
        hinge_axis_z=axis_z,
        body_wall_outer_y=body_wall_outer_y,
        body_relief_clearance=body_relief_clearance,
        pin_clearance=pin_clearance,
    )


def build_latch_pivot(lid: Any, latch_cfg: dict, hardware: dict) -> Any:
    """蓋側のレバー回転軸(2 ナックル + ピン穴)。

    `latch.pivot.geometry.{axis_start, axis_end, axis_y, axis_z}` 指定があれば
    2 ナックルを配置、無ければ素通し。
    """
    pivot = latch_cfg.get("pivot", {})
    geom = pivot.get("geometry")
    if geom is None:
        return lid

    knuckle_d = float(pivot.get("knuckle_outer_diameter", 6.0))
    pattern = list(pivot.get("pattern", ["lid", "lid"]))
    z_clearance = float(pivot.get("z_clearance", 0.4))
    pin_clearance = float(pivot.get("pin_clearance", 0.2))

    fastener = hardware.get("latch", {}).get("pivot_pin", {})
    pin_d = float(fastener.get("diameter", 2.0))

    axis_start = float(geom["axis_start"])
    axis_end = float(geom["axis_end"])
    axis_y = float(geom["axis_y"])
    axis_z = float(geom["axis_z"])

    slots = plan_knuckle_chain(
        total_length=axis_end - axis_start,
        pattern=pattern,
        z_clearance=z_clearance,
        axis_origin=axis_start,
    )
    for slot in slots:
        knuckle = make_knuckle(
            outer_diameter=knuckle_d,
            pin_diameter=pin_d,
            length=slot.length,
            pin_clearance=pin_clearance,
        )
        knuckle = knuckle.translate((slot.axis_start, axis_y, axis_z))
        lid = lid.union(knuckle)
    return lid


def build_latch_catch(body: Any, latch_cfg: dict, hardware: dict) -> Any:
    """本体側の catch ピン保持(2 ナックル、A 方式 cap_side)。"""
    catch = latch_cfg.get("catch", {})
    cap_side = catch.get("cap_side", "right")
    assert cap_side in ("left", "right"), f"cap_side は left/right のみ: {cap_side}"

    geom = catch.get("geometry")
    if geom is None:
        return body

    knuckle_d = float(catch.get("knuckle_outer_diameter", 6.0))
    pattern = list(catch.get("pattern", ["body", "body"]))
    z_clearance = float(catch.get("z_clearance", 0.4))
    pin_clearance = float(catch.get("pin_clearance", 0.2))

    fastener = hardware.get("latch", {}).get("catch_pin", {})
    pin_d = float(fastener.get("diameter", 2.0))

    axis_start = float(geom["axis_start"])
    axis_end = float(geom["axis_end"])
    axis_y = float(geom["axis_y"])
    axis_z = float(geom["axis_z"])

    slots = plan_knuckle_chain(
        total_length=axis_end - axis_start,
        pattern=pattern,
        z_clearance=z_clearance,
        axis_origin=axis_start,
    )
    for slot in slots:
        knuckle = make_knuckle(
            outer_diameter=knuckle_d,
            pin_diameter=pin_d,
            length=slot.length,
            pin_clearance=pin_clearance,
        )
        knuckle = knuckle.translate((slot.axis_start, axis_y, axis_z))
        body = body.union(knuckle)
    return body


def build_latch_lever(latch_cfg: dict, hardware: dict) -> Any:
    """独立部品: 上端ピン穴 + 下端フック + finger_lift タブ。"""
    lever_cfg = latch_cfg.get("lever")
    if lever_cfg is None:
        return None

    fastener_pivot = hardware.get("latch", {}).get("pivot_pin", {})
    fastener_catch = hardware.get("latch", {}).get("catch_pin", {})
    pivot_d = float(fastener_pivot.get("diameter", 2.0))
    hook_d = float(fastener_catch.get("diameter", 2.0))

    return make_latch_lever(
        length=float(lever_cfg["length"]),
        width=float(lever_cfg["width"]),
        thickness=float(lever_cfg["thickness"]),
        pivot_hole_diameter=pivot_d,
        pivot_offset_from_top=float(lever_cfg.get("pivot_offset_from_top", 3.0)),
        hook_hole_diameter=hook_d,
        hook_offset_from_bottom=float(lever_cfg.get("hook_offset_from_bottom", 3.0)),
        hook_open=bool(lever_cfg.get("hook_open", True)),
        pin_clearance=float(lever_cfg.get("pin_clearance", 0.2)),
    )


@register("hinge_lever")
def build_hinge_lever_closure(body: Any, lid: Any, case_spec: dict, case_config: dict) -> dict[str, Any]:
    """closure dispatcher エントリ: 3 部品を組み立てる。"""
    del case_spec
    hw = resolve_hardware(case_config)
    body, lid = build_hinge_assembly(body, lid, case_config.get("hinge", {}), hw)
    lid = build_latch_pivot(lid, case_config.get("latch", {}), hw)
    body = build_latch_catch(body, case_config.get("latch", {}), hw)
    lever = build_latch_lever(case_config.get("latch", {}), hw)
    return {
        "case-body": body,
        "case-lid": lid,
        "latch-lever": lever,
    }
