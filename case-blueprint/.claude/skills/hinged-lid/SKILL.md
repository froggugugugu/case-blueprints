---
name: hinged-lid
description: ヒンジ蓋ケース特化スキル(機構特化・横断)— 軸ピン+レバー式ラッチの3部品構成(本体/蓋/レバー)。M2 ピン+ねじの長尺セットをデフォルトに、`hardware:` プリセット差替えで幅狭ラッチ・別径構成にも転用可。`/design` 確定後の closure 詳細を埋める。
---

# /hinged-lid — ヒンジ蓋ケース特化スキル

## 目的

ヒンジで開閉する蓋付きケースの **ヒンジ機構と蓋ラッチ機構** を専用設計する。
3 部品構成(本体 + 蓋 + ラッチレバー独立部品)で、汎用 M2 ハードウェア
セットを標準プリセットとして持つ。

ハードウェアスペック(ピン径・長、ねじ径・長、本数)を差し替えれば、
幅狭ラッチや別径構成にも転用できる。「ハードウェアの差替え =
プリセット変更」、「幾何の調整 = `hinge:` / `latch:` パラメータ編集」と
責務を分離している。

`/design` が closure を抽象的に決めたあと、本スキルが具体寸法を埋める **横断
スキル**(段階に属さず、必要に応じて呼ぶ)。

## 関連スキルとの違い

| スキル | 役割 |
|---|---|
| `/design` | ケース全体構造(壁・蓋・features・closure 抽象) |
| `/hinged-lid`(本スキル) | **closure.method = `hinge_lever` の詳細実装** |
| `/fit-check` | 嵌合・干渉の網羅チェック(本スキルは固有項目を fit-check に追加) |
| `/review-fix` | 利用者フィードバックの反映 |

## 前提条件

- `/design` 実行済み(`generator.py` `case-spec.yaml` `case-config.yaml` 存在)
- `cadquery`, `pyyaml` インストール済み

## 入出力

| 区分 | パス | 説明 |
|---|---|---|
| 入力 | `input/requirements/case-spec.yaml` | `closure.method` 確認 |
| 入力 | `input/design-params/case-config.yaml` | 既存値は尊重 |
| 出力 | `input/requirements/case-spec.yaml` | `case.type = hinged_box`, `closure.method = hinge_lever` |
| 出力 | `input/design-params/case-config.yaml` | `hardware:` `hinge:` `latch:` を追記/更新 |
| 出力 | `output/design/generator.py` | `build_hinge_assembly` `build_latch_*` `build_latch_lever` 追加 |
| 出力 | `output/preview/case-body.step` `.stl` | 本体 |
| 出力 | `output/preview/case-lid.step` `.stl` | 蓋 |
| 出力 | `output/preview/latch-lever.step` `.stl` | レバー独立部品 |

## モード

利用者は以下のサブコマンドで操作する。引数なしの `/hinged-lid` は対話で
モードを問う。

### `/hinged-lid init [--preset m2_long|m2_short|custom]`
ヒンジ蓋型に切替。`case-spec.yaml` の closure 更新、`case-config.yaml` に
`hardware:` `hinge:` `latch:` を生成、`generator.py` に関数を追加する。

### `/hinged-lid scale <factor>`
ナックル外径・各ナックル長・レバー寸法を `factor` 倍。ピン/ねじ長は
ハードウェア依存で固定なので、`factor` がピン長制約を超える場合は
警告して中断する(対処: ハードウェア差替え or ナックル数増)。

### `/hinged-lid latch <type>`
ラッチ機構を切替。`type` は:
- `lever_hook`(デフォルト) — 蓋に回転軸ピン、本体に catch ピン、独立レバー
- `magnet` — レバー廃止、磁石ポケット + 鉄板
- `snap` — レバー廃止、スナップフック一体
- `screw_post` — 蓋からねじで本体ボスに締結

### `/hinged-lid hardware <preset|inline>`
ハードウェアセットを切替(例: `m2_long` → `m2_short`)。`hinge:` / `latch:` の
派生値も同時に再計算するか問う(既存編集を尊重するか確認)。

## ハードウェアプリセット

`hardware:` は **固定スペック**(物理的に変えられない値)。`hinge:` / `latch:`
の幾何はここから派生する。プリセット名は **ピン径と長さで物理的に同定** できる
規約(`m2_long` = M2 ピン 28mm + ねじ 30mm)。

### `m2_long`(デフォルト・M2 × 28-30mm)

```yaml
hardware:
  preset: m2_long
  hinge:
    fastener:
      type: screw_pan_head
      nominal: M2
      length: 30.0
      diameter: 2.0
      head_diameter: 4.0
      head_height: 1.6
      engagement: self_tap          # 末端ナックルでセルフタップ
    count: 2                         # 左右 2 アセンブリ
  latch:
    pivot_pin:                       # 蓋側(レバー回転軸)
      type: parallel_pin
      nominal: M2
      length: 28.0
      diameter: 2.0
    catch_pin:                       # 本体側(レバーフック対象)
      type: parallel_pin
      nominal: M2
      length: 28.0
      diameter: 2.0
    count: 1                         # 中央 1 個
```

