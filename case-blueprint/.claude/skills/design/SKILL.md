---
name: design
description: 段階 2-3 — input/objects/*.yaml と project-config.yaml を統合し、case-spec.yaml(ケース全体仕様)を生成。続いて CadQuery の generator.py と validator.py を出力し、STEP/STL に書き出す。
when_to_use: 「設計する」「CAD を生成」「ケース全体を組む」「採寸完了→次へ」「generator.py を作って」のとき。case-spec.yaml と generator.py / validator.py を初稿生成する。
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(.venv/bin/python *), Bash(python *)
paths:
  - "input/requirements/**/*.yaml"
  - "input/design-params/**/*.yaml"
  - "output/design/**/*.py"
model: claude-opus-4-7
---

# /design — 要件統合と設計生成 skill

## 目的

`/measure` で採寸したオブジェクト群を入力に、ケース全体の仕様(`case-spec.yaml`)、寸法パラメータ(`case-config.yaml`)、CadQuery 実装(`generator.py`)、検証ロジック(`validator.py`)を生成する。最後に generator/validator を実行し、`output/preview/` に STEP/STL を出力する。

## 前提条件

- `input/objects/` に少なくとも 1 つの `.yaml` が存在(`/measure` 完了済み)
- `project-config.yaml` が編集済み(プリンタ機種・材料・設計ルール記入済み)
- `cadquery`, `pyyaml` がインストール済み(`pip install -e ".[dev]"` 実行済み)

## 入出力

| | パス | 説明 |
|---|---|---|
| **入力** | `input/objects/*.yaml` | 採寸結果(全ファイル) |
| | `project-config.yaml` | プリンタ・材料設定 |
| | `input/requirements/case-spec.yaml` | 2 回目以降:人間補正済みの可能性あり |
| | `input/design-params/case-config.yaml` | 2 回目以降:寸法調整済みの可能性あり |
| **出力** | `input/requirements/case-spec.yaml` | 初稿(ハイブリッドゾーン、人間補正可) |
| | `input/design-params/case-config.yaml` | 初稿(L2 主要編集対象) |
| | `output/design/generator.py` | CadQuery 実装 |
| | `output/design/validator.py` | 検証ロジック |
| | `output/preview/*.step` `*.stl` | generator 実行結果 |
| | `output/reports/validation.md` | validator 実行結果 |

## 段階 2: 要件統合の手順

### Step 1: input 読み込み

- `input/objects/*.yaml` を全て読み込む
- `project-config.yaml` を読み込む
- 既存の `case-spec.yaml` があれば読み込む(2 回目以降、人間補正を尊重)

### Step 2: 構造化メタ + notes 解析 → features 推論

#### 2.1 構造化メタの優先利用(L1)

利用者が `/measure` Step 6.5 で構造化フィールドを埋めていれば **そちらを優先**:

| object.yaml キー | features 推論 |
|---|---|
| `connectors[]` | 各コネクタの `face` / `position` / `oblong` / `diameter` から `cable_port` feature を生成 |
| `controls[]` (display) | `display_window` feature(`size` を継承) |
| `controls[]` (button/switch) | `button_cutout` 等の type を新規命名 |
| `thermal.requires_ventilation: true` | `ventilation` feature を `+Z` 面に既定追加 |
| `thermal.hot_spots[]` | hot_spot の face に `ventilation` を集中配置 |
| `grip_zones[]` | 装飾 (`body_text` 等) は **これらの face を避ける** |

`controls[].face` / `connectors[].face` の集合は **印刷向き判定**(Step 5 参照)でも使われる。

#### 2.2 notes 解析(L0 フォールバック)

構造化メタが無いオブジェクトは従来通り notes キーワードから推論:

| キーワード(例) | 推論される feature type |
|---|---|
| 「ファン」「発熱」「通気」 | `ventilation` |
| 「USB」「コネクタ」「電源」 | `cable_port` |
| 「ディスプレイ」「画面」「表示」 | `display_window` |
| 「カラビナ」「吊るす」「フック」 | `carabiner_hole` |
| 「マウント」「固定」「枠」 | `mounting_bracket` |
| 既知パターン外 | 文脈から新しい type 名を Claude が考案 |

