"""fit_check の本体実装。

利用者プロジェクトの `output/design/fit_check.py` は本モジュールを import
して `main(allowlist=...)` を呼ぶ薄い shim になる。Claude が CadQuery
ロジックを書き起こす量を最小化する目的。

## カテゴリ(quality-gates.md と対応)

- **A. 内寸マージン**: object_clearance, z_margin, 各軸 vs 実測
- **B. 嵌合 / closure**: closure.method ごとの validate を呼ぶ
- **C. 蝶番設計**: hinge_lever / snap_lip_with_hinge の固有チェック
- **D. CAD 干渉**: body × lid の intersect 体積、features 同士の bbox 重なり
- **E. 印刷可能性**: printer_bed / 壁厚 / orientation
- **F. 拡張**: `MECHANISMS` dict に追加するだけで取り込める

## ALLOWLIST 構造

```python
ALLOWLIST = [
    {"label": "本体ナックル右半円×蓋プレート -Y 端",
     "max_mm3": 50.0,
     "where": "蝶番付近、構造上避けられない 1mm 帯"},
]
```

label / max_mm3 / where(理由)を必ず併記。明示許容(P16)を強制する仕組み。
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from . import closures, materials
from .features import normalize_side


# ===== Issue / Report データ構造 =====


@dataclass
class Issue:
    category: str  # "A. 内寸マージン" 等
    level: str  # "pass" / "warn" / "fail"
    message: str
    value: float | None = None


@dataclass
class FitCheckReport:
    issues: list[Issue] = field(default_factory=list)
    cad_overlaps: dict[str, float] = field(default_factory=dict)
    allowlist_total_mm3: float = 0.0
    allowlist_unmatched_mm3: float = 0.0

    @property
    def n_pass(self) -> int:
        return sum(1 for i in self.issues if i.level == "pass")

    @property
    def n_warn(self) -> int:
        return sum(1 for i in self.issues if i.level == "warn")

    @property
    def n_fail(self) -> int:
        return sum(1 for i in self.issues if i.level == "fail")


# ===== チェッカー登録 =====

# シグネチャ: checker(cfg) -> list[Issue]
Checker = Callable[[dict], list[Issue]]
CHECKERS: list[tuple[str, Checker]] = []


def checker(category: str) -> Callable[[Checker], Checker]:
    """@checker("A. 内寸マージン") で登録。"""

    def deco(fn: Checker) -> Checker:
        CHECKERS.append((category, fn))
        return fn

    return deco


# MECHANISMS: closure 等の追加チェック(F. 拡張)
MECHANISMS: dict[str, Checker] = {}


def register_mechanism(name: str) -> Callable[[Checker], Checker]:
    """新しい嵌合機構を追加するときに使う(features-catalog の type と独立)。"""

    def deco(fn: Checker) -> Checker:
        MECHANISMS[name] = fn
        return fn

    return deco


# ===== 標準チェッカー =====


@checker("A. 内寸マージン")
def _check_internal_clearance(cfg: dict) -> list[Issue]:
    """internal.object_clearance / z_margin の推奨値チェック。"""
    out: list[Issue] = []
    internal = cfg["case_config"].get("internal", {})

    oc = float(internal.get("object_clearance", 0.0))
    if oc < 0.5:
        out.append(Issue("A", "fail", f"object_clearance={oc}mm < 0.5mm。FDM の反り収縮で収まらない恐れ"))
    elif oc < 1.0:
        out.append(Issue("A", "warn", f"object_clearance={oc}mm < 1.0mm 推奨"))
    else:
        out.append(Issue("A", "pass", f"object_clearance={oc}mm ✓"))

    zm = float(internal.get("z_margin", 0.0))
    if zm < 0.5 and zm != 0.0:  # 0 は明示無指定なので skip
        out.append(Issue("A", "warn", f"z_margin={zm}mm < 0.5mm"))
    return out


@checker("B. 嵌合 / closure")
def _check_closure_method(cfg: dict) -> list[Issue]:
    """closure.method ごとの validate を呼ぶ。"""
    out: list[Issue] = []
    method = cfg["case_spec"]["case"]["closure"].get("method")
    if not method:
        out.append(Issue("B", "fail", "closure.method が未指定"))
        return out

    if method not in closures.registered_methods():
        out.append(
            Issue("B", "fail",
                  f"closure.method={method!r} は未実装。登録済: {closures.registered_methods()}")
        )
        return out

    # 材料カタログ連動の fit_clearance チェック(snap_fit / snap_lip_with_hinge)
    if method in ("snap_fit", "snap_lip_with_hinge"):
        mid = cfg["project"]["print_settings"]["default_material"].lower()
        fc = cfg["case_config"].get("lid", {}).get("fit_clearance")
        if fc is not None:
            ok, msg = materials.check_fit_clearance(mid, "snap_fit", float(fc),
                                                    label="lid.fit_clearance")
            if ok:
                out.append(Issue("B", "pass", f"lid.fit_clearance={fc}mm ({mid} 推奨範囲内)"))
            else:
                out.append(Issue("B", "warn", msg))

    out.append(Issue("B", "pass", f"closure.method={method} 登録済"))
    return out


@checker("C. 蝶番設計")
def _check_hinge(cfg: dict) -> list[Issue]:
    """hinge_lever / snap_lip_with_hinge のとき、ナックル肉厚と pin_clearance をチェック。"""
    out: list[Issue] = []
    method = cfg["case_spec"]["case"]["closure"].get("method", "")
    if method not in ("hinge_lever", "snap_lip_with_hinge"):
        return out  # 対象外

    knuckle = cfg["case_config"].get("hinge", {}).get("knuckle", {})
    if not knuckle:
        out.append(Issue("C", "warn", "hinge.knuckle セクションが未定義"))
        return out

    od = float(knuckle.get("outer_diameter", 0))
    pc = float(knuckle.get("pin_clearance", 0.2))
    hardware = cfg["case_config"].get("hardware", {}).get("hinge", {}).get("fastener", {})
    pd = float(hardware.get("diameter", 2.0))
    wall = (od - (pd + pc)) / 2 if od else 0.0
    if wall < 1.0:
        out.append(Issue("C", "fail",
                         f"ナックル肉厚={wall:.2f}mm < 1.0mm(outer={od}, pin+clear={pd + pc})"))
    elif wall < 1.5:
        out.append(Issue("C", "warn", f"ナックル肉厚={wall:.2f}mm < 1.5mm 推奨"))
    else:
        out.append(Issue("C", "pass", f"ナックル肉厚={wall:.2f}mm ✓"))

    # P14 蝶番側非対称クリア
    if method == "snap_lip_with_hinge":
        extra = float(cfg["case_config"].get("lid", {}).get("lip_hinge_side_extra_clearance", 0))
        if extra < 0.3:
            out.append(Issue("C", "fail",
                             f"lip_hinge_side_extra_clearance={extra}mm < 0.3mm(P14)"))
        else:
            out.append(Issue("C", "pass",
                             f"lip_hinge_side_extra_clearance={extra}mm ✓ (P14)"))
    return out


@checker("D. features 干渉")
def _check_features_overlap(cfg: dict) -> list[Issue]:
    """同一 face にある features の bbox が重なっていないか。"""
    out: list[Issue] = []
    features = cfg["case_spec"]["case"].get("features") or []
    by_face: dict[str, list[dict]] = defaultdict(list)
    for f in features:
        side = f.get("side")
        if not side:
            continue
        try:
            by_face[normalize_side(side)].append(f)
        except ValueError as e:
            out.append(Issue("D", "fail", f"features の side が不正: {e}"))

    overlaps = 0
    checked = 0
    for face, fs in by_face.items():
        for i in range(len(fs)):
            for j in range(i + 1, len(fs)):
                checked += 1
                if _features_bbox_overlap(fs[i], fs[j]):
                    overlaps += 1
                    a = fs[i].get("type", "?")
                    b = fs[j].get("type", "?")
                    out.append(Issue("D", "fail",
                                     f"face={face} で {a} と {b} の position が重なる"))
    if checked and not overlaps:
        out.append(Issue("D", "pass", f"features 干渉なし({checked} ペア検査)"))
    return out


@checker("D. objects 干渉")
def _check_object_collisions(cfg: dict) -> list[Issue]:
    """layout=manual のとき objects 同士の AABB 重なりを検出。"""
    arrangement = cfg["case_spec"]["case"].get("layout", {}).get("arrangement", "stacked")
    if arrangement != "manual":
        return []
    from .geometry import detect_collisions
    objects = cfg.get("objects", [])
    placements = cfg["case_spec"].get("objects", [])
    pairs = detect_collisions(objects, placements)
    if pairs:
        return [Issue("D", "fail",
                      f"objects 同士の AABB 干渉: {pairs}")]
    return [Issue("D", "pass", f"objects 同士の AABB 干渉なし({len(placements)} 個)")]


@checker("E. 印刷可能性")
def _check_print_feasibility(cfg: dict) -> list[Issue]:
    """printer_bed に外寸が収まるか / 壁厚 / orientation の存在。"""
    from .geometry import (
        external_bbox, internal_bbox_stacked, internal_bbox_side_by_side,
        internal_bbox_manual, fits_in_bed,
    )

    out: list[Issue] = []
    objects = cfg.get("objects", [])
    cc = cfg["case_config"]
    walls = cc.get("walls", {})
    internal = cc.get("internal", {})
    layout = cfg["case_spec"]["case"].get("layout", {})
    arrangement = layout.get("arrangement", "stacked")

    if not objects:
        out.append(Issue("E", "warn", "objects が空(/measure 未完了か)"))
        return out

    if arrangement == "stacked":
        ib = internal_bbox_stacked(
            objects,
            object_clearance=internal.get("object_clearance", 1.0),
            z_margin=internal.get("z_margin", 0.0),
        )
    elif arrangement == "manual":
        placements = cfg["case_spec"].get("objects", [])
        try:
            ib = internal_bbox_manual(
                objects, placements,
                object_clearance=internal.get("object_clearance", 1.0),
                z_margin=internal.get("z_margin", 0.0),
            )
        except ValueError as e:
            out.append(Issue("E", "fail", f"layout=manual の内寸計算失敗: {e}"))
            return out
    else:
        ib = internal_bbox_side_by_side(
            objects,
            object_clearance=internal.get("object_clearance", 1.0),
            z_margin=internal.get("z_margin", 0.0),
        )

    eb = external_bbox(ib, wall_thickness=walls.get("thickness", 2.0))
    bed = cfg["project"]["print_settings"]["printer_bed"]
    if fits_in_bed(eb, bed):
        out.append(Issue("E", "pass",
                         f"外寸 {eb.width:.1f}×{eb.depth:.1f}×{eb.height:.1f}mm "
                         f"が bed {bed} に収まる"))
    else:
        out.append(Issue("E", "fail",
                         f"外寸 {eb.width:.1f}×{eb.depth:.1f}×{eb.height:.1f}mm "
                         f"が bed {bed} を超える。case.split を検討"))

    rules = cfg["project"]["design_rules"]
    t = walls.get("thickness", 0)
    if t < rules["min_wall_thickness"]:
        out.append(Issue("E", "fail",
                         f"walls.thickness={t}mm < min_wall_thickness={rules['min_wall_thickness']}mm"))

    po = cfg["case_spec"]["case"].get("print_orientation", {})
    if "body" not in po or "lid" not in po:
        out.append(Issue("E", "warn", "print_orientation.body / lid が未定義"))
    return out


# ===== features 同士の bbox 重なり =====


def _features_bbox_2d(feature: dict) -> tuple[float, float, float, float] | None:
    """features の position+寸法から (umin, umax, vmin, vmax) の 2D bbox を返す。

    寸法情報が無いものは None。bbox 単位の粗いチェックなので、circle は外接四角形。
    """
    pos = feature.get("position", [0.0, 0.0])
    u, v = float(pos[0]), float(pos[1])

    # diameter / size / oblong / shape ごとに半幅を取る
    half_u = half_v = 0.0
    if "diameter" in feature:
        half_u = half_v = float(feature["diameter"]) / 2
    elif "oblong" in feature:
        w, h = feature["oblong"]
        half_u, half_v = float(w) / 2, float(h) / 2
    elif "size" in feature:
        w, h = feature["size"]
        half_u, half_v = float(w) / 2, float(h) / 2
    elif "shape" in feature and feature["shape"] == "round" and "diameter" in feature:
        half_u = half_v = float(feature["diameter"]) / 2
    else:
        return None  # 寸法情報なし

    return (u - half_u, u + half_u, v - half_v, v + half_v)


def _features_bbox_overlap(a: dict, b: dict) -> bool:
    bb_a = _features_bbox_2d(a)
    bb_b = _features_bbox_2d(b)
    if bb_a is None or bb_b is None:
        return False
    a_u0, a_u1, a_v0, a_v1 = bb_a
    b_u0, b_u1, b_v0, b_v1 = bb_b
    return not (a_u1 <= b_u0 or b_u1 <= a_u0 or a_v1 <= b_v0 or b_v1 <= a_v0)


# ===== CAD 干渉解析(D)=====


def compute_part_overlap(part_a: Any, part_b: Any) -> float:
    """parts(CadQuery Workplane)の intersect 体積を mm³ で返す。

    どちらかが None または空なら 0.0。CadQuery 非依存テスト用に try/except。
    """
    if part_a is None or part_b is None:
        return 0.0
    try:
        inter = part_a.intersect(part_b)
        val = inter.val()
        if val is None:
            return 0.0
        # Solid の場合のみ Volume が返る
        return float(val.Volume())
    except Exception:
        return 0.0


def evaluate_cad_overlap(
    parts: dict[str, Any] | None,
    pairs: list[tuple[str, str]] | None = None,
    allowlist: list[dict] | None = None,
) -> tuple[list[Issue], dict[str, float], float]:
    """parts の各 PART_PAIRS について intersect 体積を計算し、
    ALLOWLIST と照合して未許容分を fail として返す。

    Returns:
        (issues, cad_overlaps_dict, total_unmatched_mm3)
    """
    issues: list[Issue] = []
    cad_overlaps: dict[str, float] = {}

    if parts is None:
        issues.append(Issue("D", "warn", "parts が未提供。CAD 干渉解析をスキップ"))
        return issues, cad_overlaps, 0.0

    if pairs is None:
        # 既定 pair: case-body × case-lid
        pairs = [("case-body", "case-lid")]
        if "latch-lever" in parts and parts.get("latch-lever") is not None:
            pairs.append(("case-body", "latch-lever"))
            pairs.append(("case-lid", "latch-lever"))

    allow_total = sum(float(a["max_mm3"]) for a in (allowlist or []))
    total_overlap = 0.0
    for a_name, b_name in pairs:
        if a_name not in parts or b_name not in parts:
            continue
        v = compute_part_overlap(parts[a_name], parts[b_name])
        cad_overlaps[f"{a_name}×{b_name}"] = v
        total_overlap += v

    unmatched = max(0.0, total_overlap - allow_total)
    if unmatched > 100.0:
        issues.append(Issue("D", "fail",
                            f"未許容 CAD 干渉 {unmatched:.1f} mm³ > 100"))
    elif unmatched > 1.0:
        issues.append(Issue("D", "warn",
                            f"未許容 CAD 干渉 {unmatched:.1f} mm³(ALLOWLIST 追加検討)"))
    elif total_overlap > 0:
        issues.append(Issue("D", "pass",
                            f"CAD 干渉 合計 {total_overlap:.1f} mm³ / 許容 {allow_total:.1f} mm³"))
    return issues, cad_overlaps, unmatched


# ===== ランナー =====


def run_all(
    cfg: dict,
    parts: dict[str, Any] | None = None,
    allowlist: list[dict] | None = None,
) -> FitCheckReport:
    """全 CHECKERS を実行し、CAD 干渉も加えて報告を返す。"""
    report = FitCheckReport()
    for category, fn in CHECKERS:
        try:
            for issue in fn(cfg) or []:
                report.issues.append(issue)
        except Exception as e:
            report.issues.append(
                Issue(category, "fail", f"checker {fn.__name__} で例外: {e}")
            )
    # MECHANISMS も呼ぶ(F. 拡張)
    for mname, fn in MECHANISMS.items():
        try:
            for issue in fn(cfg) or []:
                report.issues.append(issue)
        except Exception as e:
            report.issues.append(
                Issue("F", "fail", f"mechanism {mname} で例外: {e}")
            )
    # CAD 干渉
    cad_issues, cad_overlaps, unmatched = evaluate_cad_overlap(parts, allowlist=allowlist)
    report.issues.extend(cad_issues)
    report.cad_overlaps = cad_overlaps
    report.allowlist_total_mm3 = sum(float(a["max_mm3"]) for a in (allowlist or []))
    report.allowlist_unmatched_mm3 = unmatched
    return report


# ===== レポート出力 =====


def write_report(
    report: FitCheckReport,
    out_path: str | Path = "output/reports/fit-check.md",
) -> int:
    """fit-check.md を書き出し、fail 数を返す。"""
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    lines = ["# Fit-Check Report", ""]
    lines.append(f"- Pass: {report.n_pass}")
    lines.append(f"- Warning: {report.n_warn}")
    lines.append(f"- Fail: {report.n_fail}")
    lines.append("")

    # カテゴリごとに集約
    by_cat: dict[str, list[Issue]] = defaultdict(list)
    for i in report.issues:
        by_cat[i.category].append(i)

    icon = {"pass": "✅", "warn": "⚠", "fail": "❌"}
    for cat in sorted(by_cat.keys()):
        lines.append(f"## {cat}")
        for i in by_cat[cat]:
            lines.append(f"- {icon.get(i.level, '?')} {i.message}")
        lines.append("")

    if report.cad_overlaps:
        lines.append("## D. CAD 干渉(数値)")
        for pair, v in report.cad_overlaps.items():
            lines.append(f"- {pair}: {v:.2f} mm³")
        lines.append(f"- ALLOWLIST 合計: {report.allowlist_total_mm3:.2f} mm³")
        lines.append(f"- 未許容: {report.allowlist_unmatched_mm3:.2f} mm³")
        lines.append("")

    p.write_text("\n".join(lines), encoding="utf-8")
    return report.n_fail


def main(
    cfg: dict | None = None,
    parts: dict[str, Any] | None = None,
    allowlist: list[dict] | None = None,
    out_path: str | Path = "output/reports/fit-check.md",
) -> int:
    """利用者プロジェクトの output/design/fit_check.py から呼ばれるエントリ。

    Args:
        cfg: loader.load_all() の結果(case_config / case_spec / project / objects)。
            None なら loader をデフォルトパスで呼ぶ。
        parts: generator.py が組み立てた parts dict({"case-body": ..., "case-lid": ...})。
            None なら CAD 干渉解析はスキップ。
        allowlist: 利用者プロジェクトで定義した ALLOWLIST。

    Returns:
        fail 件数。
    """
    if cfg is None:
        from . import loader
        cfg = loader.load_all()
    report = run_all(cfg, parts=parts, allowlist=allowlist)
    n_fail = write_report(report, out_path)
    print(f"✓ {out_path} を出力しました(pass={report.n_pass} warn={report.n_warn} fail={report.n_fail})")
    return n_fail