### `m2_short`(幅狭ラッチ用・M2 × 14-16mm)

```yaml
hardware:
  preset: m2_short
  hinge:
    fastener: { type: screw_pan_head, nominal: M2, length: 16.0, diameter: 2.0,
                head_diameter: 4.0, head_height: 1.6, engagement: self_tap }
    count: 2
  latch:
    pivot_pin: { type: parallel_pin, nominal: M2, length: 14.0, diameter: 2.0 }
    catch_pin: { type: parallel_pin, nominal: M2, length: 14.0, diameter: 2.0 }
    count: 1
```

### `custom`
任意の値。プリセット名を `custom` にしておくと scale/hardware 切替時に
上書きされない。

## case-config.yaml への追記スキーマ

```yaml
hinge:
  axis:
    side: back                       # back / front / left / right
    inset_from_top: 3.0              # 合わせ面(天面)からの Z オフセット
    inset_from_corner: 8.0           # 角からの軸方向オフセット(左右対称)
  knuckle:
    outer_diameter: 6.0              # 肉厚 = (OD - pin_d) / 2 ≥ 1.5mm 推奨
    pattern: [body, lid, body]       # 3 ナックル交互。末端 body がセルフタップ
    z_clearance: 0.4                 # ナックル間軸方向隙間
    body_relief: 0.3                 # 壁埋込時のリリーフ(P13 参照)
    pin_through_clearance: 0.2       # 通し穴径 = pin_d + 0.2(中間ナックル)
    pin_tap_pilot: 1.7               # セルフタップ下穴径(末端 body ナックル)
  fit_clearance_extra: 0.5           # ヒンジ側だけリップ嵌合に追加するクリア(P14 参照)

latch:
  type: lever_hook
  count: 1
  position:
    side: front
    x_offset: center                 # center / [mm 値] / left / right
  knuckle:
    outer_diameter: 6.0
    pin_through_clearance: 0.2
    z_clearance: 0.4
  pivot:                             # 蓋側(レバー回転軸)
    knuckle_count: 2                 # レバーを左右から挟む 2 ナックル
    knuckle_z_thickness: 4.0
    span_for_lever: 8.0              # ナックル間にレバーが入る幅
  catch:                             # 本体側(フック対象ピン)
    knuckle_count: 2                 # 両端ナックル(片側キャップ)
    knuckle_z_thickness: 4.0
    span_for_hook: 12.0              # フックが入る中央露出区間
    cap_side: right                  # A方式: 片側だけ閉じて意匠を整える
    z_offset_from_lid_seam: 4.0      # 合わせ面からの下方向オフセット
  lever:                             # 独立印刷部品
    length: 18.0                     # 上ピン中心 → 下フック先端
    thickness: 3.0                   # 板厚
    width: 8.0                       # 軸方向幅 = pivot.span_for_lever - 0.4
    finger_lift: 1.5                 # 指がかりタブ高さ
    over_center_offset: 0.0          # 0=単純フック、>0=スナップ式
    hook_inner_clearance: 0.4        # フック内径 - catch ピン径
    hole_clearance: 0.3              # レバー上端ピン穴 = pin_d + 0.3
```

## ナックル幾何の導出ルール

`pattern: [body, lid, body]` のとき、ピン総長 L から各ナックル厚を導出:

```
N         = len(pattern)                         # ナックル数(例: 3)
gaps      = N - 1                                # ナックル間隙間数
end_clear = pin_z_clearance × 2                  # ピン両端のクリア(例: 0.5×2)
usable    = L - end_clear                        # 利用可能長
thickness = (usable - gaps × z_clearance) / N    # 各ナックル厚
```

例: L=28mm, end_clear=1.0, z_clearance=0.4 → 厚 = (27 - 0.8) / 3 ≈ 8.7mm/ナックル

`pattern` を `[body, lid, body, lid, body]` に増やせばより幅広のヒンジに。

## generator.py への追加(雛形)

```python
# ----- ハードウェア解決 -----
def resolve_hardware(case_config):
    """preset から hardware の数値を解決。custom はそのまま返す。"""

# ----- ヒンジ -----
def build_hinge_assembly(body, lid, hinge_cfg, hardware):
    """両側 2 アセンブリ。pattern に従ってナックル交互生成。
    末端 body ナックルは pin_tap_pilot で下穴のみ(セルフタップ)、
    中間 lid ナックルは pin_through_clearance で通し穴。"""

# ----- ラッチ -----
def build_latch_pivot(lid, latch_cfg, hardware):
    """蓋前面、レバー回転軸の 2 ナックル。中央に span_for_lever の隙間。"""

def build_latch_catch(body, latch_cfg, hardware):
    """本体前面、catch ピン保持の 2 ナックル。
    cap_side で指定された側はキャップ(密閉)、反対側はピン挿入口として開放。
    中央は span_for_hook の露出区間。"""

def build_latch_lever(latch_cfg, hardware):
    """独立部品: 上端ピン穴(hole_clearance) + 下端フック(hook_inner_clearance)
    + 表面に finger_lift タブ。over_center_offset > 0 でフック位置をオフセット。"""

# ----- closure dispatcher -----
CLOSURE_HANDLERS = {
    "hinge_lever": build_hinge_lever_closure,
}

def build_hinge_lever_closure(body, lid, case_spec, case_config):
    hw = resolve_hardware(case_config)
    body, lid = build_hinge_assembly(body, lid, case_config["hinge"], hw)
    lid       = build_latch_pivot(lid,    case_config["latch"], hw)
    body      = build_latch_catch(body,   case_config["latch"], hw)
    lever     = build_latch_lever(        case_config["latch"], hw)
    return body, lid, lever

# ----- main 拡張 -----
# main() の export 部に latch-lever.step / .stl 出力を追加
```

