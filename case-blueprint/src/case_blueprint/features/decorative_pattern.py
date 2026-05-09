"""features type = decorative_pattern の実装。

意匠的な表面パターン(hex_grid / linear_groove)を任意 face に施す。

`ventilation` との違い: 貫通せず、深さ 0.4-2.0mm の凹彫り or 凸 emboss。
意匠目的なので密度は控えめ(0.2-0.5 推奨)。

パラメータ:
- side: 配置面(必須)
- pattern: hex_grid / linear_groove(dot_pattern は将来予約)
- density: 0.0-1.0(開口面積比、暫定的に pitch 算出に使う)
- depth: 正値=凹彫り、負値=凸 emboss(既定 0.4 mm)
- pitch: パターン間隔(指定なしは density から逆算)
- cell_size: hex_grid の六角形内接円直径(指定なしは pitch から自動)
- groove_width: linear_groove の溝幅(指定なしは pitch * 0.4)
- margin: 開口域の縁から内側の余白(既定 5.0 mm)

theme 経由の自動配置(`/style` skill が style.surface から
decorative_pattern を生成)と、case-spec.yaml の features[] への
直接記述の両方をサポート。
"""

from __future__ import annotations

import math
from typing import Any

from ..feature_registry import register
from . import cq_face_selector, normalize_side


def validate_decorative_pattern(feature: dict, case_config: dict) -> None:
    del case_config
    if "side" not in feature:
        raise AssertionError("decorative_pattern: side が必須")
    normalize_side(feature["side"])

    pattern = feature.get("pattern", "hex_grid")
    if pattern not in ("hex_grid", "linear_groove"):
        raise AssertionError(
            f"decorative_pattern.pattern={pattern!r} は hex_grid / linear_groove のいずれか"
            f"(dot_pattern は将来予約)"
        )

    depth = float(feature.get("depth", 0.4))
    if depth == 0:
        raise AssertionError("decorative_pattern.depth は 0 以外(正=凹彫り、負=凸)")
    if abs(depth) < 0.2:
        raise AssertionError(
            f"decorative_pattern.depth=|{depth}| < 0.2mm。FDM では潰れる(P4 関連)"
        )
    if abs(depth) > 2.0:
        raise AssertionError(
            f"decorative_pattern.depth=|{depth}| > 2.0mm。装飾としては過剰、寸法影響大"
        )

    density = float(feature.get("density", 0.3))
    if not 0.0 < density <= 1.0:
        raise AssertionError(
            f"decorative_pattern.density={density} は (0.0, 1.0] の範囲"
        )


@register("decorative_pattern")
def apply_decorative_pattern(part: Any, feature: dict, case_config: dict) -> Any:
    validate_decorative_pattern(feature, case_config)
    pattern = feature.get("pattern", "hex_grid")
    if pattern == "hex_grid":
        return _apply_hex_grid(part, feature, case_config)
    if pattern == "linear_groove":
        return _apply_linear_groove(part, feature, case_config)
    return part


# ----- helpers -----


def _face_uv_lengths(side: str, bb) -> tuple[float, float]:
    """対象 face の局所 (u, v) 軸方向の長さを bbox から抽出。"""
    if side in ("+Z", "-Z"):
        return bb.xlen, bb.ylen
    if side in ("+X", "-X"):
        return bb.ylen, bb.zlen
    return bb.xlen, bb.zlen  # +Y / -Y


# ----- hex_grid -----


