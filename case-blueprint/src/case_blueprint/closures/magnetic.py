"""closure.method = magnetic のリファレンス実装。

蓋にネオジム磁石、本体に鉄板(または磁石)を埋め込み、磁力で吸着。
ねじ・ヒンジ無しの最薄型。蓋は完全分離型。

設計:
- 蓋下面に磁石ポケット(蓋本体の肉を直接掘り込む)。蓋肉厚 ≥ magnet.thickness + 0.5mm を assert
- 本体内側に鉄板保持ボスを立てる(内寸を圧迫しないよう四隅に配置するのが基本)
- ボス高さ既定 = 内寸高さ − air_gap − plate_pocket_depth(自動計算、明示上書き可)
- air_gap は印刷層の積層誤差を吸収する 0.1-0.3mm の意図的な隙間

座標規約: lid_axis="+Z" 既定。本体は底面が zmin、内側底面 = zmin + bottom_thickness。
蓋は単純な板 (zmin が嵌合面)。
"""

from __future__ import annotations

from typing import Any

from . import register
from .screws import corner_positions


def validate_magnetic(case_config: dict, hardware: dict) -> None:
    """磁石ポケット深さ・吸着面クリアランスのガード。"""
    closure_cfg = case_config.get("closure", {}).get("magnetic", {})
    magnet = hardware.get("closure", {}).get("magnet", {})
    magnet_thickness = float(magnet.get("thickness", 0))
    pocket_depth = float(closure_cfg.get("pocket_depth", 0))

    if magnet_thickness:
        assert pocket_depth >= magnet_thickness + 0.2, (
            f"pocket_depth={pocket_depth} は magnet.thickness({magnet_thickness}) "
            f"+ 0.2mm 以上が必要"
        )

    count = int(closure_cfg.get("count", 0))
    assert count >= 2, (
        f"closure.magnetic.count={count} は 2 個以上を推奨(対角配置で蓋の浮きを抑える)"
    )

    air_gap = float(closure_cfg.get("air_gap", 0.1))
    assert 0 < air_gap <= 0.3, (
        f"air_gap={air_gap} は 0.1-0.3mm を推奨(印刷層の積層誤差を吸収)"
    )


def resolve_magnetic_hardware(case_config: dict) -> dict:
    return case_config.get("hardware", {})


# ----- primitives -----


def make_magnet_post(
    *,
    outer_diameter: float,
    pocket_diameter: float,
    pocket_depth: float,
    height: float,
):
    """鉄板/磁石を上端ポケットに保持するボス。原点中心、Z=0 から +Z へ立てる。"""
    import cadquery as cq

    if pocket_diameter >= outer_diameter:
        raise ValueError(
            f"pocket_diameter={pocket_diameter} >= outer_diameter={outer_diameter}。"
            f"ボスが成立しません"
        )
    if pocket_depth >= height:
        raise ValueError(
            f"pocket_depth={pocket_depth} >= height={height}。"
            f"ボスが下まで貫通してしまいます"
        )
    post = cq.Workplane("XY").circle(outer_diameter / 2).extrude(height)
    post = (
        post.faces(">Z")
        .workplane()
        .circle(pocket_diameter / 2)
        .cutBlind(-pocket_depth)
    )
    return post


# ----- compose -----


def build_magnet_pockets_lid(
    lid: Any, closure_cfg: dict, hardware: dict
) -> Any:
    """蓋下面に磁石ポケットを掘る(蓋本体の肉に直接)。"""
    bb = lid.val().BoundingBox()

    magnet = hardware.get("closure", {}).get("magnet", {})
    md = float(magnet.get("outer_diameter", 6.0))
    mt = float(magnet.get("thickness", 3.0))

    pocket_fit = float(closure_cfg.get("pocket_fit_clearance", 0.1))
    pocket_depth = float(closure_cfg.get("pocket_depth", mt + 0.2))
    count = int(closure_cfg.get("count", 4))
    inset = float(closure_cfg.get("inset", md / 2 + 1.5))

    lid_thickness = bb.zlen
    if lid_thickness < pocket_depth + 0.5:
        raise ValueError(
            f"蓋肉厚 {lid_thickness:.2f}mm < pocket_depth + 0.5mm "
            f"({pocket_depth + 0.5:.2f}mm)。蓋を厚くするか pocket_depth を下げてください"
        )

    positions = closure_cfg.get("positions") or corner_positions(
        bb.xlen, bb.ylen, inset, count
    )
    lid = (
        lid.faces("<Z")
        .workplane()
        .pushPoints(positions)
        .circle((md + pocket_fit) / 2)
        .cutBlind(-pocket_depth)
    )
    return lid


