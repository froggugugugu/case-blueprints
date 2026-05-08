"""closure.method 別の実装(ファミリ)。

各 closure module は CLOSURE_HANDLERS にビルダ関数を登録する。
generator.py は handler を呼んで body / lid / その他部品を組む。
"""

from __future__ import annotations

from typing import Callable, Any

# シグネチャ: handler(body, lid, case_spec, case_config) -> dict[name, part]
ClosureHandler = Callable[[Any, Any, dict, dict], dict[str, Any]]

CLOSURE_HANDLERS: dict[str, ClosureHandler] = {}


def register(method: str) -> Callable[[ClosureHandler], ClosureHandler]:
    def deco(fn: ClosureHandler) -> ClosureHandler:
        CLOSURE_HANDLERS[method] = fn
        return fn

    return deco


def build(method: str, body: Any, lid: Any, case_spec: dict, case_config: dict) -> dict[str, Any]:
    handler = CLOSURE_HANDLERS.get(method)
    if handler is None:
        # 未登録 method はそのまま返す(snap_fit 等の単純な closure は generator.py 側で完結)
        return {"case-body": body, "case-lid": lid}
    return handler(body, lid, case_spec, case_config)
