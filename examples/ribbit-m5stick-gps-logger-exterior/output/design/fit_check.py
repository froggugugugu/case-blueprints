"""fit_check.py — 嵌合・接合チェック(/fit-check skill の実装)

単体実行: python output/design/fit_check.py

役割:
  - パーツ同士の嵌合(リップ・蝶番組合せ・ねじ等)の干渉/クリアランスを点検
  - CAD 上の boolean intersect で重なり体積を計測
  - 過去事例ベースの推奨値と照らしてルールチェック

validator.py が「単一パーツの設計ルール」を見るのに対し、
fit_check.py は「複数パーツの嵌合」と「過去事例網羅」を担当する。

拡張方法:
  - 新しい嵌合機構: MECHANISMS に check 関数を追加
  - 新しいパーツペア: PART_PAIRS にエントリ追加
  - 意図的な重なり: ALLOWLIST に label / max_mm3 / 理由を記載
"""
import math
import yaml
from pathlib import Path

import cadquery as cq

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# ALLOWLIST: 構造上避けられない CAD 重なり(label / 上限 mm³ / 理由)
# ---------------------------------------------------------------------------
ALLOWLIST = [
    # 旧エントリ「本体ナックル右半円 × 蓋プレート -Y 端 1mm 帯」は
    # 2026-05-02 に lid_relief_clearance を導入し CAD レベルで解消したため削除。
]

# ---------------------------------------------------------------------------
# PART_PAIRS: 干渉解析するパーツの組み合わせ
# ---------------------------------------------------------------------------
PART_PAIRS = [
    {
        "name": "case-body × case-lid (closed)",
        "files": ["case-body.step", "case-lid.step"],
        "transform": "identity",  # 両者とも閉じた状態の world coord で生成済み
    },
]


# ---------------------------------------------------------------------------
# 設定読み込み
# ---------------------------------------------------------------------------
def load_configs():
    project_cfg = yaml.safe_load((PROJECT_ROOT / "project-config.yaml").read_text())
    case_spec = yaml.safe_load((PROJECT_ROOT / "input" / "requirements" / "case-spec.yaml").read_text())
    case_config = yaml.safe_load((PROJECT_ROOT / "input" / "design-params" / "case-config.yaml").read_text())
    objects = {}
    for p in (PROJECT_ROOT / "input" / "objects").glob("*.yaml"):
        obj = yaml.safe_load(p.read_text())
        objects[obj["id"]] = obj
    return project_cfg, case_spec, case_config, objects


def calc_internal(objects, case_config):
    obj_clear = case_config["internal"]["object_clearance"]
    cable_bend = case_config["internal"]["cable_bend_allowance"]
    z_margin = case_config["internal"].get("z_margin", 0.0)
    battery = objects["mobile-battery"]["dimensions"]
    m5 = objects["m5stick-s3"]["dimensions"]
    gps = objects["gps-module"]["dimensions"]
    ix = max(battery["height"], m5["height"], gps["height"]) + cable_bend
    iy = battery["width"] + max(m5["width"], gps["width"]) + obj_clear
    iz = max(battery["depth"], m5["depth"] + gps["depth"] + obj_clear) + z_margin
    return ix, iy, iz


def calc_outer(internal, case_config):
    ix, iy, iz = internal
    wall = case_config["walls"]["thickness"]
    bottom = case_config["walls"]["bottom_thickness"]
    return ix + bottom, iy + 2 * wall, iz + 2 * wall


# ---------------------------------------------------------------------------
# レポート組み立てユーティリティ
# ---------------------------------------------------------------------------
class Report:
    """セクション・行を蓄積して最後に Markdown を組み立てる。"""

    def __init__(self):
        self.sections = []  # [(title, [(level, msg), ...])]
        self.counts = {"pass": 0, "warn": 0, "fail": 0, "info": 0}

    def section(self, title):
        self.sections.append((title, []))

    def _add(self, level, msg):
        if not self.sections:
            self.section("Misc")
        self.sections[-1][1].append((level, msg))
        if level in self.counts:
            self.counts[level] += 1

    def ok(self, msg):    self._add("pass", msg)
    def warn(self, msg):  self._add("warn", msg)
    def fail(self, msg):  self._add("fail", msg)
    def info(self, msg):  self._add("info", msg)

    def render(self):
        lines = ["# Fit-Check Report", ""]
        c = self.counts
        lines.append("## サマリー")
        lines.append(f"- ✅ Pass: {c['pass']}")
        lines.append(f"- ⚠ Warning: {c['warn']}")
        lines.append(f"- ❌ Fail: {c['fail']}")
        if c["info"]:
            lines.append(f"- ℹ Info: {c['info']}")
        lines.append("")
        for title, items in self.sections:
            lines.append(f"## {title}")
            for level, msg in items:
                icon = {"pass": "✅", "warn": "⚠", "fail": "❌", "info": "ℹ"}[level]
                lines.append(f"- {icon} {msg}")
            lines.append("")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# A. 内寸マージン