**重要**: type 名は **オープン**(enum ではない)。プロジェクト次第で新しい type が増える。

### Step 3: レイアウト方針の確認(AskUserQuestion)

- 質問 1: 「オブジェクトの配置はどうしますか?」
  - 選択肢: `stacked`(縦積み) / `side_by_side`(横並び) / `manual`(3D 配置)
  - **`auto` は廃止**: Claude が文脈から推奨を 1 つ提示し、利用者が承認する形に統一
  - `manual` は **複数 objects を 3D で配置** したい場合に選ぶ。
    `case-spec.objects[].position[x,y,z]` を直接指定し、`internal_bbox_manual()`
    が AABB 集約で内寸を逆算。`detect_collisions()` が AABB 干渉を検出する
- 質問 2: 「ケース type は?」
  - 選択肢: `lidded_box`(フタ付き箱、デフォルト)/ `custom`(notes に記載 → 段階 4 で詰める)

### Step 4: 全体寸法計算

- 各オブジェクトの dimensions + 配置 + 公差 + 内部マウント余白を計算
- 結果を `printer_bed` と比較
- 収まらなければ `case.split.enabled: true` を提案

### Step 5: case-spec.yaml 初稿生成

下記スキーマに沿った YAML を `input/requirements/case-spec.yaml` に書き出す。
**`print_orientation` の決定は Step 5.5(下記)を踏むこと**。

### Step 5.5: print_orientation 決定(`@.claude/rules/print-orientation-reasoning.md` に従う)

`case.print_orientation.body` / `lid` を機械的に決めず、以下の手順を踏む:

1. **`object.orientation_hint` の集約**:
   - 全オブジェクトの `orientation_hint.bottom_preference` / `top_preference` / `forbidden_bottoms` を集める
   - `forbidden_bottoms` は **ケース全体の選択肢**から除外する強制制約として扱う
   - `bottom_preference` / `top_preference` は同じ面を指せばその優先を尊重、矛盾すれば AskUserQuestion で利用者に確認

2. **コネクタ・ボタン面を bed 接地から除外**:
   - `connectors[].face` / `controls[].face` の集合に該当する面は body の bed 接地候補から外す
   - 例: USB-C が `-Y` にあるなら `body` の bed は `-Y` 以外(典型的には `+Z` または `-Z`)

3. **6 段階決定木の適用**(print-orientation-reasoning.md):
   - 細部・最終層を **上** に → 蓋なら top_down が既定
   - オーバーハング最小化 → ヒンジナックル等は X 軸方向に並べる
   - 強度方向 vs 層方向 → 引っ張り荷重と層方向を直交
   - 接地面積確保(反り対策、特に PETG/ABS)
   - 印刷時間・収縮(`materials-catalog.md` の `shrinkage.linear_pct` を考慮)

4. **既定の埋め草**:
   - body: `bottom_down` (= `+Z bottom`)
   - lid: `top_down` (= `-Z bottom`)
   - latch-lever (closure=hinge_lever): `-Z bottom`(平面接地)

5. **case-spec.yaml `case.layout.notes` に決定根拠を 1〜2 行で残す**:
   - 例: `print_orientation: body bottom_down(コネクタ -Y を bed に置けないため + 細部の +Z 面を終層に)`

迷ったら print-orientation-reasoning.md のルール番号(§1〜§6)を notes に書いて利用者と共有する。

### Step 6: 利用者に提示(ハイブリッドゾーン)

- 生成した `case-spec.yaml` を提示
- 「内容を確認してください。直接編集しても OK です。問題なければ『次へ』、修正したい点があれば指示してください」
- 利用者の編集を尊重し、Claude は再上書きしない(constitution §1 例外)

## 段階 3: 設計生成の手順

### Step 1: input 読み込み

- 確定した `case-spec.yaml`、`project-config.yaml`、`case-config.yaml`(なければ初稿生成へ)

### Step 2: case-config.yaml 初稿生成(初回のみ)

