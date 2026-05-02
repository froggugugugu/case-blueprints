"""validator.py — 設計の整合性をチェックする。
単体実行: python output/design/validator.py
"""
import yaml
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

CHECKS = []


def check(name):
    def wrap(fn):
        CHECKS.append((name, fn))
        return fn
    return wrap


def load_configs():
    project_cfg = yaml.safe_load((PROJECT_ROOT / "project-config.yaml").read_text())
    case_spec = yaml.safe_load((PROJECT_ROOT / "input" / "requirements" / "case-spec.yaml").read_text())
    case_config = yaml.safe_load((PROJECT_ROOT / "input" / "design-params" / "case-config.yaml").read_text())
    objects = {}
    for p in (PROJECT_ROOT / "input" / "objects").glob("*.yaml"):
        obj = yaml.safe_load(p.read_text())
        objects[obj["id"]] = obj
    return project_cfg, case_spec, case_config, objects


def calculate_internal_dimensions(objects, case_config):
    obj_clear = case_config["internal"]["object_clearance"]
    cable_bend = case_config["internal"]["cable_bend_allowance"]
    z_margin = case_config["internal"].get("z_margin", 0.0)
    battery = objects["mobile-battery"]["dimensions"]
    m5 = objects["m5stick-s3"]["dimensions"]
    gps = objects["gps-module"]["dimensions"]
    ix = max(battery["height"], m5["height"], gps["height"]) + cable_bend
    iy = battery["width"] + max(m5["width"], gps["width"]) + obj_clear
    iz = max(battery["depth"], m5["depth"] + gps["depth"] + obj_clear) + z_margin
    return (ix, iy, iz)


def calculate_body_outer(ix, iy, iz, case_config):
    wall = case_config["walls"]["thickness"]
    bottom = case_config["walls"]["bottom_thickness"]
    return (ix + bottom, iy + 2 * wall, iz + 2 * wall)


@check("壁厚が min_wall_thickness 以上")
def check_wall_thickness(cfg):
    project, _, case_config, _ = cfg
    min_w = project["design_rules"]["min_wall_thickness"]
    wall = case_config["walls"]["thickness"]
    bottom = case_config["walls"]["bottom_thickness"]
    assert wall >= min_w, f"side wall {wall} < min {min_w}"
    assert bottom >= min_w, f"bottom {bottom} < min {min_w}"


@check("蓋厚が min_wall_thickness 以上")
def check_lid_thickness(cfg):
    project, _, case_config, _ = cfg
    min_w = project["design_rules"]["min_wall_thickness"]
    lid_t = case_config["lid"]["thickness"]
    assert lid_t >= min_w, f"lid thickness {lid_t} < min {min_w}"


@check("嵌合クリアランスが正の値")
def check_fit_clearance(cfg):
    _, _, case_config, _ = cfg
    fit = case_config["lid"]["fit_clearance"]
    assert fit > 0, f"fit_clearance must be > 0, got {fit}"


@check("ケース外寸 + 蓋(嵌合 + ラッチ壁)が printer_bed に収まる")
def check_printer_bed(cfg):
    project, _, case_config, objects = cfg
    bed = project["print_settings"]["printer_bed"]
    ix, iy, iz = calculate_internal_dimensions(objects, case_config)
    ox, oy, oz = calculate_body_outer(ix, iy, iz, case_config)
    lid_t = case_config["lid"]["thickness"]
    # 蓋は単純な板だが、蝶番ナックル(直径)が +X 方向に少し突き出る
    knuckle_d = case_config.get("hinge", {}).get("knuckle_diameter", 6.0)
    lip_h = case_config["lid"].get("lip_height", 0.0)
    c_cfg = case_config.get("catch", {})
    plate_extend_y = c_cfg.get("plate_extend_y", 0.0) if c_cfg.get("enabled", True) else 0.0
    wall_depth_x = c_cfg.get("wall_depth_x", 0.0) if c_cfg.get("enabled", True) else 0.0
    body_print_dims = (ox + knuckle_d, oy, oz)
    # 蓋の総 X 寸法 = lip_h(下) + lid_t(板) + knuckle_d/2(上) ≈ 簡略化のため knuckle_d 加算
    lid_x = lip_h + lid_t + knuckle_d / 2
    lid_y = oy + plate_extend_y + knuckle_d / 2
    lid_print_dims = (lid_x, lid_y, oz)

    for label, dims in [("body", body_print_dims), ("lid", lid_print_dims)]:
        d = sorted(dims, reverse=True)
        b = sorted(bed, reverse=True)
        assert all(d[i] <= b[i] for i in range(3)), \
            f"{label} {dims} does not fit in bed {bed}"