# ---------------------------------------------------------------------------
def check_internal_margins(report, project_cfg, case_spec, case_config, objects):
    report.section("A. 内寸マージン")

    obj_clear = case_config["internal"]["object_clearance"]
    z_margin = case_config["internal"].get("z_margin", 0.0)

    # object_clearance
    if obj_clear >= 1.0:
        report.ok(f"object_clearance: {obj_clear} mm (推奨 ≥ 1.0)")
    elif obj_clear >= 0.5:
        report.warn(f"object_clearance: {obj_clear} mm < 1.0 推奨。FDM 反りで内寸が縮むリスク")
    else:
        report.fail(f"object_clearance: {obj_clear} mm < 0.5。オブジェクトが入らない可能性")

    # z_margin
    if z_margin >= 1.0:
        report.ok(f"z_margin: {z_margin} mm (推奨 ≥ 1.0)")
    elif z_margin >= 0.5:
        report.warn(f"z_margin: {z_margin} mm < 1.0 推奨")
    else:
        report.fail(f"z_margin: {z_margin} mm < 0.5")

    # 内寸 vs 実測
    ix, iy, iz = calc_internal(objects, case_config)
    report.info(f"計算内寸 (X×Y×Z): {ix:.1f} × {iy:.1f} × {iz:.1f} mm")


# ---------------------------------------------------------------------------
# B. リップ嵌合クリアランス
# ---------------------------------------------------------------------------
def check_lip_fit(report, case_spec, case_config):
    report.section("B. リップ嵌合クリアランス")

    lid_cfg = case_config.get("lid", {})
    fit = lid_cfg.get("fit_clearance", 0.0)
    hinge_extra = lid_cfg.get("lip_hinge_side_extra_clearance", 0.0)
    has_hinge = case_config.get("hinge", {}).get("enabled", False)

    # 全周共通
    if fit >= 0.4:
        report.ok(f"fit_clearance: {fit} mm (推奨 ≥ 0.4)")
    elif fit >= 0.3:
        report.warn(f"fit_clearance: {fit} mm < 0.4 推奨。FDM 公差で消えやすい")
    else:
        report.fail(f"fit_clearance: {fit} mm < 0.3。リップ嵌合不能の高リスク")

    if not has_hinge:
        report.info("蝶番なし — 蝶番側追加クリアランスは適用外")
        return

    # 蝶番側追加クリア
    total_hinge_side = fit + hinge_extra
    if total_hinge_side >= 1.0:
        report.ok(f"蝶番側総クリア: {total_hinge_side:.2f} mm (fit {fit} + extra {hinge_extra})")
    elif total_hinge_side >= 0.5:
        report.warn(f"蝶番側総クリア: {total_hinge_side:.2f} mm。蝶番ピンが Y を拘束するため ≥ 1.0 推奨")
    else:
        report.fail(f"蝶番側総クリア: {total_hinge_side:.2f} mm < 0.5。嵌合不能の高リスク")