## A 方式: catch ピンの片側キャップ

**根拠**: 印刷オリエンテーションが本体・蓋とも底面接地のとき、ナックル
(横向き円柱)は内側の上半分にブリッジが必要。両側完全閉鎖だと:
- ピンが挿入できない
- 円柱内部が密閉されてサポート除去不可

**A 方式の運用**:
- 本体 catch ナックル 2 個のうち、`cap_side` 側を **外端は閉じる(フラット
  キャップ)、内端は開放**
- 反対側(挿入口)は両端開放
- 完成後、挿入口側からピンを差し込み → cap 側ナックルにピン先端が突き当たる
- 外観は片側だけ穴が露出するが、`cap_side` を見える側に振り分けることで
  意匠の対称性を保てる

## /fit-check に追加されるチェック

| 項目 | 推奨 | 警告 | 失敗 |
|---|---|---|---|
| レバー回転スイープ vs 本体外周 | 干渉 0 | — | 干渉あり |
| レバー回転スイープ vs 蓋外周 | 干渉 0 | — | 干渉あり |
| フック内径 vs catch ピン径 | クリア 0.3-0.5 mm | 0.2 or 0.7 | < 0.2 or > 0.8 |
| catch ピン Z オフセット vs レバー長 | フック先端が catch ピン下を通過 | 接触のみ | 通過しない |
| 末端 body ナックル肉厚 vs セルフタップ下穴 | ≥ 1.5 mm | ≥ 1.0 mm | < 1.0 mm(割れリスク) |
| ナックル厚(導出値) | ≥ 3 mm | ≥ 2 mm | < 2 mm |
| `over_center_offset` > 0 のとき過剰締込量 | 壁の弾性内 | 弾性限界の 70-100% | 弾性限界超 |
| `cap_side` 設定が有効値 | left/right のいずれか | — | 未設定 |

実装は `output/design/fit_check.py` の `MECHANISMS` レジストリに `hinge_lever`
キーで関数を追加する形。

## ゲート

完了条件:
- `case-config.yaml` に `hardware:` `hinge:` `latch:` セクションが揃う
- `generator.py` に `build_hinge_assembly` `build_latch_pivot` `build_latch_catch`
  `build_latch_lever` `build_hinge_lever_closure` が存在
- `output/preview/case-body.step` `case-lid.step` `latch-lever.step` が出力済み
- `/fit-check` のヒンジ/ラッチ項目が ❌ なし(あれば `/review-fix` に戻る)

## 注意事項

- **責務分離**: `hardware:` は物理スペック(差し替えがハードウェアの問題)、
  `hinge:` / `latch:` は派生幾何(印刷品質や好みの問題)。利用者の通常編集は後者
- **scale の制約**: ピン/ねじ長が固定のため、`factor > ~1.4` は破綻する。
  事前に `usable = L - end_clear` を計算して制約超過を警告(P17 参照)
- **A 方式の `cap_side`**: `left` か `right` のみ。`both` を選ぶとピンが挿入
  不可になるためエラー
- **lever 部品の独立性**: スライサーで別オブジェクト扱い。サポート設定は
  本体/蓋と異なってよい(レバー単体は底面接地、サポート不要)
- **左右対称**: ヒンジ 2 アセンブリは X 軸中心線で左右対称。中心からの
  `inset_from_corner` で位置決め
- **ハイブリッドゾーン**: `case-config.yaml` を利用者が直接編集可。本スキル
  再実行時は既存値を尊重し、不足セクションのみ補完する(constitution §1)
- **過去事例の活用**: 蝶番のリリーフカット(P13)、蝶番側リップ非対称クリア
  (P14)、本体固定運用(P15)などは `@.claude/pitfalls.md` を参照して初期値に反映

## 関連

- `@.claude/skills/design/SKILL.md` — 段階 2-3、closure を抽象的に決める
- `@.claude/skills/fit-check/SKILL.md` — 段階 4-5、本スキルの固有チェック追加先
- `@.claude/skills/review-fix/SKILL.md` — 段階 4、パラメータ調整
- `@.claude/skills/export/SKILL.md` — 段階 5、3 部品の STL/3MF 出力
- `@.claude/pitfalls.md` — P13(リリーフカット忘れ)、P14(非対称クリア)、P15(本体固定)、P17(scale 制約)
- `@.claude/quality-gates.md` — 5 段階ゲート + 横断スキルとしての位置付け
