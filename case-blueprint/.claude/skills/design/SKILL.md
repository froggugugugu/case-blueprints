---
name: design
description: 段階 2-3 — input/objects/*.yaml と project-config.yaml を統合し、case-spec.yaml(ケース全体仕様)を生成。続いて CadQuery の generator.py と validator.py を出力し、STEP/STL に書き出す。
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

### Step 2: notes 解析と features 推論

各オブジェクトの `notes` フィールドを解析し、必要な features を推論する:

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
  - 選択肢: `stacked`(縦積み) / `side_by_side`(横並び) / `auto`(Claude 最適化)
- 質問 2: 「ケース type は?」
  - 選択肢: `lidded_box`(フタ付き箱、デフォルト)/ `custom`(notes に記載 → 段階 4 で詰める)

### Step 4: 全体寸法計算

- 各オブジェクトの dimensions + 配置 + 公差 + 内部マウント余白を計算
- 結果を `printer_bed` と比較
- 収まらなければ `case.split.enabled: true` を提案

### Step 5: case-spec.yaml 初稿生成

下記スキーマに沿った YAML を `input/requirements/case-spec.yaml` に書き出す。

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

- 「`output/preview/case-body.step` を Fusion / FreeCAD で開いて確認してください」
- 「`output/reports/validation.md` で検証結果を確認」
- 「修正は `/review-fix` を使うか、`input/design-params/case-config.yaml` を直接編集」

## `case-spec.yaml` スキーマ

```yaml
case:
  name: my-router-case
  type: lidded_box                      # 当面 lidded_box。将来 hinged_box / split_shell を予約
  closure:
    method: snap_fit                    # 単純: snap_fit / screws / magnetic
                                         # 複合の例: snap_lip_with_hinge, snap_lip_with_screws
    lid_axis: "+Z"                      # 蓋がどの面か(+X / -X / +Y / -Y / +Z / -Z)
    # 複合 method の場合、サブ構造を必要に応じて追加(オープン構造):
    # snap_fit: { lip_height: 2.0, fit_clearance: 0.2 }
    # hinge:    { side: "-Y", axis: "Z", knuckle_diameter: 6.0, knuckle_count_body: 2, knuckle_count_lid: 1 }
    # catch:    { side: "+Y", bump_diameter: 3.0, bump_protrusion: 0.6 }
  print_orientation:
    body: bottom_down                   # 印刷時の向き(底面が bed に接する基準)
    lid: top_down
  split:
    enabled: false                      # printer_bed に収まらない場合 true
    plane: horizontal                   # horizontal / vertical
  layout:
    arrangement: stacked                # stacked / side_by_side / auto
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
- 既知 type に雛形関数があれば再利用
- **新しい type が必要になったら、generator.py に対応関数を追加**
- 利用者は段階 4 の feedback で新 type を要求できる(例:「ベルクロループを付けて」)

generator.py の `feature_dispatcher` で type → 実装関数にマッピング:

```python
FEATURE_HANDLERS = {
    "ventilation": apply_ventilation,
    "cable_port": apply_cable_port,
    # 新しい type を Claude が必要に応じて追加
}
```

## generator.py の雛形構造

```python
"""generator.py — CadQuery でケースを生成。単体実行: python output/design/generator.py"""
import yaml
import cadquery as cq
from pathlib import Path

# ----- 設定読み込み -----
def load_configs(): ...

# ----- 主要関数(L2 で書き換えやすい単位) -----
def calculate_internal_dimensions(objects, case_config): ...
def build_case_body(internal_dims, case_config): ...
def build_lid(internal_dims, case_config): ...
def apply_features(body, lid, case_spec, case_config): ...

# ----- 個別 feature 実装(必要に応じて Claude が追加) -----
def apply_ventilation(part, feature, case_config): ...
def apply_cable_port(part, feature, case_config): ...

FEATURE_HANDLERS = {
    "ventilation": apply_ventilation,
    "cable_port": apply_cable_port,
}

# ----- main -----
def main():
    project, case_spec, case_config, objects = load_configs()
    internal = calculate_internal_dimensions(objects, case_config)
    body = build_case_body(internal, case_config)
    lid = build_lid(internal, case_config)
    body, lid = apply_features(body, lid, case_spec, case_config)

    Path("output/preview").mkdir(parents=True, exist_ok=True)
    cq.exporters.export(body, "output/preview/case-body.step")
    cq.exporters.export(body, "output/preview/case-body.stl")
    cq.exporters.export(lid,  "output/preview/case-lid.step")
    cq.exporters.export(lid,  "output/preview/case-lid.stl")
    print("✓ output/preview/ に STEP/STL を出力しました")

if __name__ == "__main__":
    main()
```

## validator.py の雛形構造

```python
"""validator.py — 設計の整合性をチェック。単体実行: python output/design/validator.py"""
import yaml
from pathlib import Path

CHECKS = []
def check(name):
    def wrap(fn):
        CHECKS.append((name, fn))
        return fn
    return wrap

@check("外寸 = 内寸 + 壁厚 × 2")
def check_outer_inner_relation(cfg): ...

@check("嵌合クリアランスが正の値")
def check_fit_clearance(cfg): ...

@check("ケースが printer_bed に収まる")
def check_printer_bed(cfg): ...

@check("オブジェクト同士の干渉なし")
def check_object_collision(cfg): ...

def main():
    cfg = load_configs()
    report = ["# Validation Report\n"]
    for name, fn in CHECKS:
        try:
            fn(cfg)
            report.append(f"- ✅ {name}")
        except AssertionError as e:
            report.append(f"- ❌ {name}: {e}")

    Path("output/reports").mkdir(parents=True, exist_ok=True)
    Path("output/reports/validation.md").write_text("\n".join(report))
    print("✓ output/reports/validation.md を出力しました")

if __name__ == "__main__":
    main()
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

## 関連

- `@.claude/skills/measure/SKILL.md` — 段階 1 の出力を入力にする
- `@.claude/skills/review-fix/SKILL.md` — 段階 4 でフィードバックを反映
- `@schemas/case-spec.schema.yaml` — case-spec.yaml の機械可読スキーマ(構築中)
- `@schemas/case-config.schema.yaml` — case-config.yaml の機械可読スキーマ(構築中)
