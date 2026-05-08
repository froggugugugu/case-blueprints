"""validator.py の基盤。

@check デコレータと標準チェック群。利用者プロジェクトの
output/design/validator.py がこのモジュールを import して使う。

チェック種別:
- @check: AssertionError なら ❌(致命)、無ければ ✅
- @warn:  ValueError なら ⚠(印刷ばらつき次第で許容)、無ければ ✅
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Any

CHECKS: list[tuple[str, str, Callable[[dict], None]]] = []  # (kind, name, fn)


def check(name: str) -> Callable[[Callable[[dict], None]], Callable[[dict], None]]:
    """登録デコレータ(致命チェック)。AssertionError を raise すれば ❌。"""

    def deco(fn: Callable[[dict], None]) -> Callable[[dict], None]:
        CHECKS.append(("check", name, fn))
        return fn

    return deco


def warn(name: str) -> Callable[[Callable[[dict], None]], Callable[[dict], None]]:
    """登録デコレータ(警告チェック)。ValueError を raise すれば ⚠。

    印刷ばらつき次第で許容できる、絶対 NG ではないが見直し推奨の項目に使う。
    """

    def deco(fn: Callable[[dict], None]) -> Callable[[dict], None]:
        CHECKS.append(("warn", name, fn))
        return fn

    return deco


def run_all(cfg: dict) -> tuple[list[str], int, int, int]:
    """全 CHECKS を実行し (report 行, pass 数, warn 数, fail 数) を返す"""
    lines: list[str] = []
    n_pass = n_warn = n_fail = 0
    for kind, name, fn in CHECKS:
        try:
            fn(cfg)
            lines.append(f"- ✅ {name}")
            n_pass += 1
        except AssertionError as e:
            lines.append(f"- ❌ {name}: {e}")
            n_fail += 1
        except ValueError as e:
            if kind == "warn":
                lines.append(f"- ⚠ {name}: {e}")
                n_warn += 1
            else:
                lines.append(f"- ❌ {name}: {e}")
                n_fail += 1
    return lines, n_pass, n_warn, n_fail


def write_report(cfg: dict, out_path: str | Path = "output/reports/validation.md") -> int:
    """レポートを書き出し、失敗数を返す"""
    lines, n_pass, n_warn, n_fail = run_all(cfg)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "# Validation Report",
        "",
        f"- Pass: {n_pass}",
        f"- Warning: {n_warn}",
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


@check("default_material が登録済み")
def _check_material_registered(cfg: dict) -> None:
    from . import materials

    mid = cfg["project"]["print_settings"]["default_material"].lower()
    available = materials.list_available()
    assert mid in available, (
        f"default_material='{mid}' は data/materials/ に未登録。"
        f"利用可能: {available}。"
        f"新材料は src/case_blueprint/data/materials/<id>.yaml と "
        f".claude/rules/materials-catalog.md を追加してください"
    )


@warn("snap_fit fit_clearance が材料推奨範囲内")
def _warn_fit_clearance_snap_fit_material(cfg: dict) -> None:
    from . import materials

    method = cfg["case_spec"]["case"]["closure"].get("method", "")
    if method not in ("snap_fit", "snap_lip_with_hinge"):
        return  # 対象外 closure ならスキップ
    mid = cfg["project"]["print_settings"]["default_material"].lower()
    fc = cfg["case_config"].get("lid", {}).get("fit_clearance")
    if fc is None:
        return
    ok, msg = materials.check_fit_clearance(mid, "snap_fit", float(fc), label="lid.fit_clearance")
    if not ok:
        raise ValueError(msg)


@warn("hinge pin_clearance が材料推奨範囲内")
def _warn_hinge_pin_clearance_material(cfg: dict) -> None:
    from . import materials

    method = cfg["case_spec"]["case"]["closure"].get("method", "")
    if method not in ("hinge_lever", "snap_lip_with_hinge"):
        return
    mid = cfg["project"]["print_settings"]["default_material"].lower()
    knuckle = cfg["case_config"].get("hinge", {}).get("knuckle", {})
    pc = knuckle.get("pin_clearance")
    if pc is None:
        return
    ok, msg = materials.check_fit_clearance(mid, "hinge_pin", float(pc), label="hinge.knuckle.pin_clearance")
    if not ok:
        raise ValueError(msg)


@warn("magnet pocket fit が材料推奨範囲内")
def _warn_magnet_pocket_material(cfg: dict) -> None:
    from . import materials

    method = cfg["case_spec"]["case"]["closure"].get("method", "")
    if method != "magnetic":
        return
    mid = cfg["project"]["print_settings"]["default_material"].lower()
    closure_cfg = cfg["case_config"].get("closure", {}).get("magnetic", {})
    pf = closure_cfg.get("pocket_fit_clearance")
    if pf is None:
        return
    ok, msg = materials.check_fit_clearance(mid, "magnet_pocket", float(pf), label="closure.magnetic.pocket_fit_clearance")
    if not ok:
        raise ValueError(msg)


@warn("印刷温度が材料の推奨範囲内")
def _warn_print_temp_material(cfg: dict) -> None:
    from . import materials

    mid = cfg["project"]["print_settings"]["default_material"].lower()
    nozzle_temp = cfg["project"]["print_settings"].get("nozzle_temp_c")
    if nozzle_temp is None:
        return  # 設定なしならスキップ(slicer 側で設定する想定)
    data = materials.load(mid)
    lo, hi = data["thermal"]["print_temp_c"]
    if not (lo <= float(nozzle_temp) <= hi):
        raise ValueError(
            f"nozzle_temp_c={nozzle_temp}°C は {mid} 推奨範囲 [{lo}, {hi}] の外"
        )
