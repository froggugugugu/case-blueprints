---
name: measure
description: 段階 1 — ケースに収納するオブジェクトを対話的に採寸し、input/objects/<id>.yaml に 1 ファイル 1 オブジェクトで保存する。座標軸と「正面」の基準を提示してから採寸を促す。
when_to_use: 「採寸する」「測りたい」「オブジェクト追加」「収納物の登録」「ノギスで測る」のとき。
allowed-tools: Read, Write, Edit, Glob, Bash(.venv/bin/python -m case_blueprint.cli validate-schema *)
paths:
  - "input/objects/**/*.yaml"
model: inherit
---

# /measure — オブジェクト採寸 skill

## 目的

ケースの中身となるオブジェクトの寸法・公差・特記事項を、対話的かつ標準化された手順で記録する。
人間が後でファイルを直接編集できる YAML 形式で保存し、`design` skill が読み取れる状態にする。

## 前提条件

- 利用者プロジェクトのルートで Claude Code が起動している
- `project-config.yaml` が存在する(プリンタ機種・材料の設定済み)
- `input/objects/` ディレクトリが存在する(`setup.sh` で作成済み)

## 入出力

| | 内容 |
|---|---|
| **入力** | 対話(AskUserQuestion で人間から取得) |
| **出力** | `input/objects/<id>.yaml`(1 ファイル 1 オブジェクト) |

## 採寸基準(必ず最初に利用者に提示する)

### 座標軸の定義 — オブジェクトを正面から見て

```
       Z (Height: 高さ)
       ↑
       │   ┌──────────┐
       │  ╱           ╱│
       │ ┌──────────┐  │
       │ │   正面   │  │
       │ │          │  │
       │ │          │ ╱
       │ └──────────┘
       └────────→ X (Width: 横方向)
      ╱
     ╱
    Y (Depth: 奥行)
```

| 軸 | 名称 | 意味 |
|---|---|---|
| X | **Width** | 正面から見て**左右**の長さ(横方向) |
| Y | **Depth** | 正面から見て**手前 → 奥**の長さ(奥行方向) |
| Z | **Height** | 上下の高さ |

### 「正面」の決め方(優先順)

1. **コネクタ・操作部が多い面**(USB ポート、電源スイッチ、LED など)
2. **使用時に見える面**(ディスプレイ、ロゴ、ボタン)
3. 上記が決まらない場合は **任意に決めて `notes` に記載**

### 「底面」の決め方

プリンタベッドに置く想定の面を底面とする(通常は重力方向に置いたときの底)。
これにより印刷向きの判断が後段で楽になる。

## 手順(8 + 1 ステップ)

各ステップは AskUserQuestion で人間から取得。回答が曖昧な場合は再質問する。

### Step 1: オブジェクト ID

- 質問: 「このオブジェクトの ID を入力してください(英数字+ハイフン)」
- バリデーション: `^[a-z0-9][a-z0-9-]*$`(小文字英数字+ハイフン、先頭は英数字)
- 例: `router-main`, `ssd-1tb`, `cable-usb-c`
- 既存の `input/objects/<id>.yaml` と重複しないか確認

### Step 2: 表示名

- 質問: 「表示名(日本語可)を入力してください」
- 自由入力(例: `ルーター本体`)

### Step 3: 形状カテゴリ

- 質問: 「形状カテゴリを選んでください」
- 選択肢: `rectangular`(直方体) / `cylindrical`(円筒) / `custom`(任意形状)

### Step 3.5: 採寸基準の提示と「正面」の確認

- まず**「採寸基準」セクションの座標軸図と説明を提示**する
- 次に AskUserQuestion で「正面」を確認:
  - 質問: 「このオブジェクトの『正面』はどの面ですか?」
  - 選択肢:
    - `connector_side` — コネクタ・操作部が多い面
    - `display_side` — ディスプレイ・ロゴ・ボタンが見える面
    - `custom` — その他(`notes` に記載を促す)
- 選択後、「この向きで Width / Depth / Height を測ってください」と再確認してから Step 4 へ

### Step 4: 寸法(形状に応じて分岐)

形状カテゴリごとに必要な寸法を AskUserQuestion で取得:

- **rectangular**: `width`, `depth`, `height` (mm, 正の数)
- **cylindrical**: `diameter`, `height` (mm, 正の数)
- **custom**: 外形を囲む直方体(bounding box)として `width`, `depth`, `height` を取得 + `notes` に詳細記述を促す