@check("カラビナタブ: 穴周りに最低マージン確保")
def check_carabiner_tab_margin(cfg):
    _, _, case_config, _ = cfg
    tab_cfg = case_config.get("carabiner_tab", {})
    if tab_cfg.get("enabled") is False:
        return
    base_w = tab_cfg.get("base_width_x", 22.0)
    tip_w = tab_cfg.get("tip_width_x", 14.0)
    extend = tab_cfg.get("extend_y", 14.0)
    thick = tab_cfg.get("thickness_z", 5.0)
    diam = tab_cfg.get("hole_diameter", 6.0)
    hole_offset_tip = tab_cfg.get("hole_offset_from_tip", 5.0)
    margin_min = tab_cfg.get("margin_min", 3.0)

    # 先端側マージン (Y 方向): 先端から穴中心までの距離 - 穴半径
    tip_y_margin = hole_offset_tip - diam / 2
    assert tip_y_margin >= margin_min, \
        f"先端マージン {tip_y_margin:.2f} < {margin_min}"

    # 基部側マージン (Y 方向): 基部から穴中心までの距離 - 穴半径
    base_y_margin = (extend - hole_offset_tip) - diam / 2
    assert base_y_margin >= margin_min, \
        f"基部マージン {base_y_margin:.2f} < {margin_min}"

    # X 方向(先端側): 先端幅は穴の周りに最低マージン以上必要
    # 台形なので穴位置(先端寄り)での実際幅を線形補間で求める
    # Y=face_y で base_w、Y=face_y+extend で tip_w
    # 穴は Y=face_y+extend-hole_offset_tip にあるので、その時の幅:
    t = (extend - hole_offset_tip) / extend  # t=0 が基部、t=1 が先端
    width_at_hole = base_w * (1 - t) + tip_w * t
    x_margin = (width_at_hole - diam) / 2
    assert x_margin >= margin_min, \
        f"X 方向マージン {x_margin:.2f} < {margin_min} (穴位置幅 {width_at_hole:.2f})"

    # Z 方向(板厚): 厚みが穴径以上 + マージン確保(Z 貫通の場合は不要だが、強度として要件)
    # Z 厚は穴貫通方向なのでマージン要件なし、ただし最低厚みは確保
    assert thick >= 3.0, f"タブ板厚 {thick} < 3.0(剛性確保)"


@check("カラビナタブ: 形状が台形(基部広・先端狭)")
def check_carabiner_tab_shape(cfg):
    _, case_spec, case_config, _ = cfg
    tab_cfg = case_config.get("carabiner_tab", {})
    if tab_cfg.get("enabled") is False:
        return
    base_w = tab_cfg.get("base_width_x", 22.0)
    tip_w = tab_cfg.get("tip_width_x", 14.0)
    assert base_w >= tip_w, f"台形構造のため base_w({base_w}) >= tip_w({tip_w}) を期待"
    assert tab_cfg.get("shape", "trapezoid") == "trapezoid", \
        f"shape は trapezoid を期待: {tab_cfg.get('shape')}"


@check("オブジェクト最大長軸が内寸 X に収まる")
def check_objects_fit(cfg):
    _, _, case_config, objects = cfg
    ix, _, _ = calculate_internal_dimensions(objects, case_config)
    cable_bend = case_config["internal"]["cable_bend_allowance"]
    available = ix - cable_bend
    for obj_id, obj in objects.items():
        if obj_id.startswith("cable-"):
            continue
        if obj["shape"] == "cylindrical":
            longest = max(obj["dimensions"]["diameter"], obj["dimensions"]["height"])
        else:
            longest = max(obj["dimensions"]["width"], obj["dimensions"]["depth"], obj["dimensions"]["height"])
        assert longest <= available, f"{obj_id} longest {longest} > available X {available}"