def _apply_hex_grid(part: Any, feature: dict, case_config: dict) -> Any:
    """六角格子配置の凹/凸装飾。

    pitch 未指定なら density から逆算: 六角形 1 個の内接円面積 = π*(cell/2)^2、
    1 セル占有面積 = pitch * (pitch * sqrt(3)/2)、その比が density。
    """
    del case_config
    import cadquery as cq

    side = feature["side"]
    selector = cq_face_selector(side)
    depth = float(feature.get("depth", 0.4))
    margin = float(feature.get("margin", 5.0))
    density = float(feature.get("density", 0.3))

    pitch = feature.get("pitch")
    if pitch is None:
        # 既定 pitch = 8mm(意匠的に視認できる粒度)
        pitch = 8.0
    pitch = float(pitch)

    # 六角形の内接円直径 cell_size。density から逆算
    # 占有面積 = pitch^2 * sqrt(3)/2、六角形面積 = (3*sqrt(3)/2)*(s)^2(s = 一辺)
    # 内接円直径 d = sqrt(3)*s → s = d/sqrt(3)
    # density = ((3*sqrt(3)/2)*(d/sqrt(3))^2) / (pitch^2 * sqrt(3)/2)
    #         = (3 * d^2) / (3 * pitch^2 * sqrt(3) / 2 * 2 / 3) ... 簡略化:
    #         d ≒ pitch * sqrt(density) としておけば近似で十分
    cell_size = float(feature.get("cell_size", pitch * math.sqrt(density)))
    side_len = cell_size / math.sqrt(3)  # 一辺

    face = part.faces(selector).val()
    bb = face.BoundingBox()
    u_len, v_len = _face_uv_lengths(side, bb)
    u_usable = max(0.0, u_len - 2 * margin)
    v_usable = max(0.0, v_len - 2 * margin)

    if u_usable <= cell_size or v_usable <= cell_size:
        # 配置できない狭さ → 何もしない(エラーにはしない、意匠なので)
        return part

    # 行ピッチ = pitch * sqrt(3)/2(縦方向)
    row_pitch = pitch * math.sqrt(3) / 2
    n_v = max(1, int(v_usable / row_pitch))
    n_u_per_row = max(1, int(u_usable / pitch))

    positions = []
    v_start = -v_usable / 2 + row_pitch / 2
    for j in range(n_v):
        v_pos = v_start + j * row_pitch
        offset_u = (pitch / 2) if j % 2 == 1 else 0.0
        u_start = -u_usable / 2 + pitch / 2 + offset_u
        for i in range(n_u_per_row):
            u_pos = u_start + i * pitch
            if abs(u_pos) > u_usable / 2:
                continue
            positions.append((u_pos, v_pos))

    if not positions:
        return part

    sk = cq.Sketch().regularPolygon(side_len, 6)

    wp = (
        part.faces(selector)
        .workplane(centerOption="CenterOfBoundBox")
        .pushPoints(positions)
    )
    if depth > 0:
        # 凹彫り
        return wp.placeSketch(sk).cutBlind(-depth)
    # 凸 emboss(負値)
    return wp.placeSketch(sk).extrude(-depth)


# ----- linear_groove -----


def _apply_linear_groove(part: Any, feature: dict, case_config: dict) -> Any:
    """平行 groove 装飾(細い溝の繰り返し)。"""
    del case_config
    import cadquery as cq  # noqa: F401

    side = feature["side"]
    selector = cq_face_selector(side)
    depth = float(feature.get("depth", 0.4))
    margin = float(feature.get("margin", 5.0))
    pitch = float(feature.get("pitch", 4.0))
    groove_width = float(feature.get("groove_width", pitch * 0.4))

    face = part.faces(selector).val()
    bb = face.BoundingBox()
    u_len, v_len = _face_uv_lengths(side, bb)
    u_usable = max(0.0, u_len - 2 * margin)
    v_usable = max(0.0, v_len - 2 * margin)

    if u_usable <= groove_width or v_usable <= pitch:
        return part

    n = max(1, int(v_usable / pitch))
    if n < 1:
        return part

    wp = (
        part.faces(selector)
        .workplane(centerOption="CenterOfBoundBox")
        .rarray(1, pitch, 1, n, center=True)
        .rect(u_usable, groove_width)
    )
    if depth > 0:
        return wp.cutBlind(-depth)
    return wp.extrude(-depth)