既存ファイルがなければ下記スキーマに沿って初稿を生成。
2 回目以降は既存値を尊重(L2 で利用者が直接編集している可能性)。

### Step 3: generator.py 生成

- CadQuery で実装
- `main()` で全 yaml 読み込み + build + export
- 機能ごとに関数を分離(L2 で書き換えやすい構造、後述「雛形構造」参照)
- features 配列を `feature_dispatcher` で type ごとに対応関数に振り分け

### Step 4: validator.py 生成

- 寸法整合・嵌合・収納可能性チェック関数を実装(後述「雛形構造」参照)

### Step 5: 実行

- `python output/design/generator.py` を実行 → `output/preview/*.step` `*.stl` 生成
- `python output/design/validator.py` を実行 → `output/reports/validation.md` 生成

### Step 6: 利用者に提示

- 「`output/preview/case-body.step` を任意の STEP/STL ビューアで開いて確認してください」
- 「`output/reports/validation.md` で検証結果を確認」
- 「修正は `/review-fix` を使うか、`input/design-params/case-config.yaml` を直接編集」

## `case-spec.yaml` スキーマ

```yaml
case:
  name: my-router-case
  type: lidded_box                      # lidded_box(フタ付き箱)/ hinged_box(蝶番蓋)/ split_shell(将来予約)
  closure:
    method: snap_fit                    # 単純: snap_fit / screws / magnetic
                                         # 複合の例: snap_lip_with_hinge, snap_lip_with_screws
                                         # ヒンジ + 独立レバーラッチ(/hinged-lid 対応): hinge_lever
    lid_axis: "+Z"                      # 蓋がどの面か。**現在 closure 実装は `+Z` のみサポート**。
                                         # 他軸を選びたい場合は generator.py で rotate して
                                         # +Z へ正規化してから closure を呼ぶ。直接渡すと
                                         # closures/__init__.py の assert_lid_axis_supported() が
                                         # NotImplementedError で fail-fast する。
    # 複合 method の場合、サブ構造を必要に応じて追加(オープン構造):
    # snap_fit: { lip_height: 2.0, fit_clearance: 0.2 }
    # hinge:    { side: "-Y", axis: "Z", knuckle_diameter: 6.0, knuckle_count_body: 2, knuckle_count_lid: 1 }
    # catch:    { side: "+Y", bump_diameter: 3.0, bump_protrusion: 0.6 }
    # hinge_lever を選んだ場合、hardware: / hinge: / latch: の詳細は /hinged-lid が埋める
  print_orientation:
    body: bottom_down                   # 印刷時の向き(底面が bed に接する基準)
    lid: top_down
  split:
    enabled: false                      # printer_bed に収まらない場合 true
    plane: horizontal                   # horizontal / vertical
  layout:
    arrangement: stacked                # stacked / side_by_side / manual(3D 配置、objects[].position 必須)
    orientation: horizontal             # horizontal / vertical
    notes: |                            # 自由記述。持ち方・ポート向き・ケーブル取り回し・内寸目標等
      持ち方: 縦持ち、長軸 X が垂直。+X 端が上(蓋)、-X 端が下(底)。
      ポート向き: USB-A / USB-C は +X 方向(蓋を開けると上端に揃う)。
      ケーブル取り回し: バッテリー → M5 は U 字型、+X 方向に 34mm の余裕。
      内寸目標: X × Y × Z = 約 125 × 54.5 × 23 mm。
  features:
    # type は文字列(オープン)。固定リストではない。Claude が必要に応じて新規 type を生成。
    # 以下は単なる例:
    - { type: ventilation,       side: top,    pattern: grid,    density: 0.3 }
    - { type: cable_port,        side: back,   position: [50, 16], diameter: 8 }
    - { type: display_window,    side: front,  size: [40, 20],   position: [0, 0] }
    - { type: carabiner_hole,    side: top,    diameter: 6 }
    - { type: carabiner_tab,     side: "+Y",   shape: trapezoid, hole_diameter: 6, base_width_x: 22, tip_width_x: 14 }
    - { type: mounting_bracket,  target: router-main, style: ribs }
    - { type: body_text,         side: "+Z",   text: "MY DEVICE", font_file: ToaHI-Rg.ttf, emboss_depth: 0.6 }

objects:                                # /measure で採寸したオブジェクトのリスト
  - id: router-main
    position: [0, 0, 0]                 # ケース内座標 (mm) — 内寸ボックスの -X/-Y/-Z 角を原点
    rotation: 0                         # Z 軸回りの回転 (度)
    note: USB ポートを +X 側に向ける、など配置の意図を文章で残せる(オプション)
```

