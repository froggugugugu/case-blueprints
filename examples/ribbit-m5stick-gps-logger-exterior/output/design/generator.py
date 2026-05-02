"""generator.py — CadQuery でケースを生成する。
単体実行: python output/design/generator.py

レイアウト:
  - 縦持ち想定。長軸 X が垂直方向となる。
  - +X 端に蓋(嵌合リップ + 蝶番 + ラッチ)。-X 端は閉じた底。
  - 蝶番: -Y 辺の +X 端(本体 2 ナックル + 蓋 1 ナックル + M2 ピン挿入式)
  - ラッチ(catch): +Y 面 snap bump + 蓋の +Y 側ラッチ壁(上板と一体)
  - カラビナタブ: +Y 面、台形 + 先端 R 面取り、Z 方向貫通穴
  - 本体テキスト: 任意の面に盛り上げ加工(emboss)で配置
"""
import math
import yaml
import cadquery as cq
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PHI = (1 + math.sqrt(5)) / 2  # 黄金比 ≈ 1.618


# ----- 設定読み込み -----
def load_configs():
    project_cfg = yaml.safe_load((PROJECT_ROOT / "project-config.yaml").read_text())
    case_spec = yaml.safe_load((PROJECT_ROOT / "input" / "requirements" / "case-spec.yaml").read_text())
    case_config = yaml.safe_load((PROJECT_ROOT / "input" / "design-params" / "case-config.yaml").read_text())

    objects = {}
    for p in (PROJECT_ROOT / "input" / "objects").glob("*.yaml"):
        obj = yaml.safe_load(p.read_text())
        objects[obj["id"]] = obj

    return project_cfg, case_spec, case_config, objects


# ----- 寸法計算 -----
def calculate_internal_dimensions(objects, case_config, case_spec):
    """内寸 (X, Y, Z) を計算する。"""
    obj_clear = case_config["internal"]["object_clearance"]
    cable_bend = case_config["internal"]["cable_bend_allowance"]

    battery = objects["mobile-battery"]["dimensions"]
    m5 = objects["m5stick-s3"]["dimensions"]
    gps = objects["gps-module"]["dimensions"]

    z_margin = case_config["internal"].get("z_margin", 0.0)

    internal_x = max(battery["height"], m5["height"], gps["height"]) + cable_bend
    internal_y = battery["width"] + max(m5["width"], gps["width"]) + obj_clear
    internal_z = max(battery["depth"], m5["depth"] + gps["depth"] + obj_clear) + z_margin

    return (internal_x, internal_y, internal_z)


def calculate_body_outer(internal_dims, case_config):
    """本体外形寸法 (ox, oy, oz) を返す。+X は開放(キャップ型)。"""
    ix, iy, iz = internal_dims
    wall = case_config["walls"]["thickness"]
    bottom = case_config["walls"]["bottom_thickness"]
    return (ix + bottom, iy + 2 * wall, iz + 2 * wall)


# ----- 本体・蓋 -----
def build_case_body(internal_dims, case_config):
    """箱本体(-X 端閉鎖、+X 端開放)。"""
    ix, iy, iz = internal_dims
    fillet_outer = case_config["fillet"]["outer_radius"]
    ox, oy, oz = calculate_body_outer(internal_dims, case_config)

    # 外形: YZ 平面に長方形を描き、+X 方向へ ox 押し出す
    body = (cq.Workplane("YZ")
            .rect(oy, oz)
            .extrude(ox))
    if fillet_outer > 0:
        try:
            body = body.edges("|X").fillet(fillet_outer)
        except Exception as e:
            print(f"⚠ body outer fillet skip: {e}")

    # 底面 (-X) のエッジ面取り(手触り改善 + 印刷時の角ばり緩和)
    bottom_r = case_config["fillet"].get("bottom_radius", 1.0)
    if bottom_r > 0:
        try:
            body = body.faces("<X").edges().fillet(bottom_r)
        except Exception as e:
            print(f"⚠ body bottom fillet skip: {e}")

    # 内側を彫り込む
    body = (body.faces(">X").workplane()
            .rect(iy, iz)
            .cutBlind(-ix))
    return body


