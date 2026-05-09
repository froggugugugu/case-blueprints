"""silhouette(本体外形)別の素体生成モジュール。

`/style` skill の `style.silhouette` キーに対応する形状を register。
generator.py は `silhouettes.build(name, internal, walls, lid_cfg, style_cfg)`
を呼んで `{"body_blank": ..., "lid_blank": ...}` を受け取る。

L2 段階の実装(2026-05 時点):

- `rectangular`: 既存の box ベース(既定)
- `rounded`: 角丸矩形(垂直エッジに fillet)
- `hex`: 六角プリズム(将来予約、L2-B)
- `capsule`: 両端半円(将来予約、L2-C)

未実装の silhouette を要求された場合は `rectangular` にフォールバックし、
print で警告する(意匠は試行錯誤領域、エラーで止めない)。

closure / features の多くは body / lid の bbox 内省で動くため、
`rectangular` / `rounded` 程度の差なら closure 工事は不要(bbox は box の
外接矩形を返すため)。`hex` / `capsule` で closure 5 種が動くかは個別検証
が必要(L2-B のスコープ)。
"""

from __future__ import annotations

from typing import Any, Callable

# シグネチャ: handler(internal, walls, lid_cfg, style_cfg) -> {"body_blank", "lid_blank"}
SilhouetteBuilder = Callable[..., dict[str, Any]]
SILHOUETTES: dict[str, SilhouetteBuilder] = {}


def register(name: str) -> Callable[[SilhouetteBuilder], SilhouetteBuilder]:
    def deco(fn: SilhouetteBuilder) -> SilhouetteBuilder:
        SILHOUETTES[name] = fn
        return fn

    return deco


def registered_silhouettes() -> list[str]:
    return sorted(SILHOUETTES.keys())


def build(
    name: str,
    internal: Any,
    walls: dict,
    lid_cfg: dict,
    style_cfg: dict | None = None,
) -> dict[str, Any]:
    """silhouette ディスパッチ。未登録は rectangular フォールバック。"""
    handler = SILHOUETTES.get(name)
    if handler is None:
        if name and name != "rectangular":
            print(
                f"[silhouettes] silhouette={name!r} は未実装、rectangular に "
                f"フォールバック(利用可能: {registered_silhouettes()})"
            )
        handler = SILHOUETTES["rectangular"]
    return handler(internal, walls, lid_cfg, style_cfg or {})


# 副作用 import で各 silhouette が register される
from . import rectangular  # noqa: E402,F401
from . import rounded  # noqa: E402,F401
