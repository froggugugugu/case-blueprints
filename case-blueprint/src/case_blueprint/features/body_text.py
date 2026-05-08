"""features type = body_text の実装。

凸/凹文字を指定 face に焼く。フォントは `input/fonts/<font_file>` に
ローカル配置必須(配布禁止フォントの誤コミット回避は README 参照)。

パラメータ:
- side: 配置面(必須)
- text: 文字列(必須)
- font_file: input/fonts/ 直下のファイル名(必須、.ttf/.otf)
- emboss_depth: 正値=凸、負値=凹(既定 0.6 mm = 0.2mm 層 × 3 層相当)
- size: 文字高(mm、既定 8.0)
- position: 任意 [u, v](既定 [0, 0])
- font_dir: フォント検索先(既定 "input/fonts")。テスト等で上書き可
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..feature_registry import register
from . import cq_face_selector, normalize_side


def validate_body_text(feature: dict, case_config: dict, font_dir: str | None = None) -> None:
    del case_config
    if "side" not in feature:
        raise AssertionError("body_text: side が必須")
    normalize_side(feature["side"])

    text = feature.get("text", "").strip()
    if not text:
        raise AssertionError("body_text: text が空")

    if "font_file" not in feature:
        raise AssertionError("body_text: font_file が必須")

    depth = float(feature.get("emboss_depth", 0.6))
    if depth == 0:
        raise AssertionError("body_text.emboss_depth は 0 以外(正=凸、負=凹)")

    abs_depth = abs(depth)
    if abs_depth < 0.4:
        raise AssertionError(
            f"body_text.emboss_depth=|{depth}| < 0.4mm。FDM では潰れる(P4 参照)"
        )
    if abs_depth > 1.5:
        raise AssertionError(
            f"body_text.emboss_depth=|{depth}| > 1.5mm。範囲外(0.4-1.5mm 推奨)"
        )

    size = float(feature.get("size", 8.0))
    if size <= 0:
        raise AssertionError(f"body_text.size={size} は正の値")

    # font ファイル存在チェック(`font_dir` を上書き可能、テスト用)
    fdir = font_dir or feature.get("font_dir", "input/fonts")
    fpath = Path(fdir) / feature["font_file"]
    if not fpath.exists():
        raise AssertionError(
            f"body_text: フォント {fpath} が見つかりません。"
            f"input/fonts/ にダウンロードして配置してください"
            f"(README フォント節 + LICENSE-*.txt の取り扱い参照)"
        )


@register("body_text")
def apply_body_text(part: Any, feature: dict, case_config: dict) -> Any:
    validate_body_text(feature, case_config)
    import cadquery as cq

    side = feature["side"]
    selector = cq_face_selector(side)
    text = feature["text"]
    fdir = feature.get("font_dir", "input/fonts")
    font_path = str((Path(fdir) / feature["font_file"]).resolve())
    depth = float(feature.get("emboss_depth", 0.6))
    size = float(feature.get("size", 8.0))
    pos = feature.get("position", [0.0, 0.0])
    u, v = float(pos[0]), float(pos[1])

    # 凸: union(extrude 正方向)、凹: cut(extrude 負方向 = 表面から内側へ)
    text_solid = (
        part.faces(selector).workplane(centerOption="CenterOfBoundBox")
        .center(u, v)
        .text(text, size, abs(depth), fontPath=font_path, combine=False)
    )
    if depth > 0:
        return part.union(text_solid)
    return part.cut(text_solid)