## `case-config.yaml` スキーマ(L2 主要編集対象)

**重要**: `case-config.yaml` は固定スキーマではなく **オープン構造**:

- 下記の `walls` / `lid` / `internal` / `fillet` は最小例(あらゆるケース設計で共通の基本ブロック)
- features ごとに固有のパラメータブロックを **追加できる**(例: `carabiner_tab:` `hinge:` `catch:` `body_text:` 等)
- パラメータブロックの key 名は **features の type と一致** させる慣習
- 利用者が直接編集する場面が多いため、コメントで意味と単位を必ず明示する

```yaml
walls:
  thickness: 2.4                        # 壁厚 (mm)
  bottom_thickness: 2.4

lid:
  thickness: 2.0
  fit_clearance: 0.2                    # 嵌合の隙間(片側)
  lip_height: 3.0                       # 位置決めリップの高さ
  # axis: "+Z"                          # case-spec.closure.lid_axis を反映する場合

internal:
  object_clearance: 1.0                 # オブジェクト周辺の余裕 (mm)
  bracket_clearance: 0.3                # マウント枠との隙間
  # cable_bend_allowance: 34.0          # ケーブル湾曲のための追加余裕(必要に応じて)
  # z_margin: 1.0                       # Z 方向の追加マージン

fillet:
  outer_radius: 2.0                     # 外側角の R
  inner_radius: 0.5                     # 内側角の R
  # bottom_radius: 1.0                  # 底面エッジの R(手触り重視時)

# --- features ごとの固有パラメータブロック(オープン構造、必要に応じて追加) ---

# carabiner_tab:
#   enabled: true
#   shape: trapezoid
#   base_width_x: 22.0
#   tip_width_x: 14.0
#   extend_y: 14.0
#   thickness_z: 5.0
#   hole_diameter: 6.0
#   tip_fillet_radius: 4.0

# hinge:
#   enabled: true
#   side: "-Y"
#   knuckle_diameter: 6.0
#   pin_diameter: 2.0
#   knuckle_count_body: 2
#   knuckle_count_lid: 1
#   knuckle_clearance_z: 0.4

# catch:
#   enabled: true
#   side: "+Y"
#   bump_diameter: 3.0
#   bump_protrusion: 0.6

# body_text:
#   enabled: true
#   text: "MY DEVICE"
#   font_file: ToaHI-Rg.ttf
#   side: "+Z"
#   emboss_depth: 0.6
```

利用者は段階 4 で **このファイルを直接編集**して寸法を調整する(L2 ワークフロー)。
features を追加するときは **対応するパラメータブロックも追加** する慣習。

## features の取り扱い方針

`features` 配列の `type` は文字列で **オープン**(enum 固定なし):

- Claude は `notes` から必要な type を推論
- **既知 type の実装は `src/case_blueprint/features/` に固定済み**:
  `ventilation` / `cable_port` / `display_window` / `button_cutout` /
  `mounting_bracket` / `body_text`。`from case_blueprint import features` で
  自動 register される
- generator.py は **features を import するだけ**。`@register` 関数を generator.py
  には書かない(二重実装を避ける)
- 新しい type が必要なら **`src/case_blueprint/features/<type>.py` を新設して
  `@register("type")` する** か、当該プロジェクト限定なら generator.py に
  `@register` で追記する(後者は使い切り、前者は本リポへ還元する形)
- 利用者は段階 4 の feedback で新 type を要求できる(例:「ベルクロループを付けて」)