def build_lid(internal_dims, case_config):
    """嵌合リップ付き蓋(+X 面被せ型)+ ラッチ壁を統合。蝶番で保持される。

    構成(全て 3D 体積で連結):
      1. 上板: 本体外形 + ラッチ用に +Y 方向へ拡張
      2. 嵌合リップ: 本体内側に押し込む solid block(上板を貫通させ体積接続)
      3. ラッチ壁: 上板の +Y 拡張部から -X 方向に降ろす壁(板と体積で接続)
    """
    ix, iy, iz = internal_dims
    lid_t = case_config["lid"]["thickness"]
    lip_h = case_config["lid"]["lip_height"]
    fit = case_config["lid"]["fit_clearance"]
    # 蝶番側(-Y)のリップだけ追加で縮める量。+Y 側はそのまま。
    hinge_extra = case_config["lid"].get("lip_hinge_side_extra_clearance", 0.0)
    fillet_outer = case_config["fillet"]["outer_radius"]

    c_cfg = case_config.get("catch", {})
    catch_enabled = c_cfg.get("enabled", True)
    catch_extend_y = c_cfg.get("plate_extend_y", 2.5)
    catch_wall_depth = c_cfg.get("wall_depth_x", 5.0)

    ox, oy, oz = calculate_body_outer(internal_dims, case_config)

    # ----- 1. 上板(+Y にラッチ用拡張) -----
    plate_y_max = oy / 2 + (catch_extend_y if catch_enabled else 0)
    plate_y_min = -oy / 2
    plate_oy = plate_y_max - plate_y_min
    plate_y_center = (plate_y_min + plate_y_max) / 2

    lid = (cq.Workplane("YZ")
           .rect(plate_oy, oz)
           .extrude(lid_t)
           .translate((ox, plate_y_center, 0)))
    if fillet_outer > 0:
        try:
            lid = lid.edges("|X").fillet(fillet_outer)
        except Exception as e:
            print(f"⚠ lid outer fillet skip: {e}")

    # ----- 2. 嵌合リップブロック(上板を貫通させ 3D 体積接続) -----
    # 蝶番側(-Y)だけ hinge_extra 縮める。+Y 端は iy/2 - fit のまま。
    # 結果: -Y 端 = -iy/2 + fit + hinge_extra、+Y 端 = iy/2 - fit
    # リップ Y 寸法は iy - 2*fit - hinge_extra、Y 中心は +hinge_extra/2 にシフト。
    lip_y = iy - 2 * fit - hinge_extra
    lip_z = iz - 2 * fit
    lip_center_y = hinge_extra / 2
    # リップは X ∈ [ox - lip_h, ox + lid_t] に伸ばし、上板 X ∈ [ox, ox + lid_t] と完全に重ねる
    lip = (cq.Workplane("YZ")
           .rect(lip_y, lip_z)
           .extrude(lip_h + lid_t)
           .translate((ox - lip_h, lip_center_y, 0)))

    # 嵌合リップの面取り(縦コーナー → 先端の順で fillet)
    lip_tip_r = case_config["lid"].get("lip_tip_fillet_radius",
                                       min(0.5, lip_h / 3, fit * 1.5))
    lip_corner_r = case_config["lid"].get("lip_corner_fillet_radius", 0.5)
    if lip_corner_r > 0:
        try:
            # リップの縦 4 エッジ (|X) を先に丸める(本体内寸コーナーとの当たり緩和)
            lip = lip.edges("|X").fillet(lip_corner_r)
        except Exception as e:
            print(f"⚠ lip corner fillet skip: {e}")
    if lip_tip_r > 0:
        try:
            # リップ先端 (-X 端) の周囲 4 エッジ — 嵌合のリードイン + 印刷オーバーハング対策
            lip = lip.edges("<X").fillet(lip_tip_r)
        except Exception as e:
            print(f"⚠ lip tip fillet skip: {e}")

    lid = lid.union(lip)

    # ----- 3. ラッチ壁(上板の +Y 拡張部から -X 方向に降ろす) -----
    if catch_enabled:
        wall_x_lo = ox - catch_wall_depth
        wall_x_hi = ox + lid_t          # 上板を完全貫通して体積接続
        wall_y_lo = oy / 2              # 本体 +Y 外面に密着(内面)
        wall_y_hi = oy / 2 + catch_extend_y
        wall_z = max(oz - 2 * (fillet_outer + 1.0), oz * 0.7)

        wall = (cq.Workplane("XY")
                .moveTo((wall_x_lo + wall_x_hi) / 2,
                        (wall_y_lo + wall_y_hi) / 2)
                .rect(wall_x_hi - wall_x_lo, wall_y_hi - wall_y_lo)
                .extrude(wall_z)
                .translate((0, 0, -wall_z / 2)))

        # 仕上げ面取り(union 前にラッチ壁単体で実施)
        tip_r = c_cfg.get("tip_fillet_radius",
                          min(1.0, catch_extend_y / 3, catch_wall_depth / 3))
        side_r = c_cfg.get("side_fillet_radius", 0.5)
        try:
            # 先端(-X 端、リップの底面)4 エッジを R=tip_r で丸める
            wall = wall.edges("<X").fillet(tip_r)
        except Exception as e:
            print(f"⚠ catch wall tip fillet skip: {e}")
        try:
            # 外面(+Y)の上下(±Z)エッジを R=side_r で丸める
            wall = wall.edges(">Y and |X").fillet(side_r)
        except Exception as e:
            print(f"⚠ catch wall outer fillet skip: {e}")

        lid = lid.union(wall)

    return lid