# ---------------------------------------------------------------------------
# C. 蝶番設計
# ---------------------------------------------------------------------------
def check_hinge_design(report, case_spec, case_config, objects):
    report.section("C. 蝶番設計")

    h_cfg = case_config.get("hinge", {})
    if not h_cfg.get("enabled", False):
        report.info("蝶番なし")
        return

    # ナックル肉厚
    knuckle_d = h_cfg.get("knuckle_diameter", 6.0)
    pin_d = h_cfg.get("pin_diameter", 2.0)
    pin_clear = h_cfg.get("pin_clearance", 0.4)
    wall = (knuckle_d - (pin_d + pin_clear)) / 2
    if wall >= 1.5:
        report.ok(f"ナックル肉厚: {wall:.2f} mm (推奨 ≥ 1.5)")
    elif wall >= 1.0:
        report.warn(f"ナックル肉厚: {wall:.2f} mm。強度マージン不足、可能なら ≥ 1.5")
    else:
        report.fail(f"ナックル肉厚: {wall:.2f} mm < 1.0。割れリスク高")

    # ナックル Z 高さ
    n_body = h_cfg.get("knuckle_count_body", 2)
    n_lid = h_cfg.get("knuckle_count_lid", 1)
    z_clear = h_cfg.get("knuckle_clearance_z", 0.4)
    total = n_body + n_lid
    n_gaps = total - 1
    edge = z_clear

    ix, iy, iz = calc_internal(objects, case_config)
    _, _, oz = calc_outer((ix, iy, iz), case_config)
    knuckle_h = (oz - 2 * edge - n_gaps * z_clear) / total
    if knuckle_h >= 5.0:
        report.ok(f"ナックル Z 高さ: {knuckle_h:.2f} mm (推奨 ≥ 5)")
    elif knuckle_h >= 3.0:
        report.warn(f"ナックル Z 高さ: {knuckle_h:.2f} mm。短め、回転の安定性に注意")
    else:
        report.fail(f"ナックル Z 高さ: {knuckle_h:.2f} mm < 3。短すぎ")

    # pin_clearance
    if 0.4 <= pin_clear <= 0.6:
        report.ok(f"pin_clearance: {pin_clear} mm (推奨 0.4-0.6)")
    elif 0.3 <= pin_clear <= 0.7:
        report.warn(f"pin_clearance: {pin_clear} mm。やや tight or loose")
    else:
        report.fail(f"pin_clearance: {pin_clear} mm 推奨範囲外")

    # knuckle_clearance_z
    if 0.4 <= z_clear <= 0.6:
        report.ok(f"knuckle_clearance_z: {z_clear} mm (推奨 0.4-0.6)")
    elif z_clear >= 0.3:
        report.warn(f"knuckle_clearance_z: {z_clear} mm。tight、印刷誤差で固着リスク")
    else:
        report.fail(f"knuckle_clearance_z: {z_clear} mm < 0.3")

    # body_relief_clearance(壁埋込時)
    overlap_y = 1.0  # generator.py のデフォルト埋込量
    is_embedded = overlap_y > 0
    body_relief = h_cfg.get("body_relief_clearance", 0.0)
    if is_embedded:
        if body_relief >= 0.3:
            report.ok(f"body_relief_clearance: {body_relief} mm (壁埋込あり、推奨 ≥ 0.3)")
        elif body_relief >= 0.2:
            report.warn(f"body_relief_clearance: {body_relief} mm。狭め")
        else:
            report.fail(
                f"body_relief_clearance: {body_relief} mm。"
                f"蝶番ナックルが壁に埋まる設計では蓋シリンダーが本体壁に当たる。≥ 0.3 必須"
            )

    # lid_relief_clearance(壁埋込時、対称チェック)
    lid_relief = h_cfg.get("lid_relief_clearance", 0.0)
    if is_embedded:
        if lid_relief >= 0.3:
            report.ok(f"lid_relief_clearance: {lid_relief} mm (壁埋込あり、推奨 ≥ 0.3)")
        elif lid_relief >= 0.2:
            report.warn(f"lid_relief_clearance: {lid_relief} mm。狭め")
        else:
            report.fail(
                f"lid_relief_clearance: {lid_relief} mm。"
                f"本体ナックル +X 半円が蓋プレート -Y 端と干渉する。≥ 0.3 必須"
            )

    # lid_knuckle_extra_clearance_z
    lid_extra_z = h_cfg.get("lid_knuckle_extra_clearance_z", 0.0)
    if lid_extra_z > 0:
        if 0.3 <= lid_extra_z <= 0.5:
            report.ok(f"lid_knuckle_extra_clearance_z: {lid_extra_z} mm (本体固定運用、推奨 0.3-0.5)")
        else:
            report.warn(f"lid_knuckle_extra_clearance_z: {lid_extra_z} mm。範囲外")
    else:
        report.info("lid_knuckle_extra_clearance_z: 0 (本体・蓋を同時に再生成する運用)")