```python
# generator.py の features 利用は import 1 行で完結
from case_blueprint import features  # 副作用 import で全 type が register
from case_blueprint.feature_registry import apply_all
```

## generator.py の雛形構造(src 連動)

`features` / `closures` / `validators` / `fit_check` の本体実装は src 側に
集約済み。generator.py は **「設定読み込み + 形状の素体作成 + dispatcher 呼び出し
+ export」** の 4 工程に絞って書く。Claude が新規生成するコード量は最小化される。

```python
"""generator.py — CadQuery でケースを生成。単体実行: python output/design/generator.py"""
from pathlib import Path
import cadquery as cq

from case_blueprint import closures, features, loader, silhouettes  # 副作用 import で register
from case_blueprint.feature_registry import apply_all
from case_blueprint.geometry import (
    internal_bbox_stacked, internal_bbox_side_by_side,
)

del features, silhouettes  # F401 抑制(import 副作用のみ目的)


def _internal_dims(objects, case_config, layout):
    arrangement = layout.get("arrangement", "stacked")
    fn = internal_bbox_stacked if arrangement == "stacked" else internal_bbox_side_by_side
    return fn(
        objects,
        object_clearance=case_config.get("internal", {}).get("object_clearance", 1.0),
        z_margin=case_config.get("internal", {}).get("z_margin", 0.0),
    )


def _stack_lid_on_body(body, lid):
    """蓋を本体の上に物理的に配置する(lid_axis="+Z" 既定)。

    CadQuery の box() は原点中心。素体のままだと body と lid が同じ Z 範囲を
    占有して closure 前から CAD 干渉が発生する(/fit-check D が ❌ になる原因)。
    body の zmax に lid の zmin が乗るよう translate する。
    """
    body_zmax = body.val().BoundingBox().zmax
    lid_h = lid.val().BoundingBox().zlen
    return lid.translate((0, 0, body_zmax + lid_h / 2))


def main():
    cfg = loader.load_all()
    case_spec, case_config, objects = cfg["case_spec"], cfg["case_config"], cfg["objects"]

    layout = case_spec["case"].get("layout", {})
    internal = _internal_dims(objects, case_config, layout)

    # silhouette ディスパッチ(rectangular / rounded / hex / capsule)
    style_cfg = case_config.get("style", {})
    silhouette_name = style_cfg.get("silhouette", "rectangular")
    blanks = silhouettes.build(
        silhouette_name, internal,
        case_config.get("walls", {}),
        case_config.get("lid", {}),
        style_cfg,
    )
    body, lid = blanks["body_blank"], blanks["lid_blank"]
    lid = _stack_lid_on_body(body, lid)   # 物理配置(closure の前に必ず実行)

    # closure dispatcher(snap_fit / hinge_lever / ...)
    method = case_spec["case"]["closure"]["method"]
    parts = closures.build(method, body, lid, case_spec, case_config)
    body, lid = parts["case-body"], parts["case-lid"]

    # features を side で本体/蓋に振り分けて適用
    feats = case_spec["case"].get("features") or []
    # mounting_bracket(ribs)等で target object id を寸法に解決
    from case_blueprint.features.mounting_bracket import resolve_targets
    feats = resolve_targets(feats, objects)
    body = apply_all(body, [f for f in feats if f.get("side") not in ("+Z", "top")], case_config)
    lid = apply_all(lid, [f for f in feats if f.get("side") in ("+Z", "top")], case_config)

    Path("output/preview").mkdir(parents=True, exist_ok=True)
    for name, part in [("case-body", body), ("case-lid", lid)] + [
        (n, p) for n, p in parts.items() if n not in ("case-body", "case-lid") and p is not None
    ]:
        cq.exporters.export(part, f"output/preview/{name}.step")
        cq.exporters.export(part, f"output/preview/{name}.stl")
    print("✓ output/preview/ に STEP/STL を出力しました")


if __name__ == "__main__":
    main()
```

