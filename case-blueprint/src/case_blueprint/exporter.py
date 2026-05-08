"""STEP / STL / 3MF エクスポート。

CadQuery が必要(generator.py からのみ呼ばれる前提)。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def export_part(part: Any, base_path: str | Path, formats: tuple[str, ...] = ("step", "stl")) -> list[Path]:
    """パーツを指定形式で複数出力。返り値は出力ファイルパスの一覧。"""
    import cadquery as cq  # 遅延 import(jsonschema-only テストを cq 抜きで通すため)

    base = Path(base_path)
    base.parent.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for fmt in formats:
        out = base.with_suffix(f".{fmt}")
        if fmt == "step":
            cq.exporters.export(part, str(out))
        elif fmt == "stl":
            cq.exporters.export(part, str(out))
        elif fmt == "3mf":
            cq.exporters.export(part, str(out), exportType="3MF")
        else:
            raise ValueError(f"未対応の format: {fmt}")
        written.append(out)
    return written


def export_assembly(parts: dict[str, Any], output_dir: str | Path, formats: tuple[str, ...] = ("step", "stl")) -> list[Path]:
    """複数パーツを一括出力。parts は {basename: cq.Workplane} の辞書。"""
    out_dir = Path(output_dir)
    written: list[Path] = []
    for name, part in parts.items():
        written.extend(export_part(part, out_dir / name, formats=formats))
    return written
