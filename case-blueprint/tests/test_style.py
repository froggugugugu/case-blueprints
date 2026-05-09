"""src/case_blueprint/style.py のテスト。

THEMES 辞書 / resolve_style / apply_style_to_case_config /
derive_decorative_features を網羅。
"""

from __future__ import annotations

import pytest

from case_blueprint import style


# ===== THEMES 辞書 =====


def test_themes_list_contains_main_six():
    themes = style.list_themes()
    for t in ["futuristic", "minimal", "fancy", "industrial", "cute", "retro"]:
        assert t in themes


@pytest.mark.parametrize("theme", ["futuristic", "minimal", "fancy", "industrial", "cute", "retro"])
def test_each_theme_has_required_sections(theme):
    t = style.THEMES[theme]
    assert "fillets" in t
    assert "surface" in t
    assert "fillet_radius" in t
    assert "outer" in t["fillet_radius"]


# ===== resolve_style =====


class TestResolveStyle:
    def test_empty_returns_empty(self):
        assert style.resolve_style({}) == {}
        assert style.resolve_style(None) == {}

    def test_theme_only_uses_dictionary(self):
        out = style.resolve_style({"theme": "minimal"})
        assert out["fillets"]["outer_corners"] == "medium"
        assert out["surface"]["pattern"] == "none"
        assert out["fillet_radius"]["outer"] == 2.0

    def test_explicit_value_overrides_theme(self):
        """明示値が theme 由来の値を上書きする"""
        out = style.resolve_style({
            "theme": "futuristic",
            "fillets": {"outer_corners": "large"},  # theme は sharp だが large で上書き
        })
        assert out["fillets"]["outer_corners"] == "large"
        assert out["fillets"]["edge_treatment"] == "chamfered_edge"  # theme 由来は残る

    def test_custom_theme_uses_only_explicit(self):
        """custom テーマは明示値のみ"""
        out = style.resolve_style({
            "theme": "custom",
            "fillets": {"outer_corners": "sharp"},
        })
        assert out["fillets"]["outer_corners"] == "sharp"
        assert "fillet_radius" not in out  # theme 由来の値は入らない

    def test_unknown_theme_defaults_to_empty_base(self):
        """未知テーマでも明示値は通る"""
        out = style.resolve_style({
            "theme": "weird_theme",
            "fillets": {"outer_corners": "medium"},
        })
        assert out["fillets"]["outer_corners"] == "medium"

    def test_deep_merge_preserves_unmodified_keys(self):
        """surface.density だけ上書きしても他の surface 値は残る"""
        out = style.resolve_style({
            "theme": "industrial",
            "surface": {"density": 0.5},
        })
        assert out["surface"]["density"] == 0.5
        assert out["surface"]["pattern"] == "linear_groove"  # theme 由来


# ===== apply_style_to_case_config =====


class TestApplyStyleToCaseConfig:
    def test_no_style_returns_unchanged(self):
        cfg = {"walls": {"thickness": 2.4}}
        assert style.apply_style_to_case_config(cfg) == cfg

    def test_theme_fills_fillet_radius(self):
        cfg = {"style": {"theme": "futuristic"}}
        out = style.apply_style_to_case_config(cfg)
        assert out["fillet"]["outer_radius"] == 0.5
        assert out["fillet"]["inner_radius"] == 0.3

    def test_explicit_fillet_takes_priority(self):
        """既存の fillet.outer_radius が theme 由来より優先される"""
        cfg = {
            "style": {"theme": "futuristic"},
            "fillet": {"outer_radius": 5.0},
        }
        out = style.apply_style_to_case_config(cfg)
        assert out["fillet"]["outer_radius"] == 5.0  # 明示値維持
        assert out["fillet"]["inner_radius"] == 0.3  # 未指定は theme 由来

    def test_does_not_mutate_input(self):
        """入力 dict を破壊しない"""
        cfg = {"style": {"theme": "minimal"}}
        out = style.apply_style_to_case_config(cfg)
        assert "fillet" not in cfg  # 元は変わらない
        assert "fillet" in out


# ===== derive_decorative_features =====


class TestDeriveDecorativeFeatures:
    def test_no_style_returns_empty(self):
        assert style.derive_decorative_features({}) == []
        assert style.derive_decorative_features(None) == []

    def test_pattern_none_returns_empty(self):
        out = style.derive_decorative_features({"theme": "minimal"})
        assert out == []

    def test_futuristic_yields_hex_grid(self):
        out = style.derive_decorative_features({"theme": "futuristic"})
        assert len(out) == 1
        assert out[0]["type"] == "decorative_pattern"
        assert out[0]["pattern"] == "hex_grid"
        assert out[0]["side"] == "+Z"
        assert out[0]["density"] == 0.35

    def test_explicit_overrides_theme(self):
        out = style.derive_decorative_features({
            "theme": "futuristic",
            "surface": {"density": 0.6, "side": "+Y"},
        })
        assert out[0]["density"] == 0.6
        assert out[0]["side"] == "+Y"
        assert out[0]["pattern"] == "hex_grid"  # theme 由来