利用者プロジェクトでこの雛形を編集する場面は限定的:
- L2(数値変更): `case-config.yaml` を編集すれば generator.py は触らない
- L1(構造変更): 新 type の `apply_<type>` を generator.py 末尾に `@register("...")` で追加
- 共通化したくなったら、それを `src/case_blueprint/features/<type>.py` に昇格

## validator.py の雛形構造(src 連動)

標準チェックは `src/case_blueprint/validators.py` の `@check` / `@warn` で
登録済み。利用者プロジェクトの validator.py は **shim** として、必要なら
固有チェックを追加してから `write_report` を呼ぶだけ:

```python
"""validator.py — 設計の整合性をチェック。単体実行: python output/design/validator.py"""
from case_blueprint import loader, validators  # 副作用 import で標準 CHECKS が登録
from case_blueprint.validators import check, warn, write_report


# ----- プロジェクト固有チェック(必要なら追加) -----
# @check("固有チェック名")
# def _check_xxx(cfg):
#     assert ..., "..."


def main():
    cfg = loader.load_all()
    n_fail = write_report(cfg)
    if n_fail:
        print(f"❌ {n_fail} 件の fail")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## ゲート

### 段階 2 完了条件
- `input/requirements/case-spec.yaml` が存在し、スキーマに準拠
- 利用者が「次へ」と確認している(または初回自動進行)
- 全 objects が case-spec.yaml の objects 配列に含まれている

### 段階 3 完了条件
- `output/design/generator.py` `validator.py` が存在
- generator.py が正常実行され、`output/preview/*.step` `*.stl` が出力済み
- validator.py が実行され、❌ なし(あれば段階 4 に進む前に修正試行)

## 注意事項

- **AskUserQuestion は段階 2 の Step 3 とハイブリッドゾーン提示のみ**: 残りは自動進行(対話を最小化)
- **case-spec.yaml はハイブリッドゾーン**: Claude 初稿後、利用者が直接編集可(constitution §1)。次回実行時は編集後を尊重
- **case-config.yaml は L2 主要編集対象**: 利用者が直接編集する前提。Claude は値を尊重し、generator.py を再実行する
- **「初回 50%」を念頭に**: 完璧な初稿を目指さない。段階 4 で詰める前提(README「ワークフローのリズム感」参照)
- **features の type 拡張**: 新 type が必要なら、Claude は `FEATURE_HANDLERS` 辞書と対応関数を generator.py に追加する

## closure 詳細を `/hinged-lid` に委ねる

`closure.method = hinge_lever`(蓋を蝶番で開閉し、独立レバーでラッチ)を選んだ場合、
本 skill では closure を **抽象的に** 決めるのみで、具体的な寸法・部品分割・
ハードウェア解決は **横断スキル `/hinged-lid`** に委ねる:

- 本 skill の出力: `closure.method: hinge_lever`、`case.type: hinged_box`
- `/hinged-lid` の出力: `case-config.yaml` への `hardware:` `hinge:` `latch:` 追記、
  `generator.py` への `build_hinge_assembly` `build_latch_*` `build_latch_lever` 追加、
  `latch-lever.step/.stl` の追加出力

`/design` 完了後、`/lead` または利用者の判断で `/hinged-lid init` を呼ぶ。

## 関連

- `@.claude/skills/measure/SKILL.md` — 段階 1 の出力を入力にする(connectors / controls / orientation_hint 含む)
- `@.claude/skills/review-fix/SKILL.md` — 段階 4 でフィードバックを反映
- `@.claude/skills/hinged-lid/SKILL.md` — closure.method = hinge_lever の詳細実装
- `@.claude/rules/print-orientation-reasoning.md` — Step 5.5 の決定ルール
- `@.claude/rules/closures-catalog.md` — closure.method の選択肢
- `@.claude/rules/materials-catalog.md` — 材料別の収縮率(印刷向き判定で考慮)
- `@schemas/case-spec.schema.yaml` — case-spec.yaml の機械可読スキーマ
- `@schemas/case-config.schema.yaml` — case-config.yaml の機械可読スキーマ
- `@schemas/object.schema.yaml` — object 構造化メタ(connectors / controls / thermal 等)
