"""closure.method = screws のリファレンス実装。

蓋を本体ボスにねじ止めする最も堅牢な closure。ヒンジ無し、ラッチ無し、
蓋は完全分離型。防水ねじや heat-set インサートもプリセットで切り替え可能。

設計:
- 本体内側にねじ受けボス(円筒)を立て、中心に下穴を空ける
- 蓋に貫通穴 + 任意で countersink/counterbore を切る
- 配置は対角(count=2)/ 四隅(count=4)/ 四隅+中央(count=6)を既定で提供
- カスタム位置は `closure.screws.positions: [[x, y], ...]` で上書き可能

座標規約: lid_axis="+Z" 既定。蓋・本体ともに XY 中心が原点に揃っていることを
前提とする(generator.py が `cq.Workplane("XY").box()` で作る既定の状態)。
"""

from __future__ import annotations

from typing import Any

from . import assert_lid_axis_supported, register


def validate_screws(case_config: dict, hardware: dict) -> None:
    """ボス肉厚・下穴クリアランス・本数のガード。"""
    closure_cfg = case_config.get("closure", {}).get("screws", {})
    boss_outer_diameter = float(closure_cfg.get("boss_outer_diameter", 0))
    fastener = hardware.get("closure", {}).get("fastener", {})
    screw_d = float(fastener.get("diameter", 0))
    pilot_d = float(closure_cfg.get("pilot_diameter", screw_d * 0.85 if screw_d else 0))

    if boss_outer_diameter and pilot_d:
        wall = (boss_outer_diameter - pilot_d) / 2
        assert wall >= 1.5, (
            f"ボス肉厚 {wall:.2f}mm < 1.5mm。"
            f"boss_outer_diameter を増やすか pilot_diameter を見直す必要あり"
        )

    count = int(closure_cfg.get("count", 0))
    assert count >= 2, (
        f"closure.screws.count={count} は 2 本以上を推奨(対角配置で蓋の浮きを抑える)"
    )

    positions = closure_cfg.get("positions")
    if positions is not None:
        assert isinstance(positions, list) and all(
            isinstance(p, (list, tuple)) and len(p) == 2 for p in positions
        ), f"closure.screws.positions は [[x, y], ...] 形式: {positions}"
        assert len(positions) == count, (
            f"positions 数 {len(positions)} と count {count} が一致しない"
        )


def resolve_screws_hardware(case_config: dict) -> dict:
    return case_config.get("hardware", {})


# ----- primitives -----


def make_screw_boss(
    *,
    outer_diameter: float,
    pilot_diameter: float,
    height: float,
    bottom_solid: float = 1.0,
):
    """ねじ受けボス(原点中心、Z=0 から +Z に押し出し)。

    pilot_diameter > 0 のとき下穴を中心に切る。bottom_solid だけ底に肉を残す
    (セルフタップでも下まで貫通しない、ねじが本体外に飛び出さない構造)。
    """
    import cadquery as cq

    if pilot_diameter >= outer_diameter:
        raise ValueError(
            f"pilot_diameter={pilot_diameter} >= outer_diameter={outer_diameter}。"
            f"ボスが成立しません"
        )
    boss = cq.Workplane("XY").circle(outer_diameter / 2).extrude(height)
    if pilot_diameter > 0:
        depth = max(height - bottom_solid, 0.1)
        boss = (
            boss.faces(">Z")
            .workplane()
            .circle(pilot_diameter / 2)
            .cutBlind(-depth)
        )
    return boss


def corner_positions(
    inner_x: float, inner_y: float, inset: float, count: int
) -> list[tuple[float, float]]:
    """ねじ位置を「ケース XY 中心を原点」とした座標で返す。

    count=2: 対角 / count=4: 四隅 / count=6: 四隅 + 中央左右
    """
    half_x = inner_x / 2 - inset
    half_y = inner_y / 2 - inset
    if half_x <= 0 or half_y <= 0:
        raise ValueError(
            f"inset={inset} が大きすぎてボス位置が成立しない "
            f"(inner=({inner_x}, {inner_y}))"
        )
    if count == 2:
        return [(-half_x, -half_y), (half_x, half_y)]
    if count == 4:
        return [
            (-half_x, -half_y),
            (half_x, -half_y),
            (-half_x, half_y),
            (half_x, half_y),
        ]
    if count == 6:
        return [
            (-half_x, -half_y),
            (half_x, -half_y),
            (-half_x, 0.0),
            (half_x, 0.0),
            (-half_x, half_y),
            (half_x, half_y),
        ]
    raise ValueError(
        f"count={count} は 2/4/6 のみサポート(custom は closure.screws.positions で指定)"
    )


