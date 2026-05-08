"""closure.method = hinge_lever のリファレンス実装の骨格。

`/hinged-lid init` がこのモジュールを import し、`build_hinge_lever_closure`
が呼ばれて body / lid / latch-lever の 3 部品を返す。

実装は **骨格のみ**:hardware 解決と各 builder の入口だけを定義し、
具体的な CadQuery geometry は generator.py 側で個別ケースに合わせて埋める
(/hinged-lid skill が SKILL.md の雛形を参照して生成)。
"""

from __future__ import annotations

from typing import Any

from . import register


def resolve_hardware(case_config: dict) -> dict:
    """hardware preset から具体値を解決。custom はそのまま返す。"""
    hw = case_config.get("hardware", {})
    preset = hw.get("preset", "custom")
    if preset == "custom":
        return hw
    # 将来:プリセット辞書を別ファイルに切り出してロード
    # 現状は hw に既に展開されている想定で素通し
    return hw


def validate_scale_constraints(hinge_cfg: dict, hardware: dict) -> None:
    """P17 対策: scale 後にナックル厚が下限を割らないかを事前検証。"""
    knuckle = hinge_cfg.get("knuckle", {})
    pattern = knuckle.get("pattern", ["body", "lid", "body"])
    z_clearance = knuckle.get("z_clearance", 0.4)

    fastener = hardware.get("hinge", {}).get("fastener", {})
    pin_length = float(fastener.get("length", 0))
    if pin_length <= 0:
        return  # hardware 未設定なら検証スキップ

    end_clear = z_clearance * 2  # ピン両端クリア
    n = len(pattern)
    gaps = n - 1
    usable = pin_length - end_clear
    thickness = (usable - gaps * z_clearance) / n
    assert thickness >= 2.0, (
        f"P17: ナックル厚 {thickness:.2f}mm < 2.0mm。"
        f"hardware.hinge.fastener.length を増やすか pattern のナックル数を増やしてください。"
    )


def build_hinge_assembly(body: Any, lid: Any, hinge_cfg: dict, hardware: dict) -> tuple[Any, Any]:
    """両側 2 アセンブリのナックル交互生成。
    実装は generator.py 側で具体ケースに合わせて埋める。
    """
    validate_scale_constraints(hinge_cfg, hardware)
    return body, lid


def build_latch_pivot(lid: Any, latch_cfg: dict, hardware: dict) -> Any:
    """蓋側:レバー回転軸の 2 ナックル。"""
    return lid


def build_latch_catch(body: Any, latch_cfg: dict, hardware: dict) -> Any:
    """本体側:catch ピン保持の 2 ナックル。A方式 cap_side。"""
    cap_side = latch_cfg.get("catch", {}).get("cap_side", "right")
    assert cap_side in ("left", "right"), f"cap_side は left/right のみ: {cap_side}"
    return body


def build_latch_lever(latch_cfg: dict, hardware: dict) -> Any:
    """独立部品:上端ピン穴 + 下端フック + finger_lift タブ。"""
    # placeholder: generator.py 側で CadQuery 実装
    return None


@register("hinge_lever")
def build_hinge_lever_closure(body: Any, lid: Any, case_spec: dict, case_config: dict) -> dict[str, Any]:
    """closure dispatcher エントリ: 3 部品を組み立てる。"""
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