数値は浮動小数点で受け取り、0 以下は再入力を求める。

### Step 5: 公差

- 質問: 「公差(mm)を入力してください。デフォルトは 0.5 です」
- デフォルト: `0.5`
- 製造ばらつきや測定誤差を吸収するため、ケース内寸はこの値分だけ拡張される

### Step 6: 特記事項

- 質問: 「特記事項を自由記述してください。なければ空欄で OK」
- 自由入力(複数行可)
- **書くべき内容**(後段の `/design` で Claude が features 配列・配置・構造に変換する材料):
  - **物理的特性**: 発熱、ファン、振動、防水要否、許容温度
  - **コネクタ・操作**: USB-C × 2 / 電源スイッチの位置 / LED / GROVE ポート など、**どの面にあるか** を明示
  - **接続関係**: 他オブジェクトとどうつながるか(USB-C ケーブル / GROVE ケーブル / I2C / 電源など)。**ケーブル長**と**取り回し**(短くて済むか、湾曲が必要か)も書く
  - **運用方針**: 「常時開放 / 蓋を開けて操作 / 完全密閉」「充電は外装穴経由 / 蓋を開けて充電」など
  - **使い方の意図**: 用途(アウトドア / デスク常設 / 車載)、装着方法(カラビナ吊り / マウントブラケット)、ロック方式(防水ネジ止め / 磁石 / スナップフィット)
  - **表示・操作面**: ディスプレイの位置、ボタン位置、視認性要件(常時見たい / 蓋を閉めて隠す)
  - **サイズ最適化方針**: 「コンパクト優先 / 余裕重視 / 拡張性確保」など、設計の優先軸
- 例:
  ```
  物理: ファン内蔵、底面通気必要
  コネクタ: 背面 USB-C × 2、電源 × 1、正面右下に LED、左側面 GROVE × 1
  接続: M5 ↔ GPS = GROVE ケーブル(短く)、M5 ↔ バッテリー = USB-C ケーブル(湾曲必要)
  運用: 蓋を閉めた状態で使用、操作開口部ゼロ。充電は蓋を開けて行う
  用途: アウトドア、カラビナで吊るす
  表示: ディスプレイは蓋で覆う(視認不要)
  ロック: 工具なしで開閉(スナップフィット希望)
  サイズ: 3 機器をできるだけコンパクトに収める
  ```

### Step 6.5: 構造化メタの取得(任意、L1 推奨)

**注意**: ここから先の 6 項目はすべて optional。利用者が「不要」「あとで」と答えたらそのまま Step 7 へ進む。
ただし、ここに値が入ると `/design` の features 推論・印刷向き判定・`/fit-check` の精度が**目に見えて上がる**ため、軽く誘導する。

質問は AskUserQuestion で 1 つずつ。回答は構造化された YAML として保存する(schema 仕様は `@schemas/object.schema.yaml`)。

#### 6.5-A. コネクタ / 操作部の構造化(`connectors[]` / `controls[]`)

- 質問: 「コネクタやボタン・LED の位置を構造化して残しますか?(yes/skip)」
- yes の場合、以下を 1 件ずつ繰り返し:
  - 種別: `USB-C` / `USB-A` / `HDMI` / `DC` / `3.5mm` / `button` / `switch` / `dial` / `led` / `display` 等
  - 配置面: `+X` / `-X` / `+Y` / `-Y` / `+Z` / `-Z`(または通称: front / back / left / right / top / bottom)
  - 種別が **コネクタ** なら `connectors[]` に、ボタン等なら `controls[]` に振り分け
- 「もう無い」と答えるまで繰り返す
- これらは `cable_port` / `display_window` / `button_cutout` feature の position 推論に直結するので、面と簡易的な位置だけでも書く価値が高い

#### 6.5-B. 発熱(`thermal`)

- 質問: 「発熱しますか?(yes/skip)」
- yes の場合:
  - 局所発熱点があれば `hot_spots[]` に face / position / max_temp_c
  - 全体: `max_surface_temp_c` / `requires_ventilation: true`
- これがあると `/design` が `ventilation` feature を自動提案する

#### 6.5-C. 重量(`weight_g`)

- 質問: 「重量(g)が分かっていれば入力してください。不明なら skip」
- 数値があれば magnetic closure の保持力検証(P30 想定)や落下耐性に使える

#### 6.5-D. 把持面(`grip_zones[]`)

