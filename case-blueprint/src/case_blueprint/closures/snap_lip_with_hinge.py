"""closure.method = snap_lip_with_hinge のリファレンス実装。

ヒンジで開閉する蓋に、ラッチ(レバー)を持たない汎用ヒンジ蓋型。
蓋を閉じた状態は **リップ嵌合** の摩擦で保持する。レバーが要らないので
3 部品を出さず本体 + 蓋の 2 部品で完結する。

`hinge_lever` から「レバー」を取り去った位置付け。簡易ケース・小物入れ向け。

設計のポイント:
- 蝶番側のリップは P14(蝶番側非対称クリアランス)の対象。リップを蝶番側に向けて
  中心シフトすることで、蝶番ピンが拘束する Y 位置の印刷誤差を逃がす。
- ヒンジ primitives は `hinge_lever.py` から共有。
"""

from __future__ import annotations

from typing import Any

from . import register
from .hinge_lever import (
    resolve_hardware as _resolve_hinge_hardware,
    validate_scale_constraints,
    build_hinge_assembly as _build_hinge_assembly,
)
from .snap_fit import make_lip_ring


def validate_snap_lip_with_hinge(case_config: dict, hardware: dict) -> None:
    """リップ嵌合 + 蝶番側非対称クリア(P14)を検証。"""
    lid = case_config.get("lid", {})
    fit_clearance = float(lid.get("fit_clearance", 0))
    assert fit_clearance > 0, (
        f"lid.fit_clearance={fit_clearance} は正の値である必要がある(P5 参照)"
    )
    extra = float(lid.get("lip_hinge_side_extra_clearance", 0))
    assert extra >= 0.3, (
        f"lid.lip_hinge_side_extra_clearance={extra} は 0.3mm 以上を推奨(P14 蝶番側非対称クリア)"
    )
    validate_scale_constraints(case_config.get("hinge", {}), hardware)


# ----- compose -----


def build_hinge_assembly(body: Any, lid: Any, hinge_cfg: dict, hardware: dict) -> tuple[Any, Any]:
    """hinge_lever と共通のヒンジ組立を再利用。"""
    return _build_hinge_assembly(body, lid, hinge_cfg, hardware)


def build_snap_lip(
    body: Any,
    lid: Any,
    lid_cfg: dict,
    hinge_cfg: dict,
    walls_cfg: dict,
) -> tuple[Any, Any]:
    """リップ嵌合(蝶番側のみ非対称に広く取る)。

    P14: hinge.side 方向にリップを縮め(extra クリア)、反対側は標準クリアで嵌合。
    """
    bb = lid.val().BoundingBox()

    wall_t = float(walls_cfg.get("thickness", 2.0))
    fit_c = float(lid_cfg.get("fit_clearance", 0.2))
    extra = float(lid_cfg.get("lip_hinge_side_extra_clearance", 1.1))
    lip_h = float(lid_cfg.get("lip_height", 3.0))
    lip_t = float(lid_cfg.get("lip_thickness", wall_t))
    tip_r = float(lid_cfg.get("lip_tip_fillet_radius", 0.0))
    corner_r = float(lid_cfg.get("lip_corner_fillet_radius", 0.0))

    hinge_side = hinge_cfg.get("side", "-Y")
    std = wall_t + fit_c

    x_min = bb.xmin + std
    x_max = bb.xmax - std
    y_min = bb.ymin + std
    y_max = bb.ymax - std

    if hinge_side == "-Y":
        y_min += extra
    elif hinge_side == "+Y":
        y_max -= extra
    elif hinge_side == "-X":
        x_min += extra
    elif hinge_side == "+X":
        x_max -= extra
    else:
        raise ValueError(f"未対応の hinge.side: {hinge_side}")

    lip_outer_x = x_max - x_min
    lip_outer_y = y_max - y_min
    if lip_outer_x <= 0 or lip_outer_y <= 0:
        raise ValueError(
            f"リップ外寸が非正: ({lip_outer_x}, {lip_outer_y})。"
            f"fit_clearance / extra / 蓋寸法のバランスを見直してください"
        )

    lip_cx = (x_min + x_max) / 2
    lip_cy = (y_min + y_max) / 2

    ring = make_lip_ring(
        outer_x=lip_outer_x,
        outer_y=lip_outer_y,
        lip_height=lip_h,
        lip_thickness=lip_t,
        tip_fillet_radius=tip_r,
        corner_fillet_radius=corner_r,
    )
    ring = ring.translate((lip_cx, lip_cy, bb.zmin))
    lid = lid.union(ring)
    return body, lid


@register("snap_lip_with_hinge")
def build_snap_lip_with_hinge_closure(
    body: Any, lid: Any, case_spec: dict, case_config: dict
) -> dict[str, Any]:
    """closure dispatcher エントリ: 本体 + 蓋 の 2 部品を返す(レバー無し)。"""
    del case_spec
    hw = _resolve_hinge_hardware(case_config)
    validate_snap_lip_with_hinge(case_config, hw)
    hinge_cfg = case_config.get("hinge", {})
    lid_cfg = case_config.get("lid", {})
    walls_cfg = case_config.get("walls", {})
    body, lid = build_hinge_assembly(body, lid, hinge_cfg, hw)
    body, lid = build_snap_lip(body, lid, lid_cfg, hinge_cfg, walls_cfg)
    return {
        "case-body": body,
        "case-lid": lid,
    }