# ----- feature: カラビナタブ(台形 + 面取り) -----
def apply_carabiner_tab(part, feature, case_config, body_dims):
    ox, oy, oz = body_dims

    tab_cfg = case_config.get("carabiner_tab", {})
    if tab_cfg.get("enabled") is False:
        return part

    base_w = feature.get("base_width_x", tab_cfg.get("base_width_x", 22.0))
    tip_w = feature.get("tip_width_x", tab_cfg.get("tip_width_x", 14.0))
    extend = feature.get("extend_y", tab_cfg.get("extend_y", 14.0))
    thick = feature.get("thickness_z", tab_cfg.get("thickness_z", 5.0))
    hole_d = feature.get("hole_diameter", tab_cfg.get("hole_diameter", 6.0))
    hole_offset_tip = feature.get("hole_offset_from_tip", tab_cfg.get("hole_offset_from_tip", 5.0))
    tip_fillet = feature.get("tip_fillet_radius", tab_cfg.get("tip_fillet_radius", 4.0))
    base_fillet = feature.get("base_fillet_radius", tab_cfg.get("base_fillet_radius", 1.5))
    margin_top = tab_cfg.get("margin_from_top", 6.0)
    side = feature.get("side", tab_cfg.get("side", "+Y"))

    if side != "+Y":
        print(f"⚠ carabiner_tab: side {side} 未対応(+Y のみ)")
        return part

    tab_center_x = ox - margin_top - base_w / 2
    face_y = oy / 2

    # 台形プレート: 基部広(base_w)・先端狭(tip_w)
    pts = [
        (tab_center_x - base_w / 2, face_y),
        (tab_center_x + base_w / 2, face_y),
        (tab_center_x + tip_w / 2, face_y + extend),
        (tab_center_x - tip_w / 2, face_y + extend),
    ]
    tab = (cq.Workplane("XY")
           .polyline(pts).close()
           .extrude(thick)
           .translate((0, 0, -thick / 2)))

    # 先端側の縦エッジを大 R で面取り
    try:
        tab = tab.edges("|Z and >Y").fillet(tip_fillet)
    except Exception as e:
        print(f"⚠ tab tip fillet skip: {e}")
        try:
            tab = tab.edges("|Z").fillet(min(tip_fillet, base_fillet))
        except Exception as e2:
            print(f"⚠ tab fallback fillet skip: {e2}")

    # 基部側の縦エッジを小 R で面取り
    try:
        tab = tab.edges("|Z and <Y").fillet(base_fillet)
    except Exception as e:
        print(f"⚠ tab base fillet skip: {e}")

    # 上下面(±Z 面)の周辺エッジも軽く面取り(手触り改善)
    try:
        tab = tab.faces(">Z or <Z").edges().fillet(0.5)
    except Exception as e:
        print(f"⚠ tab face fillet skip: {e}")

    # 本体に union
    part = part.union(tab)

    # 貫通穴: 先端側に hole_offset_tip 内側
    hole_x = tab_center_x
    hole_y = face_y + extend - hole_offset_tip
    hole_cyl = (cq.Workplane("XY")
                .moveTo(hole_x, hole_y)
                .circle(hole_d / 2)
                .extrude(thick + 2)
                .translate((0, 0, -thick / 2 - 1)))
    part = part.cut(hole_cyl)

    return part


