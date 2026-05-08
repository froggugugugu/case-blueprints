"""closure.method 別の実装(ファミリ)。

各 closure module は CLOSURE_HANDLERS にビルダ関数を登録する。
generator.py は handler を呼んで body / lid / その他部品を組む。

オープン構造: 新 method が必要なら register() で追加するだけ。
"""

from __future__ import annotations

from typing import Callable, Any

# シグネチャ: handler(body, lid, case_spec, case_config) -> dict[name, part]
ClosureHandler = Callable[[Any, Any, dict, dict], dict[str, Any]]

CLOSURE_HANDLERS: dict[str, ClosureHandler] = {}


def assert_lid_axis_supported(
    case_spec: dict, supported: tuple[str, ...] = ("+Z",)
) -> str:
    """closure の build_*_closure 冒頭で軸サポートを検査する共通ヘルパ。

    現在 closure 実装はすべて lid_axis="+Z" 前提(蓋が上に乗る、本体は底接地)。
    `+X` 等を選んだ場合は generator.py 側で rotate して渡すか、将来の
    align_to_lid_axis() 対応を待つ必要がある。

    未対応軸を選んだ場合は NotImplementedError で fail-fast する。
    "未指定 → +Z" のフォールバックも明示的にここで行う。
    """
    axis = case_spec.get("case", {}).get("closure", {}).get("lid_axis", "+Z")
    if axis not in supported:
        raise NotImplementedError(
            f"closure.lid_axis={axis!r} は未対応(現在 {list(supported)} のみサポート)。"
            f"generator.py で rotate して +Z 軸へ正規化してから closure を呼ぶか、"
            f"将来の align_to_lid_axis() 対応をお待ちください"
        )
    return axis


def register(method: str) -> Callable[[ClosureHandler], ClosureHandler]:
    def deco(fn: ClosureHandler) -> ClosureHandler:
        CLOSURE_HANDLERS[method] = fn
        return fn

    return deco


def build(method: str, body: Any, lid: Any, case_spec: dict, case_config: dict) -> dict[str, Any]:
    handler = CLOSURE_HANDLERS.get(method)
    if handler is None:
        # 未登録 method はそのまま返す(generator.py 側で完結する場合)
        return {"case-body": body, "case-lid": lid}
    return handler(body, lid, case_spec, case_config)


def registered_methods() -> list[str]:
    """登録済み closure.method 一覧(/lead や validator が使う)。"""
    return sorted(CLOSURE_HANDLERS.keys())


# import 副作用で各 closure module の register() が走る。
# 利用者プロジェクトで `from case_blueprint import closures` した時点で
# CLOSURE_HANDLERS が埋まる。
from . import hinge_lever  # noqa: E402,F401
from . import snap_fit  # noqa: E402,F401
from . import screws  # noqa: E402,F401
from . import magnetic  # noqa: E402,F401
from . import snap_lip_with_hinge  # noqa: E402,F401