# ---------------------------------------------------------------------------
# D. CAD 干渉解析
# ---------------------------------------------------------------------------
def check_cad_interference(report):
    report.section("D. CAD 干渉解析")

    preview_dir = PROJECT_ROOT / "output" / "preview"

    for pair in PART_PAIRS:
        name = pair["name"]
        files = pair["files"]
        paths = [preview_dir / f for f in files]
        missing = [p for p in paths if not p.exists()]
        if missing:
            report.fail(f"{name}: STEP ファイルが見つからない: {[str(p) for p in missing]}")
            continue

        try:
            shapes = [cq.importers.importStep(str(p)) for p in paths]
            inter = shapes[0].intersect(shapes[1])
            try:
                volume = inter.val().Volume()
            except Exception:
                volume = 0.0  # intersection が空 solid の場合
        except Exception as e:
            report.fail(f"{name}: 解析失敗 {type(e).__name__}: {e}")
            continue

        allow_total = sum(item["max_mm3"] for item in ALLOWLIST)
        unalloweed = max(0.0, volume - allow_total)

        msg = f"{name}: 重なり総体積 {volume:.1f} mm³ / allowlist 合計 {allow_total:.1f} mm³ / 未許容 {unalloweed:.1f} mm³"

        if unalloweed >= 100.0:
            report.fail(msg + "  → 重大な干渉あり。/review-fix で修正を")
        elif unalloweed >= 1.0:
            report.warn(msg + "  → 小さな未許容干渉。意図的なら ALLOWLIST に追加")
        else:
            report.ok(msg)

    if ALLOWLIST:
        report.info("ALLOWLIST 登録項目:")
        for item in ALLOWLIST:
            report.info(f"  - {item['label']} (max {item['max_mm3']} mm³)  — {item['reason']}")


# ---------------------------------------------------------------------------
# E. 印刷可能性
# ---------------------------------------------------------------------------
def check_printability(report, project_cfg, case_spec, case_config, objects):
    report.section("E. 印刷可能性")

    bed = project_cfg["print_settings"]["printer_bed"]
    min_w = project_cfg["design_rules"]["min_wall_thickness"]

    wall = case_config["walls"]["thickness"]
    bottom = case_config["walls"]["bottom_thickness"]
    if wall >= min_w and bottom >= min_w:
        report.ok(f"壁厚: side {wall} / bottom {bottom} ≥ min {min_w}")
    else:
        report.fail(f"壁厚不足: side {wall} / bottom {bottom} (min {min_w})")

    # printer_bed
    ix, iy, iz = calc_internal(objects, case_config)
    ox, oy, oz = calc_outer((ix, iy, iz), case_config)
    knuckle_d = case_config.get("hinge", {}).get("knuckle_diameter", 0.0)
    body_dims = (ox + knuckle_d, oy, oz)

    body_sorted = sorted(body_dims, reverse=True)
    bed_sorted = sorted(bed, reverse=True)
    if all(body_sorted[i] <= bed_sorted[i] for i in range(3)):
        report.ok(f"本体は printer_bed に収まる: {body_dims} ≤ {bed}")
    else:
        report.fail(f"本体が printer_bed に入らない: {body_dims} > {bed}")

    # print_orientation
    po = case_spec.get("case", {}).get("print_orientation")
    if po and po.get("body") and po.get("lid"):
        report.ok(f"print_orientation: body={po['body']} / lid={po['lid']}")
    else:
        report.warn("print_orientation が未定義 — case-spec.yaml を確認")


# ---------------------------------------------------------------------------
# F. 将来拡張: 追加の嵌合機構
# ---------------------------------------------------------------------------
MECHANISMS = {
    # "screw_boss":       check_screw_boss,
    # "snap_hook":        check_snap_hook,
    # "magnet_mount":     check_magnet_mount,
    # "insert_post":      check_insert_post,
}

def check_mechanisms(report, case_spec, case_config):
    if not MECHANISMS:
        return
    report.section("F. その他の嵌合機構")
    for name, fn in MECHANISMS.items():
        try:
            fn(report, case_spec, case_config)
        except Exception as e:
            report.fail(f"{name}: {type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    project_cfg, case_spec, case_config, objects = load_configs()

    report = Report()
    check_internal_margins(report, project_cfg, case_spec, case_config, objects)
    check_lip_fit(report, case_spec, case_config)
    check_hinge_design(report, case_spec, case_config, objects)
    check_printability(report, project_cfg, case_spec, case_config, objects)
    check_cad_interference(report)
    check_mechanisms(report, case_spec, case_config)

    out_path = PROJECT_ROOT / "output" / "reports" / "fit-check.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report.render() + "\n")

    c = report.counts
    print(f"✓ {out_path}")
    print(f"  ✅ {c['pass']} pass / ⚠ {c['warn']} warn / ❌ {c['fail']} fail")

    return c["fail"]


if __name__ == "__main__":
    raise SystemExit(0 if main() == 0 else 1)