# ----- feature: 蝶番(ナックル蝶番) -----
def apply_hinge(body, lid, feature, case_config, body_dims):
    """-Y 辺の +X 端にナックル蝶番。本体 2 個 + 蓋 1 個を Z 方向に交互配置。"""
    ox, oy, oz = body_dims

    h_cfg = case_config.get("hinge", {})
    if h_cfg.get("enabled") is False:
        return body, lid

    side = feature.get("side", h_cfg.get("side", "-Y"))
    knuckle_d = h_cfg.get("knuckle_diameter", 6.0)
    pin_d = h_cfg.get("pin_diameter", 2.0)
    pin_clear = h_cfg.get("pin_clearance", 0.4)
    n_body = h_cfg.get("knuckle_count_body", 2)
    n_lid = h_cfg.get("knuckle_count_lid", 1)
    z_clear = h_cfg.get("knuckle_clearance_z", 0.4)
    # 蓋ナックルのみ片側ごとに Z を縮める量。本体ナックル位置は不変のまま実効 Z 隙間を広げる。
    lid_extra_z = h_cfg.get("lid_knuckle_extra_clearance_z", 0.0)
    # 蓋シリンダーが本体壁の埋込部と干渉しないよう、蓋ナックル Z 位置の本体壁を円筒状に抜く半径クリアランス
    body_relief = h_cfg.get("body_relief_clearance", 0.0)
    # 本体ナックルの +X 半円(壁埋込分が +X 側にはみ出す)が蓋プレート -Y 端と干渉するのを回避するため、
    # 本体ナックル Z 位置の蓋プレートに円筒状のリリーフカットを掘る半径クリアランス
    lid_relief = h_cfg.get("lid_relief_clearance", 0.0)

    if side != "-Y":
        print(f"⚠ hinge: side {side} 未対応(-Y のみ)")
        return body, lid

    knuckle_r = knuckle_d / 2
    pin_hole_r = (pin_d + pin_clear) / 2

    # 蝶番軸位置: X=ox(本体と蓋の境界)、Y は -oy/2 の少し外側(本体面に少し食い込む)
    overlap_y = 1.0
    axis_x = ox
    axis_y = -oy / 2 - knuckle_r + overlap_y

    body_face_y = -oy / 2

    # ナックル分配
    total = n_body + n_lid
    n_gaps = total - 1
    edge_clear = z_clear
    knuckle_h = (oz - 2 * edge_clear - n_gaps * z_clear) / total
    if knuckle_h <= 0:
        print(f"⚠ hinge: knuckle_h <= 0 (oz={oz}, total={total})")
        return body, lid

    # 配置パターン
    if n_body == 2 and n_lid == 1:
        pattern = ["body", "lid", "body"]
    elif n_body == 1 and n_lid == 2:
        pattern = ["lid", "body", "lid"]
    elif n_body == 3 and n_lid == 2:
        pattern = ["body", "lid", "body", "lid", "body"]
    elif n_body == 2 and n_lid == 3:
        pattern = ["lid", "body", "lid", "body", "lid"]
    else:
        # フォールバック (非交互)
        pattern = (["body"] * n_body) + (["lid"] * n_lid)

    # Z 配置
    z_cursor = -oz / 2 + edge_clear
    knuckles = []
    for i, owner in enumerate(pattern):
        z_start = z_cursor
        z_end = z_start + knuckle_h
        z_center = (z_start + z_end) / 2
        knuckles.append((owner, z_center, knuckle_h))
        z_cursor = z_end + (z_clear if i < total - 1 else 0)

    # 各ナックルを構築
    block_y_extent = body_face_y - axis_y  # = knuckle_r - overlap_y

    for owner, z_c, h in knuckles:
        # 蓋ナックルだけ Z 高さを 2 * lid_extra_z 短くする(中心 z_c は本体間の中央のまま)
        if owner == "lid" and lid_extra_z > 0:
            h_eff = max(h - 2 * lid_extra_z, 1.0)
        else:
            h_eff = h

        # シリンダー
        cyl = (cq.Workplane("XY")
               .moveTo(axis_x, axis_y)
               .circle(knuckle_r)
               .extrude(h_eff)
               .translate((0, 0, z_c - h_eff / 2)))

        # 接続ブロック (cylinder と本体/蓋の壁面を結合)
        block = None
        if block_y_extent > 0.01:
            if owner == "body":
                bx_lo = axis_x - knuckle_r
                bx_hi = axis_x
            else:
                bx_lo = axis_x
                bx_hi = axis_x + knuckle_r
            block = (cq.Workplane("XY")
                     .moveTo((bx_lo + bx_hi) / 2, (axis_y + body_face_y) / 2)
                     .rect(bx_hi - bx_lo, block_y_extent)
                     .extrude(h_eff)
                     .translate((0, 0, z_c - h_eff / 2)))

        # ピン穴(蓋の場合は ピンクリアランスを広めに取りたいので h_eff + 余裕で貫通)
        pin_hole = (cq.Workplane("XY")
                    .moveTo(axis_x, axis_y)
                    .circle(pin_hole_r)
                    .extrude(h_eff + 2)
                    .translate((0, 0, z_c - h_eff / 2 - 1)))

        knuckle_solid = cyl
        if block is not None:
            knuckle_solid = knuckle_solid.union(block)
        knuckle_solid = knuckle_solid.cut(pin_hole)

        if owner == "body":
            body = body.union(knuckle_solid)
            # 本体ナックル Z 位置の蓋プレートにリリーフカット(本体ナックル +X 半円が
            # 壁埋込分 overlap_y だけ +Y 方向にせり出して蓋プレート -Y 端と干渉するのを回避)
            # 半径は knuckle_r + lid_relief、Z 範囲は本体ナックル h(蓋ナックル位置とは別 Z)。
            if lid_relief > 0 and overlap_y > 0:
                lid_relief_cut = (cq.Workplane("XY")
                                  .moveTo(axis_x, axis_y)
                                  .circle(knuckle_r + lid_relief)
                                  .extrude(h)
                                  .translate((0, 0, z_c - h / 2)))
                lid = lid.cut(lid_relief_cut)
        else:
            lid = lid.union(knuckle_solid)
            # 蓋ナックル Z 位置の本体壁にリリーフカット(蓋シリンダーが本体壁の埋込部と干渉するのを回避)
            # 抜き穴の Z 範囲は元の slot 高 h(本体ナックル端から z_clear 離れている)、
            # 半径は knuckle_r + body_relief。本体ナックル(別 Z)とは重ならないので安全に cut できる。
            if body_relief > 0:
                relief_cut = (cq.Workplane("XY")
                              .moveTo(axis_x, axis_y)
                              .circle(knuckle_r + body_relief)
                              .extrude(h)
                              .translate((0, 0, z_c - h / 2)))
                body = body.cut(relief_cut)

    return body, lid


