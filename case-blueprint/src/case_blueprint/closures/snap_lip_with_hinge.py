"""closure.method = snap_lip_with_hinge のリファレンス実装の骨格。

ヒンジで開閉する蓋に、ラッチ(レバー)を持たない汎用ヒンジ蓋型。
蓋を閉じた状態は **リップ嵌合** の摩擦で保持する。レバーが要らないので
3 部品を出さず本体 + 蓋の 2 部品で完結する。

`hinge_lever` から「レバー」を取り去った位置付け。簡易ケース・小物入れ向け。

generator.py 側で `build_snap_lip_with_hinge_closure` を呼ぶ。
"""

from __future__ import annotations

from typing import Any

from . import register
from .hinge_lever import resolve_hardware as _resolve_hinge_hardware
from .hinge_lever import validate_scale_constraints


def validate_snap_lip_with_hinge(case_config: dict, hardware: dict) -> None:
    """リップ嵌合 + 蝶番側非対称クリア(P14)を検証。"""
    lid = case_config.get("lid", {})
    fit_clearance = float(lid.get("fit_clearance", 0))
    assert fit_clearance > 0, (
        f"lid.fit_clearance={fit_clearance} は正の値である必要がある(P5 参照)"
    )
    hinge_cfg = case_config.get("hinge", {})
    extra = float(hinge_cfg.get("fit_clearance_extra", 0))
    assert extra >= 0.3, (
        f"hinge.fit_clearance_extra={extra} は 0.3mm 以上を推奨(P14 蝶番側非対称クリア)"
    )
    validate_scale_constraints(hinge_cfg, hardware)


def build_hinge_assembly(body: Any, lid: Any, hinge_cfg: dict, hardware: dict) -> tuple[Any, Any]:
    """ヒンジナックル交互生成(hinge_lever と共通の骨格)。"""
    del hinge_cfg, hardware  # placeholder: generator.py が override する
    return body, lid


def build_snap_lip(body: Any, lid: Any, lid_cfg: dict, hinge_cfg: dict) -> tuple[Any, Any]:
    """リップ嵌合(蝶番側のみ非対称に広く取る)。"""
    del lid_cfg, hinge_cfg  # placeholder: generator.py が override する
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
    body, lid = build_hinge_assembly(body, lid, hinge_cfg, hw)
    body, lid = build_snap_lip(body, lid, lid_cfg, hinge_cfg)
    return {
        "case-body": body,
        "case-lid": lid,
    }
