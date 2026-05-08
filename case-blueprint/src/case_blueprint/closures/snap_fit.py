"""closure.method = snap_fit のリファレンス実装の骨格。

リップ(凸)+ 受け溝(凹)による嵌合。最もシンプルな closure で、
ヒンジもラッチも持たない。蓋は完全分離型。

generator.py 側で `build_snap_fit_closure` を呼べばよい構造とし、
具体的な CadQuery geometry は generator.py が個別ケースに合わせて埋める。
"""

from __future__ import annotations

from typing import Any

from . import register


def validate_snap_fit(case_config: dict) -> None:
    """P5 対策: fit_clearance / lip_height の最小値ガード。"""
    lid = case_config.get("lid", {})
    fit_clearance = float(lid.get("fit_clearance", 0))
    lip_height = float(lid.get("lip_height", 0))
    assert fit_clearance > 0, (
        f"lid.fit_clearance={fit_clearance} は正の値である必要がある(P5 参照)"
    )
    assert lip_height >= 1.0, (
        f"lid.lip_height={lip_height} は 1.0mm 以上を推奨"
    )


def build_lip(lid: Any, lid_cfg: dict) -> Any:
    """蓋側の嵌合リップ(凸)。実装は generator.py 側で個別。"""
    del lid_cfg  # placeholder: generator.py が override する
    return lid


def build_lip_groove(body: Any, lid_cfg: dict) -> Any:
    """本体側の受け溝(凹)。fit_clearance だけ広く取る。"""
    del lid_cfg  # placeholder: generator.py が override する
    return body


@register("snap_fit")
def build_snap_fit_closure(
    body: Any, lid: Any, case_spec: dict, case_config: dict
) -> dict[str, Any]:
    """closure dispatcher エントリ: 本体 + 蓋 の 2 部品を返す。"""
    del case_spec  # 現状未使用(将来 closure 仕様の参照に使う余地)
    validate_snap_fit(case_config)
    lid_cfg = case_config.get("lid", {})
    body = build_lip_groove(body, lid_cfg)
    lid = build_lip(lid, lid_cfg)
    return {
        "case-body": body,
        "case-lid": lid,
    }