# ----- feature: ラッチ(snap bump + 蓋側球凹み) -----
def apply_catch(body, lid, feature, case_config, body_dims):
    """+Y 面に snap bump を生やし、蓋のラッチ壁に半球凹みを彫る。

    ラッチ壁本体は build_lid で上板と一体に作られているので、ここでは
    bump と凹みの追加のみ行う(分離部品にならないようにするため)。
    """
    ox, oy, oz = body_dims

    c_cfg = case_config.get("catch", {})
    if c_cfg.get("enabled") is False:
        return body, lid

    side = feature.get("side", c_cfg.get("side", "+Y"))
    bump_d = c_cfg.get("bump_diameter", 3.0)
    bump_p = c_cfg.get("bump_protrusion", 0.6)
    pos_x_from_top = c_cfg.get("position_from_top_x", 4.0)

    if side != "+Y":
        print(f"⚠ catch: side {side} 未対応(+Y のみ)")
        return body, lid

    # 球半径(弦 = bump_d、矢高 = bump_p)
    R = (bump_d / 2) ** 2 / (2 * bump_p) + bump_p / 2

    bump_x = ox - pos_x_from_top
    sphere_center_y = oy / 2 - (R - bump_p)
    bump_z = 0

    # 本体側 snap bump
    bump = (cq.Workplane()
            .add(cq.Solid.makeSphere(R))
            .translate((bump_x, sphere_center_y, bump_z)))
    body = body.union(bump)

    # 蓋ラッチ壁内面に球凹み(bump + clearance を cut)
    recess_clear = 0.15
    recess = (cq.Workplane()
              .add(cq.Solid.makeSphere(R + recess_clear))
              .translate((bump_x, sphere_center_y, bump_z)))
    lid = lid.cut(recess)

    return body, lid