@check("USB-C ケーブル長で M5↔バッテリー間距離をカバー可能")
def check_cable_reach(cfg):
    _, _, case_config, objects = cfg
    cable_bend = case_config["internal"]["cable_bend_allowance"]
    cable = objects.get("cable-usb-c")
    if cable is None:
        return
    cable_len = cable["dimensions"]["height"]
    assert cable_len >= cable_bend - 5, f"cable straight len {cable_len} < bend allowance {cable_bend}"


@check("蓋方向(lid_axis)が想定範囲")
def check_lid_axis(cfg):
    _, _, case_config, _ = cfg
    axis = case_config["lid"].get("axis", "+Z")
    valid = {"+X", "-X", "+Y", "-Y", "+Z", "-Z"}
    assert axis in valid, f"lid.axis {axis} not in {valid}"


@check("蝶番: ナックル肉厚が最低 1mm 以上(ピン穴 - knuckle_d)")
def check_hinge_knuckle(cfg):
    _, _, case_config, _ = cfg
    h_cfg = case_config.get("hinge", {})
    if h_cfg.get("enabled") is False:
        return
    knuckle_d = h_cfg.get("knuckle_diameter", 6.0)
    pin_d = h_cfg.get("pin_diameter", 2.0)
    pin_clear = h_cfg.get("pin_clearance", 0.4)
    wall = (knuckle_d - (pin_d + pin_clear)) / 2
    assert wall >= 1.0, f"ナックル肉厚 {wall:.2f}mm < 1.0mm"


@check("蝶番: 全ナックル + クリアランスが oz に収まる")
def check_hinge_z_fit(cfg):
    _, _, case_config, objects = cfg
    h_cfg = case_config.get("hinge", {})
    if h_cfg.get("enabled") is False:
        return
    n_body = h_cfg.get("knuckle_count_body", 2)
    n_lid = h_cfg.get("knuckle_count_lid", 1)
    z_clear = h_cfg.get("knuckle_clearance_z", 0.4)
    total = n_body + n_lid
    n_gaps = total - 1
    edge_clear = z_clear

    ix, iy, iz = calculate_internal_dimensions(objects, case_config)
    _, _, oz = calculate_body_outer(ix, iy, iz, case_config)

    knuckle_h = (oz - 2 * edge_clear - n_gaps * z_clear) / total
    assert knuckle_h >= 3.0, f"ナックル高さ {knuckle_h:.2f}mm < 3.0mm(短すぎ)"


@check("ラッチ: bump_protrusion が PLA 弾性域(0.3-1.0mm)")
def check_catch_bump(cfg):
    _, _, case_config, _ = cfg
    c_cfg = case_config.get("catch", {})
    if c_cfg.get("enabled") is False:
        return
    p = c_cfg.get("bump_protrusion", 0.6)
    d = c_cfg.get("bump_diameter", 3.0)
    assert 0.3 <= p <= 1.0, f"bump_protrusion {p} は 0.3-1.0mm を推奨"
    assert d >= 2 * p, f"bump_diameter {d} は protrusion {p} の 2 倍以上を推奨"


@check("body_text: フォントファイル存在 + emboss_depth が FDM 推奨範囲(0.4-1.5mm)")
def check_body_text(cfg):
    _, _, case_config, _ = cfg
    txt_cfg = case_config.get("body_text", {})
    if txt_cfg.get("enabled") is False:
        return
    font_file = txt_cfg.get("font_file", "ToaHI-Rg.ttf")
    font_path = PROJECT_ROOT / "src" / "fonts" / font_file
    assert font_path.exists(), f"font not found: {font_path}"
    depth = txt_cfg.get("emboss_depth", 0.6)
    assert 0.4 <= depth <= 1.5, f"emboss_depth {depth}mm は 0.4-1.5 を推奨(FDM 0.2 層 × 2-7 層)"


