"""features dispatcher の基盤。

case_spec.case.features[] の各 type に対応する実装関数を登録する。
generator.py は本モジュールの HANDLERS にハンドラを追加し、apply_features() で
全 features をディスパッチする。

オープン構造: 新 type が必要なら register() で追加するだけ。
"""

from __future__ import annotations

from typing import Callable, Any

# シグネチャ: handler(part, feature_dict, case_config) -> part
FeatureHandler = Callable[[Any, dict, dict], Any]

HANDLERS: dict[str, FeatureHandler] = {}


def register(feature_type: str) -> Callable[[FeatureHandler], FeatureHandler]:
    """デコレータ: @register("ventilation") で登録"""

    def deco(fn: FeatureHandler) -> FeatureHandler:
        HANDLERS[feature_type] = fn
        return fn

    return deco


def apply(part: Any, feature: dict, case_config: dict) -> Any:
    """1 つの feature を該当ハンドラに振り分ける。未登録 type は警告 print して素通し。"""
    ftype = feature.get("type")
    if ftype is None:
        return part
    handler = HANDLERS.get(ftype)
    if handler is None:
        print(f"[feature_registry] 未登録の type: {ftype}(generator.py に @register でハンドラを追加してください)")
        return part
    return handler(part, feature, case_config)


def apply_all(part: Any, features: list[dict], case_config: dict) -> Any:
    """features 配列を順に適用"""
    for f in features:
        part = apply(part, f, case_config)
    return part


def registered_types() -> list[str]:
    """登録済み type 一覧(デバッグ・/lead 用)"""
    return sorted(HANDLERS.keys())
