from __future__ import annotations

from case_blueprint import feature_registry


def test_register_and_apply():
    # クリーンスレートで隔離(他テストが汚さない)
    feature_registry.HANDLERS.clear()

    @feature_registry.register("test_feature")
    def handle(part, feature, cfg):
        return part + [feature["value"]]

    out = feature_registry.apply([], {"type": "test_feature", "value": 42}, {})
    assert out == [42]


def test_unknown_type_passthrough(capsys):
    feature_registry.HANDLERS.clear()
    out = feature_registry.apply("input", {"type": "unknown"}, {})
    assert out == "input"
    captured = capsys.readouterr()
    assert "未登録" in captured.out


def test_apply_all_chain():
    feature_registry.HANDLERS.clear()

    @feature_registry.register("inc")
    def handle(part, feature, cfg):
        return part + 1

    out = feature_registry.apply_all(0, [{"type": "inc"}, {"type": "inc"}, {"type": "inc"}], {})
    assert out == 3