def main():
    cfg = load_configs()
    project, case_spec, case_config, objects = cfg
    ix, iy, iz = calculate_internal_dimensions(objects, case_config)
    ox, oy, oz = calculate_body_outer(ix, iy, iz, case_config)
    lid_t = case_config["lid"]["thickness"]
    lid_axis = case_config["lid"].get("axis", "+Z")
    tab_cfg = case_config.get("carabiner_tab", {})
    h_cfg = case_config.get("hinge", {})
    c_cfg = case_config.get("catch", {})

    report = ["# Validation Report", ""]
    report.append("## 計算結果")
    report.append(f"- 内寸 (X×Y×Z): **{ix:.1f} × {iy:.1f} × {iz:.1f}** mm")
    report.append(f"- 本体外形 (X×Y×Z): {ox:.1f} × {oy:.1f} × {oz:.1f} mm")
    lip_h = case_config["lid"].get("lip_height", 0.0)
    fit_c = case_config["lid"].get("fit_clearance", 0.0)
    plate_extend_y = c_cfg.get("plate_extend_y", 0.0)
    wall_depth_x = c_cfg.get("wall_depth_x", 0.0)
    report.append(f"- 蓋: 上板 {lid_t}mm + 嵌合リップ {lip_h}mm(fit_clearance {fit_c}mm)"
                  f" + ラッチ壁(板 +Y 拡張 {plate_extend_y}mm × -X 深さ {wall_depth_x}mm)")
    report.append(f"- 蓋方向 (lid_axis): **{lid_axis}**")
    report.append(f"- カラビナタブ(台形): "
                  f"基部 {tab_cfg.get('base_width_x')}mm → 先端 {tab_cfg.get('tip_width_x')}mm, "
                  f"突出 {tab_cfg.get('extend_y')}mm, 厚 {tab_cfg.get('thickness_z')}mm, "
                  f"穴径 {tab_cfg.get('hole_diameter')}mm, "
                  f"先端R {tab_cfg.get('tip_fillet_radius')}mm")
    report.append(f"- 蝶番: ナックル外径 {h_cfg.get('knuckle_diameter')}mm × "
                  f"(本体 {h_cfg.get('knuckle_count_body')} + 蓋 {h_cfg.get('knuckle_count_lid')}), "
                  f"ピン径 {h_cfg.get('pin_diameter')}mm, 取付面 {h_cfg.get('side')}")
    report.append(f"- ラッチ: bump 径 {c_cfg.get('bump_diameter')}mm × 突出 {c_cfg.get('bump_protrusion')}mm, "
                  f"取付面 {c_cfg.get('side')}")
    txt_cfg = case_config.get("body_text", {})
    if txt_cfg.get("enabled") is not False:
        import math
        PHI = (1 + math.sqrt(5)) / 2
        text_str = txt_cfg.get("text", "")
        cwf = txt_cfg.get("char_width_factor", 0.55)
        wr = txt_cfg.get("text_width_ratio", 1 / PHI)
        if txt_cfg.get("font_size_mm"):
            fs = float(txt_cfg["font_size_mm"])
        else:
            fs = (ox * wr) / max(1, len(text_str)) / cwf
        report.append(f"- body_text: '{text_str}' on {txt_cfg.get('side', '+Z')}, "
                      f"font={txt_cfg.get('font_file', 'ToaHI-Rg.ttf')}, "
                      f"size≈{fs:.2f}mm(width_ratio=1/φ={wr:.3f}), "
                      f"emboss {txt_cfg.get('emboss_depth', 0.6)}mm")
    report.append(f"- printer_bed: {project['print_settings']['printer_bed']} mm")
    report.append("")

    report.append("## チェック結果")
    pass_count, fail_count = 0, 0
    for name, fn in CHECKS:
        try:
            fn(cfg)
            report.append(f"- ✅ {name}")
            pass_count += 1
        except AssertionError as e:
            report.append(f"- ❌ {name}: {e}")
            fail_count += 1
        except Exception as e:
            report.append(f"- ⚠ {name}: {type(e).__name__}: {e}")
            fail_count += 1

    report.append("")
    report.append(f"**合計: {pass_count} passed, {fail_count} failed**")

    out_path = PROJECT_ROOT / "output" / "reports" / "validation.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(report) + "\n")
    print(f"✓ {out_path} を出力しました")
    print(f"  {pass_count} passed, {fail_count} failed")


if __name__ == "__main__":
    main()
