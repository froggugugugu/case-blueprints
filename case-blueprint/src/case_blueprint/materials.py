"""材料カタログ loader。

`src/case_blueprint/data/materials/<id>.yaml` の物性データを読み込む。
validators / closures が `material.id` を引いて推奨範囲を取得する。

利用者は project-config.yaml の `print_settings.default_material` で id を指定
(例: pla / petg / pla_plus / tpu / abs)。新材料を追加するには:
  1. data/materials/<id>.yaml を追加
  2. material.schema.yaml に準拠
  3. .claude/rules/materials-catalog.md に行を追加
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


DATA_DIR = Path(__file__).resolve().parent / "data" / "materials"


class MaterialNotFound(KeyError):
    """指定の material id が見つからない。"""


@lru_cache(maxsize=None)
def _load_raw(material_id: str) -> dict[str, Any]:
    path = DATA_DIR / f"{material_id}.yaml"
    if not path.exists():
        available = sorted(p.stem for p in DATA_DIR.glob("*.yaml"))
        raise MaterialNotFound(
            f"material '{material_id}' が見つかりません。"
            f"利用可能: {available}"
        )
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def load(material_id: str) -> dict[str, Any]:
    """材料データを取得(キャッシュあり)。"""
    return _load_raw(material_id)


def list_available() -> list[str]:
    """data/materials/*.yaml の id 一覧。"""
    return sorted(p.stem for p in DATA_DIR.glob("*.yaml"))


def fit_clearance_range(material_id: str, mechanism: str) -> tuple[float, float]:
    """機構別の推奨 fit_clearance 範囲 (min, max) を返す。

    mechanism: snap_fit / hinge_pin / magnet_pocket
    """
    data = load(material_id)
    fc = data.get("fit_clearance", {})
    if mechanism not in fc:
        raise KeyError(f"material={material_id} に {mechanism} の推奨範囲がない")
    rng = fc[mechanism]
    return float(rng[0]), float(rng[1])


def check_fit_clearance(
    material_id: str,
    mechanism: str,
    value: float,
    *,
    label: str = "fit_clearance",
) -> tuple[bool, str]:
    """値が推奨範囲内かを返す。範囲外なら (False, 警告メッセージ)。

    Returns:
        (in_range, message)
    """
    lo, hi = fit_clearance_range(material_id, mechanism)
    if lo <= value <= hi:
        return True, f"✅ {label}={value} は {material_id}/{mechanism} 推奨範囲 [{lo}, {hi}]"
    return False, (
        f"⚠ {label}={value} は {material_id}/{mechanism} 推奨範囲 [{lo}, {hi}] の外。"
        f"印刷ばらつき次第で固すぎ/ゆるすぎになる可能性"
    )


def shrinkage_pct(material_id: str) -> float:
    """線収縮率 (%) を返す。寸法補正用。"""
    return float(load(material_id)["shrinkage"]["linear_pct"])


def max_service_temp_c(material_id: str) -> float:
    return float(load(material_id)["environmental"]["max_service_temp_c"])


def is_outdoor_acceptable(material_id: str) -> bool:
    return bool(load(material_id).get("environmental", {}).get("outdoor_use_acceptable", False))


def slicer_recommendations(material_id: str) -> dict[str, Any]:
    """slicer-notes.md に埋めるための推奨スライサー設定。

    /export SKILL や slicer-advisor agent が呼ぶ。`data/materials/<id>.yaml`
    の物性データから派生値(初層補正・既定層高・警告)を組み立てる。
    """
    data = load(material_id)
    th = data["thermal"]
    ps = data["print_settings"]
    nozzle_lo, nozzle_hi = th["print_temp_c"]
    bed_lo, bed_hi = th["bed_temp_c"]
    layer_lo, layer_hi = ps["layer_height_mm"]
    infill_lo, infill_hi = ps["infill_pct"]
    speed = ps.get("print_speed_mm_s", [30, 60])

    # 既定層高: 0.20mm が範囲内ならそれ、範囲外なら中央値
    if layer_lo <= 0.20 <= layer_hi:
        layer_recommended = 0.20
    else:
        layer_recommended = round((layer_lo + layer_hi) / 2, 2)

    # 推奨ノズル/ベッドは中央値、初層は +5°C
    nozzle_recommended = round((nozzle_lo + nozzle_hi) / 2)
    bed_recommended = round((bed_lo + bed_hi) / 2)

    # ファン: PLA 100%、PETG 30-50%、ABS は密閉時 off
    if material_id in ("pla", "pla_plus"):
        fan = {"first_layer_pct": 0, "subsequent_pct": 100}
    elif material_id == "petg":
        fan = {"first_layer_pct": 0, "subsequent_pct": 40}
    elif material_id == "tpu":
        fan = {"first_layer_pct": 0, "subsequent_pct": 30}
    elif material_id == "abs":
        fan = {"first_layer_pct": 0, "subsequent_pct": 10, "note": "密閉チャンバー時はほぼ off"}
    else:
        fan = {"first_layer_pct": 0, "subsequent_pct": 50, "note": "材料に応じて調整"}

    return {
        "material_id": material_id,
        "display_name": data["display_name"],
        "nozzle_temp_c": {
            "min": nozzle_lo,
            "max": nozzle_hi,
            "recommended": nozzle_recommended,
            "first_layer": nozzle_recommended + 5,
        },
        "bed_temp_c": {
            "min": bed_lo,
            "max": bed_hi,
            "recommended": bed_recommended,
            "first_layer": bed_recommended + 5,
        },
        "enclosure_required": bool(th.get("enclosure_required", False)),
        "layer_height_mm": {
            "min": layer_lo,
            "max": layer_hi,
            "recommended": layer_recommended,
        },
        "infill_pct": {
            "min": infill_lo,
            "max": infill_hi,
            "recommended": int((infill_lo + infill_hi) / 2),
            "outdoor_or_hard_use": min(infill_hi, max(40, int((infill_lo + infill_hi) / 2) + 10)),
        },
        "print_speed_mm_s": {
            "min": speed[0],
            "max": speed[1],
            "recommended": int((speed[0] + speed[1]) / 2),
            "wall_top_layer": int(speed[0] * 0.75),
        },
        "fan": fan,
        "support_difficulty": ps["support_difficulty"],
        "warnings": _slicer_warnings(data),
    }


def _slicer_warnings(data: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if data["thermal"].get("enclosure_required"):
        warnings.append(f"{data['display_name']} は密閉チャンバー推奨(反り抑制・層間接着安定)")
    if float(data["shrinkage"]["linear_pct"]) >= 0.6:
        warnings.append(
            f"線収縮率 {data['shrinkage']['linear_pct']}%、反り対策(brim 5mm 以上 / 接地面拡大)推奨"
        )
    if data["mechanical"].get("layer_adhesion") == "low":
        warnings.append("層間接着が弱い、強度方向と層方向を直交させる印刷向きに")
    if data["environmental"].get("uv_resistance") == "low":
        warnings.append("UV 耐性が低い、屋外運用なら材料変更を検討")
    if data["mechanical"].get("stiffness") == "low":
        warnings.append("剛性が低い、構造強度が必要な部位には不向き")
    return warnings