# ----- feature: 本体テキスト(盛り上げ加工) -----
def apply_body_text(part, feature, case_config, body_dims):
    """本体外面にテキストを盛り上げ加工(union)で配置。

    フォントサイズは黄金比から自動算出: text_width = ox * (1/φ)。
    config の font_size_mm を指定した場合はそれを優先。
    """
    ox, oy, oz = body_dims

    txt_cfg = case_config.get("body_text", {})
    if txt_cfg.get("enabled") is False:
        return part

    text_str = feature.get("text", txt_cfg.get("text", "RIBBIT"))
    side = feature.get("side", txt_cfg.get("side", "+Z"))
    font_file = feature.get("font_file", txt_cfg.get("font_file", "ToaHI-Rg.ttf"))
    emboss_depth = txt_cfg.get("emboss_depth", 0.6)
    width_ratio = txt_cfg.get("text_width_ratio", 1.0 / PHI)
    char_width_factor = txt_cfg.get("char_width_factor", 0.55)
    font_size_override = txt_cfg.get("font_size_mm")

    if font_size_override:
        font_size = float(font_size_override)
    else:
        target_w = ox * width_ratio
        font_size = target_w / (max(1, len(text_str)) * char_width_factor)

    font_path = PROJECT_ROOT / "src" / "fonts" / font_file
    if not font_path.exists():
        print(f"⚠ body_text: font not found: {font_path}")
        return part

    # 面ごとのワークプレーン定義(明示的な Plane で xDir/normal を制御)
    # CadQuery の named "top" は normal +Y で直感に反するため自前で構築する。
    # text は workplane の xDir 方向に読み、normal 方向に extrude される。
    side_to_plane = {
        "+Z": cq.Plane(origin=cq.Vector(ox / 2, 0, oz / 2),
                       xDir=cq.Vector(1, 0, 0),
                       normal=cq.Vector(0, 0, 1)),
        "-Z": cq.Plane(origin=cq.Vector(ox / 2, 0, -oz / 2),
                       xDir=cq.Vector(1, 0, 0),
                       normal=cq.Vector(0, 0, -1)),
        "+Y": cq.Plane(origin=cq.Vector(ox / 2, oy / 2, 0),
                       xDir=cq.Vector(1, 0, 0),
                       normal=cq.Vector(0, 1, 0)),
        "-Y": cq.Plane(origin=cq.Vector(ox / 2, -oy / 2, 0),
                       xDir=cq.Vector(1, 0, 0),
                       normal=cq.Vector(0, -1, 0)),
    }
    plane = side_to_plane.get(side)
    if plane is None:
        print(f"⚠ body_text: side {side} 未対応({list(side_to_plane)})")
        return part

    try:
        text_wp = (cq.Workplane(plane)
                   .text(text_str, font_size, emboss_depth,
                         combine=False,
                         fontPath=str(font_path),
                         halign="center", valign="center"))
        part = part.union(text_wp)
        print(f"✓ body_text: '{text_str}' on {side}, size={font_size:.2f}mm, depth={emboss_depth}mm")
    except Exception as e:
        print(f"⚠ body_text failed: {type(e).__name__}: {e}")

    return part


FEATURE_HANDLERS = {
    "carabiner_tab": ("body", apply_carabiner_tab),
    "hinge":         ("both", apply_hinge),
    "catch":         ("both", apply_catch),
    "body_text":     ("body", apply_body_text),
}