# ----- compose -----


def build_screw_bosses(body: Any, closure_cfg: dict, hardware: dict) -> Any:
    """本体内側にねじ受けボスを N 本立てる。"""
    bb = body.val().BoundingBox()

    fastener = hardware.get("closure", {}).get("fastener", {})
    screw_d = float(fastener.get("diameter", 3.0))
    screw_l = float(fastener.get("length", 8.0))

    boss_outer_d = float(closure_cfg.get("boss_outer_diameter", screw_d * 2.0))
    pilot_d = float(closure_cfg.get("pilot_diameter", screw_d * 0.85))
    boss_inset = float(closure_cfg.get("boss_inset", boss_outer_d / 2 + 0.5))
    boss_height = float(closure_cfg.get("boss_height", max(screw_l - 2.0, 4.0)))
    count = int(closure_cfg.get("count", 4))

    positions = closure_cfg.get("positions") or corner_positions(
        bb.xlen, bb.ylen, boss_inset, count
    )

    cx = (bb.xmin + bb.xmax) / 2
    cy = (bb.ymin + bb.ymax) / 2

    for px, py in positions:
        boss = make_screw_boss(
            outer_diameter=boss_outer_d,
            pilot_diameter=pilot_d,
            height=boss_height,
        )
        boss = boss.translate((cx + px, cy + py, bb.zmin))
        body = body.union(boss)
    return body


def validate_gasket_groove(lid_cfg: dict, walls_cfg: dict) -> None:
    """lid.gasket_groove(O-リング受け矩形溝)の妥当性を検査。

    P18(防水)対策として、本体上端面の周回に矩形溝を切る前提で寸法ガード:
    - width / depth が正
    - 溝が壁内に収まる(width + 2*margin <= wall_thickness 程度)
    - depth は壁高さに対して安全(depth < wall_thickness)
    """
    g = (lid_cfg or {}).get("gasket_groove")
    if g is None:
        return  # 未定義は許容(防水不要なケース)
    width = float(g.get("width", 0))
    depth = float(g.get("depth", 0))
    assert width > 0, f"gasket_groove.width={width} は正の値"
    assert depth > 0, f"gasket_groove.depth={depth} は正の値"
    margin = float(g.get("margin_from_inner_edge", 0.5))
    assert margin >= 0, f"gasket_groove.margin_from_inner_edge={margin} は 0 以上"
    wall_t = float(walls_cfg.get("thickness", 2.0))
    assert width + 2 * margin <= wall_t + 0.01, (
        f"gasket_groove width+2*margin = {width + 2 * margin}mm が壁厚 "
        f"{wall_t}mm を超える。壁厚を上げるか width / margin を縮めてください"
    )
    assert depth < wall_t, (
        f"gasket_groove.depth={depth}mm >= 壁厚 {wall_t}mm。"
        f"溝が壁を貫通します"
    )


def make_gasket_groove_cutter(
    *,
    body_outer_x: float,
    body_outer_y: float,
    wall_thickness: float,
    body_top_z: float,
    width: float,
    depth: float,
    margin_from_inner_edge: float = 0.5,
):
    """本体上端面に切る周回矩形溝(リング状)の cutter solid を返す。

    溝の中心線は **内寸境界の外側** `margin_from_inner_edge + width/2` に置く。
    body から `cut(cutter)` して使う。
    """
    import cadquery as cq

    inner_x = body_outer_x - 2 * wall_thickness
    inner_y = body_outer_y - 2 * wall_thickness
    if inner_x <= 0 or inner_y <= 0:
        raise ValueError(
            f"本体内寸が非正: outer=({body_outer_x}, {body_outer_y}) "
            f"wall={wall_thickness}"
        )

    cl_offset = margin_from_inner_edge + width / 2
    half_outer_x = inner_x / 2 + cl_offset + width / 2
    half_outer_y = inner_y / 2 + cl_offset + width / 2
    half_inner_x = inner_x / 2 + cl_offset - width / 2
    half_inner_y = inner_y / 2 + cl_offset - width / 2

    outer_w = half_outer_x * 2
    outer_h = half_outer_y * 2
    inner_w = half_inner_x * 2
    inner_h = half_inner_y * 2

    cutter = (
        cq.Workplane("XY")
        .workplane(offset=body_top_z - depth)
        .rect(outer_w, outer_h)
        .rect(inner_w, inner_h)
        .extrude(depth)
    )
    return cutter


