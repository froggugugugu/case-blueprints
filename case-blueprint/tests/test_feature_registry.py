from __future__ import annotations

import pytest

from case_blueprint import feature_registry


@pytest.fixture(autouse=True)
def isolate_handlers():
    """各テストの前後で HANDLERS を保存・復元する。

    過去は HANDLERS.clear() を直接呼んでいたが、それだと src 側 features が
    副作用 import で登録した状態を破壊し、後続の test_features.py が落ちる。
    """
    saved = dict(feature_registry.HANDLERS)
    feature_registry.HANDLERS.clear()
    try:
        yield
    finally:
        feature_registry.HANDLERS.clear()
        feature_registry.HANDLERS.update(saved)


def test_register_and_apply():
    @feature_registry.register("test_feature")
    def handle(part, feature, cfg):
        return part + [feature["value"]]

    out = feature_registry.apply([], {"type": "test_feature", "value": 42}, {})
    assert out == [42]


def test_unknown_type_passthrough(capsys):
    out = feature_registry.apply("input", {"type": "unknown"}, {})
    assert out == "input"
    captured = capsys.readouterr()
    assert "未登録" in captured.out


def test_apply_all_chain():
    @feature_registry.register("inc")
    def handle(part, feature, cfg):
        return part + 1

    out = feature_registry.apply_all(0, [{"type": "inc"}, {"type": "inc"}, {"type": "inc"}], {})
    assert out == 3
