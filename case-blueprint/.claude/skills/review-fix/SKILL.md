---
name: review-fix
description: 段階 4 — 可視化レビューループ。利用者からのフィードバック(自然言語 or YAML 直接編集)を取り込み、case-spec.yaml / case-config.yaml / generator.py を更新して再実行する。
when_to_use: 「ここを直したい」「壁を厚くして」「○○ を追加」「印刷したらハマらない」「フィードバックを反映」「case-config.yaml を編集した後の再実行」のとき。
argument-hint: "[feedback-file | measurements]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(git diff *), Bash(.venv/bin/python *), Bash(python *)
paths:
  - "input/feedback/**/*.md"
model: inherit
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
- 利用者が STEP/STL ビューアで確認済み(または直接ファイルを確認)

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

### C. 物理ループ(実測フィードバック)

- 試作を印刷後、ノギス・組立確認の結果を **構造化された yaml** で受け取る
- 様式: `@.claude/rules/measurement-feedback.md`
- 雛形: `@.claude/templates/feedback-measurements.yaml`
- 利用者ファイル名: `input/feedback/<YYYY-MM-DD>-measurements.yaml`
- 処理:
  1. `measurements[]` の `action`(ok/loose/tight/interfere/gap)から補正候補を推論
  2. `adjustments_applied[]` を `case-config.yaml` に反映
  3. 本体不変原則(P15)を確認 — `requires_body_reprint: true` の項目は利用者に再確認
  4. `generator.py` 再実行 → `validator.py` → `output/preview/` 更新
  5. 解消しない `unresolved[]` は次イテレーションへ持ち越し

## 引数 `measurements` モード

`/review-fix measurements` と呼ばれた場合は **C. 物理ループ** に直行する:

1. 雛形をコピー(無ければ): `cp .claude/templates/feedback-measurements.yaml input/feedback/$(date +%Y-%m-%d)-measurements.yaml`
2. 利用者にファイルを開いて測定値を埋めてもらう
3. 利用者が「埋めた」と返答したら、yaml を読んで Step 3-C 以降を実行

引数なしの通常モードでは A/B/C すべての feedback を統合的に処理する。

## 処理フロー

### Step 1: フィードバックの収集

- `input/feedback/` 配下の `.md` / `.yaml` ファイルを全て読み込む
  - `<date>-measurements.yaml` は **C 種(構造化実測)** として別ルートで処理
  - `<date>.md` は **A/B 種(自然言語)** として処理
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
| **「○○ の代わりに △△ にしたい」(type 自体の置換)** | **B(構造変更 + type 名変更)** |
| **「蓋の方向を +Z から +X に」(closure / case 構造の変更)** | **B(case 全体の構造変更)** |

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
- **type の置換**(例: `carabiner_hole` → `carabiner_tab`)の場合、古い type の関数を削除し、新しい type の関数を追加。`case-config.yaml` のパラメータブロック名も連動更新
- **case 全体の構造変更**(例: `lid_axis` 変更、`closure.method` の置換)の場合、`build_case_body` / `build_lid` を **書き直し**、関連する features の position も再計算が必要

#### C の場合(実測フィードバック)

`@.claude/rules/measurement-feedback.md` の規約に沿う:

1. `<date>-measurements.yaml` を `yaml.safe_load` で読む
2. `adjustments_applied[]` を順に `case-config.yaml` に反映(指定があればそのまま、無ければ推論)
3. `measurements[]` の `action` から推論する場合の対応表:
   - `tight` → 該当する `fit_clearance` を +0.05(機構別: lid / hinge / magnet)
   - `loose` → 該当する `fit_clearance` を −0.05
   - `interfere` → 構造変更(リリーフカット追加 / 寸法見直し)。**利用者確認必須**
   - `gap` → 蓋寸法 / 印刷向き / `fit_clearance` を見直し
4. `requires_body_reprint: true` の項目があれば、利用者に「本体を再印刷します。よろしいですか?」と確認(P15)
5. 反映完了後、`unresolved[]` を要約して提示し、次イテレーションの方針を相談
6. ALLOWLIST 編集が必要な場合は `fit_check.py` の `ALLOWLIST` を更新 + `allowlist_changes` に履歴を残す

### Step 4: 再実行

- `python output/design/generator.py` 実行
- `python output/design/validator.py` 実行
- 結果を `output/preview/` `output/reports/` に上書き

### Step 5: 利用者に提示

- 「修正点を反映しました。`output/preview/case-body.step` を再度確認してください」
- 「次のフィードバックがあれば `input/feedback/` に追記、または `case-config.yaml` を直接編集」
- 「設計確定なら `/export` に進んでください」

## ゲート

`/fit-check` または `/export` skill に進む前に:

1. 直近のフィードバックが全て反映済み
2. validator に ❌ なし
3. 利用者が「設計確定」と明示している

`/fit-check` を間に挟むことを推奨(嵌合の網羅チェック)。
ゲート未達の場合は `/review-fix` の継続を促す。

## fit-check との連携

段階 4 のフィードバックでクリアランスや干渉に関する問題が出た場合:

- 個別フィードバックの反映は `/review-fix` で行う(case-config.yaml / generator.py 更新)
- 反映後、**`/fit-check` で網羅的に再検証**(過去事例ベースの推奨値と CAD 干渉を一括チェック)
- ❌ や ⚠ が出たら更に `/review-fix` でループ

「直近フィードバック反映」と「過去事例網羅+CAD 干渉」は役割分離されているので、両方走らせるのが安全。

## 本体固定運用への対応

長時間印刷の本体を再印刷したくない場合のフィードバック対応:

- フィードバックが「蓋のみで吸収可能か」をまず判定
- 可能なら蓋専用パラメータ(`lid_knuckle_extra_clearance_z`、`fit_clearance` の蓋側のみ縮小、リップ非対称クリア等)で対応
- 不可なら本体パラメータも変更が必要だが、**ハッシュ確認**(`md5 case-body.stl` 等)で実際に変わったかを記録
- generator.py で本体・蓋パラメータを分離するコメントを残す

## 注意事項

- **ハイブリッドゾーンの尊重**: 利用者が `case-spec.yaml` / `case-config.yaml` を直接編集した内容を Claude が上書きしてはいけない(constitution §1)
- **フィードバックの履歴保存**: `input/feedback/<date>.md` は処理後も残す(設計判断のトレーサビリティ)
- **解釈の曖昧さ**: フィードバックが曖昧な場合、AskUserQuestion で確認(例:「『正面』とは正面パネル全体ですか? 中心ですか?」)
- **新 type の命名**: 利用者が使った言葉を反映(「ベルクロ」→ `velcro_loop`、「磁石マウント」→ `magnetic_mount`)。snake_case で統一
- **「初回 50% → 段階 4 で 80%」** の前提を維持。段階 4 で全てを完成させようとしない(README「ワークフローのリズム感」)

## 関連

- `@.claude/skills/design/SKILL.md` — 段階 2-3、初回設計
- `@.claude/skills/export/SKILL.md` — 段階 5、最終出力
