"""features 実装モジュール群。

各 feature の `apply_<type>` と `validate_<type>` を src 側に固定する。
generator.py は `from case_blueprint import features` するだけで全 type が
register され、`feature_registry.apply_all(part, features, case_config)` で
ディスパッチされる。

`feature_registry` 自体は registry の機構のみ提供し、実装はここに置く。

座標系規約(features-catalog.md):
- side は軸記法に正規化(`+X`/`-X`/`+Y`/`-Y`/`+Z`/`-Z`)。通称(top / front 等)も
  受け付けるが、内部で軸記法に変換する。
- position は対象 face の **面中心からのオフセット**(u, v)。CadQuery の
  `faces(...).workplane().center(u, v)` がそのまま使える。

CadQuery は遅延 import(validate のみのテストでは cadquery 不要)。
"""

from __future__ import annotations

# side の正規化テーブル
SIDE_TO_AXIS: dict[str, str] = {
    "+X": "+X", "-X": "-X",
    "+Y": "+Y", "-Y": "-Y",
    "+Z": "+Z", "-Z": "-Z",
    "top": "+Z", "bottom": "-Z",
    "front": "-Y", "back": "+Y",   # 正面 = -Y(case-spec の慣習)
    "right": "+X", "left": "-X",
}

# 軸記法 -> CadQuery faces セレクタ
AXIS_TO_CQ_FACE: dict[str, str] = {
    "+X": ">X", "-X": "<X",
    "+Y": ">Y", "-Y": "<Y",
    "+Z": ">Z", "-Z": "<Z",
}


def normalize_side(side: str) -> str:
    """通称・軸記法を軸記法に正規化。未知なら ValueError。"""
    if side not in SIDE_TO_AXIS:
        raise ValueError(
            f"未知の side: {side!r}。"
            f"許容: {sorted(SIDE_TO_AXIS.keys())}"
        )
    return SIDE_TO_AXIS[side]


def cq_face_selector(side: str) -> str:
    """side(通称含む)から CadQuery faces セレクタへ変換。"""
    return AXIS_TO_CQ_FACE[normalize_side(side)]


# 副作用 import で各 feature module の register() が走る。
# `from case_blueprint import features` または `import case_blueprint.features`
# だけで HANDLERS が埋まる。
from . import ventilation  # noqa: E402,F401
from . import cable_port  # noqa: E402,F401
from . import display_window  # noqa: E402,F401
