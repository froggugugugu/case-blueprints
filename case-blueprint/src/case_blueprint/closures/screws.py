"""closure.method = screws のリファレンス実装の骨格。

蓋を本体ボスにねじ止めする最も堅牢な closure。
ヒンジ無し、ラッチ無し、蓋は完全分離型。防水ねじやインサートナットも
プリセットで切り替え可能。

generator.py 側で `build_screws_closure` を呼ぶ。具体的な CadQuery geometry は
generator.py が個別ケースに合わせて埋める。
"""

from __future__ import annotations

from typing import Any

from . import register


def validate_screws(case_config: dict, hardware: dict) -> None:
    """ボス肉厚・下穴クリアランス・ねじ突き出しのガード。"""
    closure_cfg = case_config.get("closure", {}).get("screws", {})
    boss_outer_diameter = float(closure_cfg.get("boss_outer_diameter", 0))
    fastener = hardware.get("closure", {}).get("fastener", {})
    screw_d = float(fastener.get("diameter", 0))
    pilot_d = float(closure_cfg.get("pilot_diameter", screw_d * 0.85))

    if boss_outer_diameter and screw_d:
        wall = (boss_outer_diameter - pilot_d) / 2
        assert wall >= 1.5, (
            f"ボス肉厚 {wall:.2f}mm < 1.5mm。"
            f"boss_outer_diameter を増やすか pilot_diameter を見直す必要あり"
        )

    count = int(closure_cfg.get("count", 0))
    assert count >= 2, (
        f"closure.screws.count={count} は 2 本以上を推奨(対角配置で蓋の浮きを抑える)"
    )


def resolve_screws_hardware(case_config: dict) -> dict:
    """hardware preset から具体値を解決。"""
    hw = case_config.get("hardware", {})
    return hw


def build_screw_bosses(body: Any, closure_cfg: dict, hardware: dict) -> Any:
    """本体側のねじ受けボス(下穴付き、または heat-set インサート用)。"""
    del closure_cfg, hardware  # placeholder: generator.py が override する
    return body


def build_screw_holes(lid: Any, closure_cfg: dict, hardware: dict) -> Any:
    """蓋側のねじ通し穴 + 皿ザグリ(または埋頭)。"""
    del closure_cfg, hardware  # placeholder: generator.py が override する
    return lid


@register("screws")
def build_screws_closure(
    body: Any, lid: Any, case_spec: dict, case_config: dict
) -> dict[str, Any]:
    """closure dispatcher エントリ: 本体 + 蓋 の 2 部品を返す。"""
    del case_spec
    hw = resolve_screws_hardware(case_config)
    validate_screws(case_config, hw)
    closure_cfg = case_config.get("closure", {}).get("screws", {})
    body = build_screw_bosses(body, closure_cfg, hw)
    lid = build_screw_holes(lid, closure_cfg, hw)
    return {
        "case-body": body,
        "case-lid": lid,
    }
