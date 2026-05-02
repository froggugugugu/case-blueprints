# Quality Gates — 5 段階の品質ゲート

このファイルは `case-blueprints` で生成されたプロジェクトにおける、5 段階ワークフローの **ゲート条件** を定義する。各段階の終了時、次に進む前に満たすべき条件と、Validator が標準で行うチェック項目を整理する。

人間の介入は任意だが、**ゲートそのものを削減してはならない**。

---

## 段階 1: オブジェクト入力(`/measure`)

### ゲート条件

1. `input/objects/` に **1 つ以上の `.yaml`** が存在
2. 全 YAML が `/measure` SKILL.md のスキーマに準拠
   - `id` が英数字+ハイフン
   - `dimensions` の値がすべて正
3. ID の重複なし
4. 利用者が「採寸完了」と明示確認

### 不通過時の対応

- `/measure` の継続または再実行
- スキーマ違反は YAML を直接編集して修正

---

## 段階 2: 要件統合(`/design` 前半)

### ゲート条件

1. `input/requirements/case-spec.yaml` が存在
2. 利用者が **「次へ」と確認**(または初回自動進行)
3. 全 objects が `case-spec.yaml` の `objects` 配列に含まれる
4. `case-spec.yaml` のフィールドが `/design` SKILL.md のスキーマに準拠
   - `case.name` `case.type` `closure.method` `closure.lid_axis` 必須
   - `print_orientation.body` `print_orientation.lid` 必須
   - `objects[]` は `id` `position` `rotation` を含む

### 不通過時の対応

- ハイブリッドゾーンで人間が補正(`case-spec.yaml` 直接編集)
- features の追加・削除は `/review-fix` ループで対応

---

## 段階 3: 設計生成(`/design` 後半)

### ゲート条件

1. `output/design/generator.py` `validator.py` が存在
2. `python output/design/generator.py` が **正常実行**(エラーなし)
3. `output/preview/*.step` `*.stl` が出力済み
4. `python output/design/validator.py` の結果に **❌ なし**

### Validator チェック項目(標準)

下記の **基本チェック** は generator が出力する全ケースで実施。features によって個別チェックを追加。

#### 基本(全ケース共通)

1. ✅ 壁厚が `min_wall_thickness` 以上
2. ✅ 蓋厚が `min_wall_thickness` 以上
3. ✅ 嵌合クリアランス(`lid.fit_clearance`)が正の値
4. ✅ ケース外寸が `printer_bed` に収まる
5. ✅ 内寸 = 外寸 - 壁厚 × 2 の関係が成立
6. ✅ オブジェクト最大長軸が内寸に収まる
7. ✅ オブジェクト同士の干渉なし

#### features 別の追加チェック例

| feature | チェック項目 |
|---|---|
| `cable_port` | ケーブル長で物体間距離をカバー可能 |
| `hinge` | ナックル肉厚 ≥ 1mm(ピン穴 - 外径)、全ナックル + クリアランスが取付辺長に収まる |
| `catch`(ラッチ) | bump_protrusion が PLA 弾性域(0.3-1.0mm) |
| `body_text` | フォントファイル存在、emboss_depth が FDM 推奨範囲(0.4-1.5mm) |
| `carabiner_tab` | 穴周りに最低マージン確保、形状が規定(台形等) |
| 任意 | 蓋方向(`lid_axis`)が想定範囲(+X/-X/+Y/-Y/+Z/-Z) |

新しい feature を追加する場合、対応するチェック関数を `validator.py` に追加する。

### 不通過時の対応

- `validator.py` の ❌ を確認 → `case-config.yaml` を調整 → 再実行
- 構造的問題(寸法不足、配置干渉)は `/review-fix` で再設計

---

## 段階 4: 可視化レビュー(`/review-fix`)

### ゲート条件

1. **直近のフィードバックが全て反映済み**(`input/feedback/<date>.md` 全件処理)
2. validator に ❌ なし
3. 利用者が **「設計確定」と明示**

### 不通過時の対応

- `/review-fix` を継続
- 「初回 50% → 段階 4 で 80%」の温度感(README「ワークフローのリズム感」参照)
- 段階 4 で完璧を目指さず、試作で見つかった問題は次の反復で対応

---

## 段階 4-5 橋渡し: 嵌合・干渉点検(`/fit-check`)

### ゲート条件

1. `output/design/fit_check.py` が存在(初回は skill が生成、利用者編集を尊重)
2. `output/reports/fit-check.md` が最新(`generator.py` より新しい)
3. ❌ がない、または利用者が明示的に「許容」を宣言

### Fit-Check 標準チェック項目

`/fit-check` SKILL.md の「チェック項目」より要約:

| カテゴリ | 主なチェック |
|---|---|
| A. 内寸マージン | object_clearance / z_margin / 各軸 vs 実測 |
| B. リップ嵌合 | fit_clearance / 蝶番側追加クリア / ラッチ側 |
| C. 蝶番設計 | ナックル肉厚 / Z 高さ / pin_clearance / knuckle_clearance_z / **body_relief_clearance** / **lid_knuckle_extra_clearance_z** |
| D. CAD 干渉 | `body.intersect(lid)` の体積、`ALLOWLIST` で意図的な重なりを管理 |
| E. 印刷可能性 | bed 収納 / 壁厚 / print_orientation / lid_axis 整合 |
| F. 拡張 | ねじ穴・差し込み・スナップ・磁石マウント等(`MECHANISMS` 追加で対応) |

### 不通過時の対応

- ❌: `/review-fix` に戻って `case-config.yaml` を調整、または構造変更
- 意図的な微小重なり: `fit_check.py` の `ALLOWLIST` に label / max_mm3 / 理由を併記して登録
- 解消したら ALLOWLIST から削除し、コメントで履歴を残す

---

## 段階 5: プリント出力(`/export`)

### ゲート条件

1. `output/print/` に STL / 3MF が出力済み
2. `output/print/slicer-notes.md` が生成済み
3. 利用者にスライサー起動が案内済み

### slicer-notes.md の必須要素

- ファイル一覧表(.3mf と .stl)
- 印刷向き(物理的に焼き込み済み + 根拠)
- サポート(部位別判断)
- 印刷設定(材料別の温度・層高・速度等)
- 後処理(必須 + 既知干渉 + 動作確認)
- トラブルシューティング表

詳細は `@.claude/skills/export/SKILL.md` を参照。

---

## 各段階を **飛ばさない** 運用

- 段階 1 を飛ばす → オブジェクトが採寸されておらず設計できない
- 段階 2 を飛ばす → ケース全体仕様が定まっておらず generator が書けない
- 段階 3 を飛ばす → 実装なしで preview を出せない
- **段階 4 を飛ばす** → 試作前に validator ❌ を見逃すリスク。最も飛ばされやすいので注意
- 段階 5 を飛ばす → スライサー設定がなく印刷品質が下がる

---

## 関連

- `@.claude/skills/measure/SKILL.md` — 段階 1
- `@.claude/skills/design/SKILL.md` — 段階 2-3
- `@.claude/skills/review-fix/SKILL.md` — 段階 4
- `@.claude/skills/export/SKILL.md` — 段階 5
- `@.claude/pitfalls.md` — 落とし穴と対処