def build_steel_plate_pockets_body(
    body: Any, closure_cfg: dict, walls_cfg: dict, hardware: dict
) -> Any:
    """本体内側に鉄板/対向磁石を保持するボスを立てる。"""
    bb = body.val().BoundingBox()

    plate = hardware.get("closure", {}).get("counter_plate") or hardware.get(
        "closure", {}
    ).get("magnet")
    if plate is None:
        raise ValueError(
            "hardware.closure.counter_plate (鉄板) または magnet (mag_to_mag) が未指定"
        )
    plate_d = float(plate.get("outer_diameter", 12.0))
    plate_t = float(plate.get("thickness", 1.0))

    air_gap = float(closure_cfg.get("air_gap", 0.15))
    pocket_depth = float(closure_cfg.get("plate_pocket_depth", plate_t + 0.2))
    pocket_fit = float(closure_cfg.get("plate_pocket_fit_clearance", 0.1))
    boss_outer_d = float(closure_cfg.get("boss_outer_diameter", plate_d + 3.0))

    walls_t = float(walls_cfg.get("thickness", 2.4))
    bottom_t = float(walls_cfg.get("bottom_thickness", walls_t))

    body_height = bb.zlen
    body_internal_h = body_height - bottom_t  # 上端は開放(蓋面)
    boss_height_default = body_internal_h - air_gap - pocket_depth
    boss_height = float(closure_cfg.get("boss_height", boss_height_default))

    if boss_height < 1.0:
        raise ValueError(
            f"boss_height={boss_height:.2f}mm < 1mm。closure.magnetic.boss_height を"
            f"明示するか、本体内寸高さを増やしてください "
            f"(internal_h={body_internal_h:.2f}, air_gap={air_gap}, pocket_depth={pocket_depth})"
        )

    count = int(closure_cfg.get("count", 4))
    inset = float(closure_cfg.get("inset", boss_outer_d / 2 + 0.5))
    positions = closure_cfg.get("positions") or corner_positions(
        bb.xlen, bb.ylen, inset, count
    )

    cx = (bb.xmin + bb.xmax) / 2
    cy = (bb.ymin + bb.ymax) / 2
    base_z = bb.zmin + bottom_t  # 内側底面の Z

    for px, py in positions:
        post = make_magnet_post(
            outer_diameter=boss_outer_d,
            pocket_diameter=plate_d + pocket_fit,
            pocket_depth=pocket_depth,
            height=boss_height,
        )
        post = post.translate((cx + px, cy + py, base_z))
        body = body.union(post)
    return body


@register("magnetic")
def build_magnetic_closure(
    body: Any, lid: Any, case_spec: dict, case_config: dict
) -> dict[str, Any]:
    """closure dispatcher エントリ: 本体 + 蓋 の 2 部品を返す。"""
    del case_spec
    hw = resolve_magnetic_hardware(case_config)
    validate_magnetic(case_config, hw)
    closure_cfg = case_config.get("closure", {}).get("magnetic", {})
    walls_cfg = case_config.get("walls", {})
    lid = build_magnet_pockets_lid(lid, closure_cfg, hw)
    body = build_steel_plate_pockets_body(body, closure_cfg, walls_cfg, hw)
    return {
        "case-body": body,
        "case-lid": lid,
    }
