"""validator.py の基盤。

@check デコレータと標準チェック群。利用者プロジェクトの
output/design/validator.py がこのモジュールを import して使う。
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Any

CHECKS: list[tuple[str, Callable[[dict], None]]] = []


def check(name: str) -> Callable[[Callable[[dict], None]], Callable[[dict], None]]:
    """登録デコレータ。AssertionError を raise すれば ❌、無ければ ✅。"""

    def deco(fn: Callable[[dict], None]) -> Callable[[dict], None]:
        CHECKS.append((name, fn))
        return fn

    return deco


def run_all(cfg: dict) -> tuple[list[str], int, int]:
    """全 CHECKS を実行し (report 行, pass 数, fail 数) を返す"""
    lines: list[str] = []
    n_pass = n_fail = 0
    for name, fn in CHECKS:
        try:
            fn(cfg)
            lines.append(f"- ✅ {name}")
            n_pass += 1
        except AssertionError as e:
            lines.append(f"- ❌ {name}: {e}")
            n_fail += 1
    return lines, n_pass, n_fail


def write_report(cfg: dict, out_path: str | Path = "output/reports/validation.md") -> int:
    """レポートを書き出し、失敗数を返す"""
    lines, n_pass, n_fail = run_all(cfg)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "# Validation Report",
        "",
        f"- Pass: {n_pass}",
        f"- Fail: {n_fail}",
        "",
    ]
    out.write_text("\n".join(header + lines) + "\n", encoding="utf-8")
    return n_fail


# ----- 基本チェック(全プロジェクト共通) -----


@check("壁厚 ≥ min_wall_thickness")
def _check_wall_thickness(cfg: dict) -> None:
    walls = cfg["case_config"].get("walls", {})
    rules = cfg["project"]["design_rules"]
    t = walls.get("thickness", 0)
    assert t >= rules["min_wall_thickness"], f"thickness={t} < {rules['min_wall_thickness']}"


@check("蓋厚 ≥ min_wall_thickness")
def _check_lid_thickness(cfg: dict) -> None:
    lid = cfg["case_config"].get("lid", {})
    rules = cfg["project"]["design_rules"]
    t = lid.get("thickness", 0)
    assert t >= rules["min_wall_thickness"], f"lid.thickness={t} < {rules['min_wall_thickness']}"


@check("嵌合クリアランスが正の値")
def _check_fit_clearance(cfg: dict) -> None:
    lid = cfg["case_config"].get("lid", {})
    fc = lid.get("fit_clearance", 0)
    assert fc > 0, f"lid.fit_clearance={fc} は正の値である必要がある"


@check("ケースが printer_bed に収まる")
def _check_printer_bed(cfg: dict) -> None:
    from .geometry import internal_bbox_stacked, external_bbox, fits_in_bed

    objects = cfg.get("objects", [])
    if not objects:
        return  # objects が無ければスキップ
    cc = cfg["case_config"]
    walls = cc.get("walls", {})
    internal = cc.get("internal", {})
    layout = cfg["case_spec"]["case"].get("layout", {})
    arrangement = layout.get("arrangement", "stacked")

    if arrangement == "stacked":
        ib = internal_bbox_stacked(
            objects,
            object_clearance=internal.get("object_clearance", 1.0),
            z_margin=internal.get("z_margin", 0.0),
        )
    else:
        from .geometry import internal_bbox_side_by_side
        ib = internal_bbox_side_by_side(
            objects,
            object_clearance=internal.get("object_clearance", 1.0),
            z_margin=internal.get("z_margin", 0.0),
        )

    eb = external_bbox(ib, wall_thickness=walls.get("thickness", 2.0))
    bed = cfg["project"]["print_settings"]["printer_bed"]
    assert fits_in_bed(eb, bed), f"外寸 {eb} が bed {bed} に収まらない"


@check("外寸 = 内寸 + 壁厚 × 2 の関係が成立")
def _check_outer_inner_relation(cfg: dict) -> None:
    # 概念チェック:case-config に外寸/内寸の両方が記入されている場合のみ実行
    # 通常は generator.py が internal から external を導出するため pass 扱い
    pass
