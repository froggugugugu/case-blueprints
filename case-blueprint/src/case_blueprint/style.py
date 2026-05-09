"""意匠(style)の中間表現と theme → パラメータ群の翻訳。

case-config.yaml の `style:` セクションを「中間言語」として、
ファジー要求(「未来感」「ファンシー」)を CAD パラメータに翻訳する。

設計方針:
- THEMES 辞書: 6 主要テーマの推奨パラメータ
- resolve_style(): theme + 明示値を deep merge(明示値優先)
- apply_style_to_case_config(): 解決済み style を case_config の派生値
  (fillet.outer_radius / decorative_pattern feature 等)に統合する
- 利用者の `/review-fix` での自然言語フィードバックをそのまま受け止める
  ため、解決後も style: セクションは保持する(再適用に備える)
"""

from __future__ import annotations

from typing import Any


# ===== 主要テーマの辞書 =====

# 角(fillets)・表面(surface)・全体半径(fillet_radius)の 3 軸で記述。
# 将来 silhouette が rectangular 以外に拡張されたら、本辞書も拡張する。

THEMES: dict[str, dict[str, Any]] = {
    "futuristic": {
        "fillets": {
            "outer_corners": "sharp",
            "edge_treatment": "chamfered_edge",
        },
        "surface": {
            "pattern": "hex_grid",
            "density": 0.35,
            "depth": 0.4,
            "side": "+Z",
        },
        "fillet_radius": {"outer": 0.5, "inner": 0.3, "bottom": 0.5},
    },
    "minimal": {
        "fillets": {
            "outer_corners": "medium",
            "edge_treatment": "fillet",
        },
        "surface": {"pattern": "none"},
        "fillet_radius": {"outer": 2.0, "inner": 0.5, "bottom": 1.0},
    },
    "fancy": {
        "fillets": {
            "outer_corners": "large",
            "edge_treatment": "fillet",
        },
        "surface": {
            "pattern": "dot_pattern",
            "density": 0.5,
            "depth": 0.6,
            "side": "+Z",
        },
        "fillet_radius": {"outer": 4.0, "inner": 1.0, "bottom": 2.0},
    },
    "industrial": {
        "fillets": {
            "outer_corners": "sharp",
            "edge_treatment": "mixed",
        },
        "surface": {
            "pattern": "linear_groove",
            "density": 0.3,
            "depth": 0.5,
            "side": "+Z",
        },
        "fillet_radius": {"outer": 0.8, "inner": 0.3, "bottom": 0.5},
    },
    "cute": {
        "fillets": {
            "outer_corners": "extra_large",
            "edge_treatment": "fillet",
        },
        "surface": {"pattern": "none"},
        "fillet_radius": {"outer": 5.0, "inner": 1.5, "bottom": 3.0},
    },
    "retro": {
        "fillets": {
            "outer_corners": "medium",
            "edge_treatment": "fillet",
        },
        "surface": {
            "pattern": "linear_groove",
            "density": 0.25,
            "depth": 0.6,
            "side": "+Z",
        },
        "fillet_radius": {"outer": 2.5, "inner": 0.6, "bottom": 1.5},
    },
}


def list_themes() -> list[str]:
    """利用可能なテーマ ID 一覧。"""
    return sorted(THEMES.keys())


# ===== 解決ロジック =====


def _deep_merge(base: dict, override: dict) -> dict:
    """dict を再帰的にマージ(override 優先、base は変更しない)。"""
    result = {**base}
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def resolve_style(style_cfg: dict | None) -> dict:
    """style.theme を辞書で解決し、明示値で上書き。

    入力:
        style_cfg: case_config["style"] 相当
    出力:
        解決後の dict(theme 由来 + 明示値)。fillet_radius / fillets /
        surface / silhouette / reference_images 等を含む。

    custom テーマや theme なしのときは、明示値のみで構成する。
    """
    if not style_cfg:
        return {}
    theme = style_cfg.get("theme", "custom")
    base = THEMES.get(theme, {}).copy() if theme != "custom" else {}

    # 明示値を deep merge(theme 由来を override)
    override = {k: v for k, v in style_cfg.items() if k != "theme"}
    return _deep_merge(base, override)


def apply_style_to_case_config(case_config: dict) -> dict:
    """resolve_style 結果から case_config の派生値を統合する。

    - fillet_radius → case_config.fillet.outer/inner/bottom_radius(未指定のみ)
    - surface.pattern → features に decorative_pattern を追加(未指定のみ)

    既存の case_config.fillet / features に明示値があれば尊重する
    (ハイブリッドゾーンの精神、constitution §1)。

    返り値は **新しい dict**(元の case_config は変更しない)。
    """
    style = case_config.get("style") or {}
    if not style:
        return case_config

    resolved = resolve_style(style)

    # コピーを作って編集
    new_cfg = {**case_config}
    new_cfg["fillet"] = {**new_cfg.get("fillet", {})}

    fillet_radius = resolved.get("fillet_radius", {})
    for key, dest in [("outer", "outer_radius"),
                      ("inner", "inner_radius"),
                      ("bottom", "bottom_radius")]:
        if dest not in new_cfg["fillet"] and key in fillet_radius:
            new_cfg["fillet"][dest] = float(fillet_radius[key])

    # surface.pattern を features に投影(none 以外のとき)
    surface = resolved.get("surface", {})
    pattern = surface.get("pattern", "none")
    if pattern != "none":
        # Note: features 配列は case-spec.yaml にあるので、ここでは
        # case_config に埋めず、generator.py 側で resolve_style + features
        # への投影を行う。本関数は fillet 派生値の統合に絞る。
        # (decorative_pattern を case-spec.features[] に直接書く運用が標準)
        pass

    return new_cfg


def derive_decorative_features(style_cfg: dict | None) -> list[dict]:
    """style.surface から decorative_pattern feature を生成。

    case-spec.yaml の features[] に既に decorative_pattern が手書きされて
    いる場合は generator が重複を避けるよう判定する。

    返り値: features 配列に append できる feature dict のリスト
    (style に surface.pattern が無ければ空リスト)。
    """
    if not style_cfg:
        return []
    resolved = resolve_style(style_cfg)
    surface = resolved.get("surface", {})
    pattern = surface.get("pattern", "none")
    if pattern == "none":
        return []

    feature = {
        "type": "decorative_pattern",
        "pattern": pattern,
        "side": surface.get("side", "+Z"),
        "density": float(surface.get("density", 0.3)),
        "depth": float(surface.get("depth", 0.4)),
    }
    if "pitch" in surface:
        feature["pitch"] = float(surface["pitch"])
    return [feature]