def build_gasket_groove(body: Any, lid_cfg: dict, walls_cfg: dict) -> Any:
    """lid.gasket_groove が定義されていれば本体上端面に切る、無ければ素通し。

    溝は本体側に掘るのが定石(蓋を閉じたときに O-リングが圧縮される)。
    """
    g = (lid_cfg or {}).get("gasket_groove")
    if g is None:
        return body

    bb = body.val().BoundingBox()
    wall_t = float(walls_cfg.get("thickness", 2.0))
    width = float(g["width"])
    depth = float(g["depth"])
    margin = float(g.get("margin_from_inner_edge", 0.5))

    cutter = make_gasket_groove_cutter(
        body_outer_x=bb.xlen, body_outer_y=bb.ylen,
        wall_thickness=wall_t, body_top_z=bb.zmax,
        width=width, depth=depth, margin_from_inner_edge=margin,
    )
    cx = (bb.xmin + bb.xmax) / 2
    cy = (bb.ymin + bb.ymax) / 2
    cutter = cutter.translate((cx, cy, 0))
    return body.cut(cutter)


def build_screw_holes(lid: Any, closure_cfg: dict, hardware: dict) -> Any:
    """蓋に貫通穴 + countersink/counterbore を切る。"""
    bb = lid.val().BoundingBox()

    fastener = hardware.get("closure", {}).get("fastener", {})
    screw_d = float(fastener.get("diameter", 3.0))
    head_d = float(fastener.get("head_diameter", screw_d * 1.8))
    head_h = float(fastener.get("head_height", screw_d * 0.6))

    through_d = screw_d + float(closure_cfg.get("through_clearance", 0.4))
    countersink_cfg = closure_cfg.get("countersink", {})
    cs_enabled = bool(countersink_cfg.get("enabled", True))
    cs_top_d = float(countersink_cfg.get("top_diameter", head_d + 0.5))
    cs_depth = float(countersink_cfg.get("depth", head_h + 0.2))

    boss_outer_d = float(closure_cfg.get("boss_outer_diameter", screw_d * 2.0))
    boss_inset = float(closure_cfg.get("boss_inset", boss_outer_d / 2 + 0.5))
    count = int(closure_cfg.get("count", 4))
    positions = closure_cfg.get("positions") or corner_positions(
        bb.xlen, bb.ylen, boss_inset, count
    )

    if cs_enabled:
        lid = (
            lid.faces(">Z")
            .workplane()
            .pushPoints(positions)
            .cboreHole(through_d, cs_top_d, cs_depth)
        )
    else:
        lid = (
            lid.faces(">Z")
            .workplane()
            .pushPoints(positions)
            .hole(through_d)
        )
    return lid


@register("screws")
def build_screws_closure(
    body: Any, lid: Any, case_spec: dict, case_config: dict
) -> dict[str, Any]:
    """closure dispatcher エントリ: 本体 + 蓋 の 2 部品を返す。"""
    assert_lid_axis_supported(case_spec)
    hw = resolve_screws_hardware(case_config)
    validate_screws(case_config, hw)
    lid_cfg = case_config.get("lid", {})
    walls_cfg = case_config.get("walls", {})
    validate_gasket_groove(lid_cfg, walls_cfg)
    closure_cfg = case_config.get("closure", {}).get("screws", {})
    body = build_screw_bosses(body, closure_cfg, hw)
    body = build_gasket_groove(body, lid_cfg, walls_cfg)  # P18 防水(任意)
    lid = build_screw_holes(lid, closure_cfg, hw)
    return {
        "case-body": body,
        "case-lid": lid,
    }