- 質問: 「使用時に手で持つ面はありますか?(複数可、skip 可)」
- 例: `top` / `+Y` / `front`
- 装飾(emboss / 模様)を**避けるべき面**として `/design` に渡される

#### 6.5-E. 印刷向きヒント(`orientation_hint`)

- 質問: 「印刷時に底にしたい面 / 終層に出したい面 / 底にできない面はありますか?(skip 可)」
- 例: `bottom_preference: "+Z"` / `top_preference: "-Z"` / `forbidden_bottoms: ["+X"]`
- これは `/design` の `print_orientation` 決定で **最優先で尊重される**(`@.claude/rules/print-orientation-reasoning.md` 参照)
- コネクタ面が `forbidden_bottoms` に入ると、その面が bed 接地にならない設計が選ばれる

### Step 7: 確認と保存

- 入力内容を YAML 形式でプレビュー表示
- 質問: 「この内容で `input/objects/<id>.yaml` に保存してよいですか?(yes/no)」
- yes → 保存
- no → どのフィールドを修正するか聞いて該当 Step に戻る

### Step 8: ループ判定

- 質問: 「他のオブジェクトを採寸しますか?(yes/no)」
- yes → Step 1 から繰り返し
- no → skill 終了、ゲートチェックへ

## `input/objects/<id>.yaml` スキーマ

```yaml
id: router-main                  # Step 1: 英数字+ハイフン、ファイル名と一致
name: ルーター本体                # Step 2: 表示名(日本語可)
shape: rectangular               # Step 3: rectangular / cylindrical / custom
front_face: connector_side       # Step 3.5: connector_side / display_side / custom
dimensions:                      # Step 4: 形状に応じてキーが変わる
  width: 168.0                   #   - rectangular: width / depth / height
  depth: 124.0                   #   - cylindrical: diameter / height
  height: 33.0                   #   - custom: bounding box の width / depth / height
tolerance: 0.5                   # Step 5: 公差 (mm)
notes: |                         # Step 6: 自由記述(空可)
  本体はファン内蔵で発熱あり。
  背面に USB-C × 2、電源コネクタ × 1。

# --- Step 6.5: 構造化メタ(全て optional)---
# 書けば /design の features 推論・印刷向き判定・/fit-check の精度が上がる。
# 書かなくても従来通り notes だけで動く。

connectors:
  - type: USB-C
    face: "-Y"                   # 背面
    position: [0, 10]            # 面中心からのオフセット (u, v)
  - type: USB-C
    face: "-Y"
    position: [-25, 10]
  - type: DC
    face: "-Y"
    position: [25, 10]
controls:
  - type: led
    face: "+Y"
    position: [40, -10]
  - type: switch
    face: "+Y"
    position: [-40, 0]
thermal:
  hot_spots:
    - face: "+Z"
      position: [0, 0]
      max_temp_c: 65
  max_surface_temp_c: 50
  requires_ventilation: true
weight_g: 220
grip_zones: ["+Z", "front"]
orientation_hint:
  bottom_preference: "+Z"
  forbidden_bottoms: ["-Y"]      # コネクタ面は底にしない
```

## ゲート(段階 1 完了条件)

`/design` skill に進む前に、以下を満たす必要がある:

1. `input/objects/` に **1 つ以上の `.yaml` ファイル**が存在する
2. すべての YAML が上記スキーマに準拠している(ID 重複なし、`dimensions` の値が正)
3. 利用者が「採寸完了」と明示的に確認している

ゲート未達の場合は `/measure` の継続または再実行を促す。

## 注意事項

- **Claude が YAML を直接書き換えない**: skill 終了後、人間が YAML を直接編集できる(constitution §1)。次回 `/measure` 実行時は既存 YAML を読み込み、追加分のみ対話する
- **配列ではなく 1 ファイル 1 オブジェクト**: 複数オブジェクトの集約は `design` skill 側で行う
- **採寸の精度**: ノギス推奨。定規での目測は `tolerance` を大きめ(1.0mm 以上)に設定するよう促す

## 関連

- `@.claude/skills/design/SKILL.md` — 段階 2-3、`/measure` の出力を入力にする
- `@schemas/object.schema.yaml` — 機械可読スキーマ(connectors / controls / thermal / orientation_hint 等含む)
- `@schemas/case-spec.schema.yaml` — 後段スキーマ
- `@.claude/rules/print-orientation-reasoning.md` — `orientation_hint` がここで使われる
