"""closure.method = magnetic のリファレンス実装の骨格。

蓋にネオジム磁石、本体に鉄板(または磁石)を埋め込み、磁力で吸着。
ねじ・ヒンジ無しの最薄型。蓋は完全分離型。

generator.py 側で `build_magnetic_closure` を呼ぶ。具体的な CadQuery geometry は
generator.py が個別ケースに合わせて埋める。
"""

from __future__ import annotations

from typing import Any

from . import register


def validate_magnetic(case_config: dict, hardware: dict) -> None:
    """磁石ポケット深さ・吸着面クリアランスのガード。"""
    closure_cfg = case_config.get("closure", {}).get("magnetic", {})
    magnet = hardware.get("closure", {}).get("magnet", {})
    magnet_thickness = float(magnet.get("thickness", 0))
    pocket_depth = float(closure_cfg.get("pocket_depth", 0))

    if magnet_thickness:
        assert pocket_depth >= magnet_thickness + 0.2, (
            f"pocket_depth={pocket_depth} は magnet.thickness({magnet_thickness}) + 0.2mm 以上が必要"
        )

    count = int(closure_cfg.get("count", 0))
    assert count >= 2, (
        f"closure.magnetic.count={count} は 2 個以上を推奨(対角配置で蓋の浮きを抑える)"
    )

    # 蓋と本体の合わせ面は完全密着しないので gap を許容する設計
    air_gap = float(closure_cfg.get("air_gap", 0.1))
    assert 0 < air_gap <= 0.3, (
        f"air_gap={air_gap} は 0.1-0.3mm を推奨(印刷層の積層誤差を吸収)"
    )


def resolve_magnetic_hardware(case_config: dict) -> dict:
    return case_config.get("hardware", {})


def build_magnet_pockets_lid(lid: Any, closure_cfg: dict, hardware: dict) -> Any:
    """蓋側の磁石ポケット(押し込み or 接着保持)。"""
    del closure_cfg, hardware  # placeholder: generator.py が override する
    return lid


def build_steel_plate_pockets_body(body: Any, closure_cfg: dict, hardware: dict) -> Any:
    """本体側の鉄板または対向磁石ポケット。"""
    del closure_cfg, hardware  # placeholder: generator.py が override する
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
    lid = build_magnet_pockets_lid(lid, closure_cfg, hw)
    body = build_steel_plate_pockets_body(body, closure_cfg, hw)
    return {
        "case-body": body,
        "case-lid": lid,
    }