def apply_features(body, lid, case_spec, case_config, body_dims):
    for feature in (case_spec.get("case", {}).get("features") or []):
        ftype = feature.get("type")
        entry = FEATURE_HANDLERS.get(ftype)
        if entry is None:
            print(f"⚠ feature type '{ftype}' のハンドラ未実装")
            continue
        target, handler = entry
        if target == "body":
            body = handler(body, feature, case_config, body_dims)
        elif target == "both":
            body, lid = handler(body, lid, feature, case_config, body_dims)
        else:
            print(f"⚠ feature {ftype}: unknown target {target}")
    return body, lid


# ----- 印刷用変換 -----
def transform_for_print(part, orientation):
    """部品を印刷向きに回転し、最低点が Z=0 に来るよう平行移動。"""
    if orientation == "bottom_down":
        # 本体: -X 端を bed 接地面にする。Y 軸まわりに -90° 回転で world X → print Z。
        rotated = part.rotate((0, 0, 0), (0, 1, 0), -90)
    elif orientation == "top_down":
        # 蓋: +X 端(上板の外面)を bed 接地面にする。Y 軸まわりに +90° 回転で world X → print -Z。
        rotated = part.rotate((0, 0, 0), (0, 1, 0), 90)
    elif orientation == "face_down":
        rotated = part
    else:
        rotated = part

    bb = rotated.val().BoundingBox()
    return rotated.translate((0, 0, -bb.zmin))


def export_for_print(body, lid, case_spec):
    """印刷向きに変換し、output/print/ に STL + 3MF を出力。"""
    out_dir = PROJECT_ROOT / "output" / "print"
    out_dir.mkdir(parents=True, exist_ok=True)

    body_orient = case_spec["case"]["print_orientation"]["body"]
    lid_orient = case_spec["case"]["print_orientation"]["lid"]

    body_print = transform_for_print(body, body_orient)
    lid_print = transform_for_print(lid, lid_orient)

    cq.exporters.export(body_print, str(out_dir / "case-body.stl"))
    cq.exporters.export(lid_print, str(out_dir / "case-lid.stl"))
    try:
        cq.exporters.export(body_print, str(out_dir / "case-body.3mf"),
                            exportType=cq.exporters.ExportTypes.THREEMF)
        cq.exporters.export(lid_print, str(out_dir / "case-lid.3mf"),
                            exportType=cq.exporters.ExportTypes.THREEMF)
        print(f"✓ {out_dir} に印刷向き STL + 3MF を出力({body_orient} / {lid_orient})")
    except Exception as e:
        print(f"⚠ 3MF 出力失敗 (STL のみ出力): {e}")

    # 印刷時の bbox を表示
    bb = body_print.val().BoundingBox()
    print(f"  body 印刷 bbox X×Y×Z = {bb.xmax - bb.xmin:.1f} × {bb.ymax - bb.ymin:.1f} × {bb.zmax - bb.zmin:.1f} mm")
    bb = lid_print.val().BoundingBox()
    print(f"  lid  印刷 bbox X×Y×Z = {bb.xmax - bb.xmin:.1f} × {bb.ymax - bb.ymin:.1f} × {bb.zmax - bb.zmin:.1f} mm")


# ----- main -----
def main():
    project, case_spec, case_config, objects = load_configs()
    internal = calculate_internal_dimensions(objects, case_config, case_spec)
    body_outer = calculate_body_outer(internal, case_config)
    print(f"内寸 (X×Y×Z): {internal[0]:.1f} × {internal[1]:.1f} × {internal[2]:.1f} mm")
    print(f"本体外形 (X×Y×Z): {body_outer[0]:.1f} × {body_outer[1]:.1f} × {body_outer[2]:.1f} mm")

    body = build_case_body(internal, case_config)
    lid = build_lid(internal, case_config)
    body, lid = apply_features(body, lid, case_spec, case_config, body_outer)

    # プレビュー出力(設計レビュー用)
    out_dir = PROJECT_ROOT / "output" / "preview"
    out_dir.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(body, str(out_dir / "case-body.step"))
    cq.exporters.export(body, str(out_dir / "case-body.stl"))
    cq.exporters.export(lid, str(out_dir / "case-lid.step"))
    cq.exporters.export(lid, str(out_dir / "case-lid.stl"))
    print(f"✓ {out_dir} に STEP/STL を出力しました")

    # 印刷用出力(印刷向きに変換)
    export_for_print(body, lid, case_spec)


if __name__ == "__main__":
    main()
