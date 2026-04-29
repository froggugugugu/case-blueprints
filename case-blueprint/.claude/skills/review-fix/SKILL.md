---
name: review-fix
description: 段階 4 — 可視化レビューループ。利用者からのフィードバック(自然言語 or YAML 直接編集)を取り込み、case-spec.yaml / case-config.yaml / generator.py を更新して再実行する。
---

# /review-fix — フィードバック反映 skill

## 目的

段階 4 の可視化レビューで利用者から受け取ったフィードバックを解釈し、設計に反映する:

- 自然言語フィードバック(`input/feedback/<date>.md`)を読み解く
- 利用者が直接編集した `case-config.yaml` / `case-spec.yaml` の変更を検出
- 該当ファイル(case-spec / case-config / generator.py)を更新
- generator/validator を再実行し、`output/preview/` を最新化

## 前提条件

- `/design` skill が実行済み(`output/design/generator.py` `validator.py` が存在)
- `output/preview/` に STEP/STL がある
- 利用者が Fusion / FreeCAD で確認済み(または直接 STEP/STL を確認)

## 入出力

| | パス | 説明 |
|---|---|---|
| **入力** | `input/feedback/<date>.md` | 自然言語フィードバック(任意) |
| | `input/design-params/case-config.yaml` | 利用者が直接編集している可能性あり |
| | `input/requirements/case-spec.yaml` | 利用者が直接編集している可能性あり |
| | 既存の `output/design/generator.py` `validator.py` | 既存実装 |
| **出力** | 更新された `case-spec.yaml` / `case-config.yaml` / `generator.py` / `validator.py` | 該当箇所のみ修正 |
| | `output/preview/*.step` `*.stl` | 再生成 |
| | `output/reports/validation.md` | 再生成 |

## フィードバックの種類

### A. 数値変更(L2 メイン)

- 利用者が `case-config.yaml` を直接編集している
- 例: `walls.thickness: 2.4` → `2.0`、`lid.fit_clearance: 0.2` → `0.3`(case-config.yaml の入れ子構造を反映)
- 処理: 差分を検出し、`generator.py` を再実行するだけ

### B. 構造変更(自然言語)

- 利用者が `input/feedback/<date>.md` に日本語で記述
- 例:「左奥と右手前に M3 ねじ穴を 4 個追加してください」「ヒンジを左側に」
- 処理:
  1. フィードバックを解釈し、変更すべき箇所を特定
  2. `case-spec.yaml` の features 配列を更新
  3. 必要なら `generator.py` に新しい feature 関数を追加
  4. 再実行

## 処理フロー

### Step 1: フィードバックの収集

- `input/feedback/` 配下の `.md` ファイルを全て読み込む
- 既処理のフィードバック(タイムスタンプ等で判定)を除外
- `case-config.yaml` の差分(git diff または mtime 比較)で数値編集を検出
- `case-spec.yaml` の差分で構造編集を検出

### Step 2: フィードバックの分類

| パターン | 分類 |
|---|---|
| `case-config.yaml` の数値編集 | A |
| 「○ mm に変えて」「壁を厚く」 | A |
| 「○ を追加して」「○ を削除」 | B |
| 「分割を変えて」「ヒンジに」 | B |
| 「位置をずらして」 | A or B(features の position 編集 = B) |

判別が曖昧な場合は AskUserQuestion で確認:

```
Q: このフィードバックは数値調整(壁厚など)ですか? それとも構造変更(穴を追加など)ですか?
A: 数値調整 / 構造変更 / 両方
```

### Step 3: 反映

#### A の場合

- `case-config.yaml` の値を尊重(Claude は再上書きしない)
- `generator.py` をそのまま実行

#### B の場合

- `case-spec.yaml` の features 配列を更新(追加・削除・position 変更)
- 新 feature type が必要な場合、`generator.py` の `FEATURE_HANDLERS` 辞書と対応関数を追加
- 例:「ベルクロループを付けて」→ `velcro_loop` type を新設、`apply_velcro_loop()` を generator.py に追加

### Step 4: 再実行

- `python output/design/generator.py` 実行
- `python output/design/validator.py` 実行
- 結果を `output/preview/` `output/reports/` に上書き

### Step 5: 利用者に提示

- 「修正点を反映しました。`output/preview/case-body.step` を再度確認してください」
- 「次のフィードバックがあれば `input/feedback/` に追記、または `case-config.yaml` を直接編集」
- 「設計確定なら `/export` に進んでください」

## ゲート

`/export` skill に進む前に:

1. 直近のフィードバックが全て反映済み
2. validator に ❌ なし
3. 利用者が「設計確定」と明示している

ゲート未達の場合は `/review-fix` の継続を促す。

## 注意事項

- **ハイブリッドゾーンの尊重**: 利用者が `case-spec.yaml` / `case-config.yaml` を直接編集した内容を Claude が上書きしてはいけない(constitution §1)
- **フィードバックの履歴保存**: `input/feedback/<date>.md` は処理後も残す(設計判断のトレーサビリティ)
- **解釈の曖昧さ**: フィードバックが曖昧な場合、AskUserQuestion で確認(例:「『正面』とは正面パネル全体ですか? 中心ですか?」)
- **新 type の命名**: 利用者が使った言葉を反映(「ベルクロ」→ `velcro_loop`、「磁石マウント」→ `magnetic_mount`)。snake_case で統一
- **「初回 50% → 段階 4 で 80%」** の前提を維持。段階 4 で全てを完成させようとしない(README「ワークフローのリズム感」)

## 関連

- `@.claude/skills/design/SKILL.md` — 段階 2-3、初回設計
- `@.claude/skills/export/SKILL.md` — 段階 5、最終出力
