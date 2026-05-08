---
name: export
description: 段階 5 — 確定済みの設計から最終プリント用 STL/3MF を出力し、スライサー設定の推奨を slicer-notes.md に記述する。
when_to_use: 利用者が「印刷ファイルを出す」「最終 STL 確定」「3MF エクスポート」と **明示的に** 指示したときのみ。誤起動防止のため自動呼び出しは無効化(disable-model-invocation: true)。
allowed-tools: Read, Write, Edit, Glob, Bash(.venv/bin/python *), Bash(python *), Bash(shasum *), Bash(md5sum *)
paths:
  - "output/print/**"
disable-model-invocation: true
model: inherit
---

# /export — プリント出力 skill

## 目的

段階 4 で設計が確定した状態から、最終 3D プリント用ファイルを出力する:

- `generator.py` を実行し、`output/print/` に最終 STL / 3MF を生成
- スライサー設定の推奨(印刷向き、サポート要否、インフィル、温度等)を `output/print/slicer-notes.md` に記述
- 利用者にスライサー起動を促す

## 前提条件

- `/review-fix` skill のゲートが通過している(設計確定)
- `output/design/generator.py` が確定状態
- `output/reports/validation.md` で ❌ がない
- **推奨**: `/fit-check` を実行済みで `output/reports/fit-check.md` が ❌ なし(嵌合・干渉の網羅チェック済み)

## 入出力

| | パス | 説明 |
|---|---|---|
| **入力** | `output/design/generator.py` | 確定済み実装 |
| | `input/requirements/case-spec.yaml` | `print_orientation` を読む |
| | `project-config.yaml` | `default_material`, `printer_bed` |
| **出力** | `output/print/case-body.stl` | 最終プリント用 |
| | `output/print/case-lid.stl` | 同上 |
| | `output/print/case-body.3mf` | 3MF(印刷向きを埋め込める、推奨) |
| | `output/print/case-lid.3mf` | 同上 |
| | `output/print/latch-lever.stl` `.3mf` | `closure.method = hinge_lever` のとき追加(`/hinged-lid` 経由) |
| | `output/print/slicer-notes.md` | スライサー設定推奨 |

## 処理フロー

### Step 1: 確定確認

- `/review-fix` skill のゲートが通過しているか確認
- 通過していなければ「先に `/review-fix` で設計を確定してください」と促す

### Step 2: 最終 generator.py 実行

- `python output/design/generator.py` を実行(エクスポート機能を含む形に拡張)
- STL を `output/print/` に出力
- 可能なら 3MF も出力(印刷向きを埋め込める)

### Step 3: スライサー設定の推奨を生成(材料カタログ連動)

#### 3.0 材料データの取得

`project-config.yaml` の `print_settings.default_material` から `materials.slicer_recommendations(mid)` を呼んで推奨値を取得する:

```python
from case_blueprint import materials
rec = materials.slicer_recommendations(project["print_settings"]["default_material"])
```

返り値は以下の構造(`@.claude/rules/materials-catalog.md` に対応):

| キー | 中身 |
|---|---|
| `nozzle_temp_c.{min,max,recommended,first_layer}` | ノズル温度 (°C) |
| `bed_temp_c.{min,max,recommended,first_layer}` | ベッド温度 (°C) |
| `enclosure_required` | 密閉チャンバー必須か |
| `layer_height_mm.{min,max,recommended}` | 層高 (mm) |
| `infill_pct.{min,max,recommended,outdoor_or_hard_use}` | インフィル密度 (%) |
| `print_speed_mm_s.{min,max,recommended,wall_top_layer}` | 印刷速度 (mm/s) |
| `fan.{first_layer_pct,subsequent_pct,note?}` | ファン設定 |
| `support_difficulty` | サポート除去難度 |
| `warnings` | 印刷時注意リスト(反り・層間接着・UV 等) |

これを下記 3.4 / 3.5 の表に転記する。**ハードコードしない**。利用者が `default_material` を切り替えれば自動的に連動する。

`output/print/slicer-notes.md` に以下のテンプレ構造で記述:

#### 3.1 ファイル一覧

```markdown
## ファイル一覧

| ファイル | 用途 | 印刷向き埋込 |
|---|---|---|
| `case-body.3mf` | 本体(推奨) | あり |
| `case-body.stl` | 本体(互換用) | あり(物理的に回転済み) |
| `case-lid.3mf`  | 蓋(推奨) | あり |
| `case-lid.stl`  | 蓋(互換用) | あり(物理的に回転済み) |
| `latch-lever.3mf` | レバー(closure=hinge_lever のときのみ) | あり |
| `latch-lever.stl` | レバー(同上、互換用) | あり |

3MF を推奨。お使いのスライサーで開けば配置済み(3MF 対応スライサーであれば配置・向きが反映される)。
STL を使う場合も既に印刷向きに回転済みなので、スライサーで再配置不要。
レバーは独立部品なので、本体・蓋とは別オブジェクト扱い(サポート設定を分けてよい)。
```

#### 3.2 印刷向きの根拠

`case-spec.yaml` の `print_orientation` から、bed 接地面と印刷後の高さを記述。`printer_bed` との余裕も比較:

```markdown
## 印刷向き(物理的に焼き込み済み)

| パーツ | 向き | bed 接地面 | 印刷後の高さ Z |
|---|---|---|---|
| `case-body` | `bottom_down` | -X 端(底面) | 130 mm |
| `case-lid`  | `top_down` | +X 端(上板の外面) | 9 mm |

bed 寸法 210 × 210 × 205mm に対し本体高 130mm は十分余裕。
```

#### 3.3 サポート(部位別判断)

`generator.py` で生成した形状を解析し、オーバーハングや張り出しを **部位別** に判定:

```markdown
## サポート

### case-body(必要)

| 部位 | 状況 | 推奨対応 |
|---|---|---|
| 蝶番ナックル(+X 端、-Y 側) | 円柱が水平方向に張り出す | ツリーサポート、または short overhang 50° 以下 |
| カラビナタブ(+Y 面、+X 端) | 板状の張り出し | ツリーサポート(タブ下面のみ) |
| カラビナタブ穴(φ6mm) | 印刷時水平向き、上半分はブリッジング | サポート不要(PLA で問題なし) |
| ラッチ突起(+Y 面の球形 bump) | 0.6mm 突出、半球 | サポート不要(極小) |
| body_text emboss(+Z 面) | 0.6mm 盛り上げ、印刷終盤 | サポート不要 |

**推奨設定**:
- ツリーサポート(またはオーガニックサポート)
- オーバーハング閾値: 50°
- サポート Z 距離: 0.2mm(剥がしやすさ重視)

### case-lid(原則不要)

| 部位 | 状況 | 推奨対応 |
|---|---|---|
| 上板(bed 接地面) | 平坦面が bed に密着 | サポート不要 |
| 嵌合リップ(柱状、上方) | 直立、面取り済み | サポート不要 |
```

#### 3.4 印刷設定(材料カタログから自動生成)

`materials.slicer_recommendations(mid)` の結果をテーブルに展開する。例(`default_material: pla` のとき):

```markdown
## 印刷設定(PLA)

| 項目 | 推奨値 | 範囲 |
|---|---|---|
| ノズル温度 | 205℃(初層 210℃) | 190-220 |
| ベッド温度 | 55℃(初層 60℃) | 50-60 |
| 層高 | 0.20 mm | 0.12-0.28 |
| 初層高 | 0.24 mm | — |
| 壁周回数 | 3(0.4 ノズル × 3 = 1.2 mm 壁厚) | 設定値 |
| インフィル密度 | 22%(屋外・ハードユース時 40%) | 15-30 |
| インフィルパターン | gyroid または cubic | — |
| 印刷速度 | 60 mm/s(壁・トップ層 30 mm/s) | 40-80 |
| ファン | 100%(初層 0%) | — |
| Brim / Skirt | 蓋は brim 5mm 推奨(接地面が小さい場合) | — |
| サポート除去難度 | low | — |
```

**他材料の例**: 利用者が `default_material: petg` に切り替えると、temperatures = 235°C / 78°C、層高範囲 0.16-0.28 等に自動更新される。

`warnings` がある場合は本セクションの末尾に箇条書きで併記する:

```markdown
### 注意点(materials カタログ由来)

- 線収縮率 0.6%、反り対策(brim 5mm 以上 / 接地面拡大)推奨
- ABS は密閉チャンバー推奨(反り抑制・層間接着安定)
```

#### 3.5 後処理

```markdown
## 後処理

### 必須
1. **蝶番ピン挿入**(蝶番がある場合): M2 釘または φ2.0mm 真鍮線/ステンレス線

### 嵌合がきつい場合(やすりで対処しない)

蓋がきつい・閉まらない場合、**実物でやすり調整に逃げず CAD で解決する**:
- 全周一律にきつい → `case-config.yaml` の `lid.fit_clearance` を 0.3 以上に上げて `generator.py` を再生成
- 蝶番側だけ擦る → `lip_hinge_side_extra_clearance` を導入(P14 参照)
- 蝶番ナックルが本体壁と干渉 → `hinge.body_relief_clearance` を設定(P13 参照)
- いずれも `/fit-check` で根本原因を点検してから `/review-fix` で対応

CAD で解決する原則を守ることで、利用者間で再現性が保たれる。

### CAD 上の意図的な重なり(あれば明示)

`fit_check.py` の `ALLOWLIST` に登録された **意図的な微小重なり** があれば、その内容と理由をここに転記:
- 例:「蝶番ナックル付近で 35.6 mm³ の許容重なり(label / max_mm3 / 理由は ALLOWLIST 参照)」
- ALLOWLIST に登録されていない重なりは**設計の不完全性**を示す。出荷前に解消する

### 動作確認チェックリスト
1. 蝶番にピン挿入 → スムーズに回転するか
2. 蓋を閉じる → 嵌合リップが本体内寸に収まり、ラッチが「カチッ」と入るか
3. ラッチ強度 → 蓋が自重・軽い揺れで開かないこと
4. カラビナ通し → 穴に金具が通ること、タブの強度
```

#### 3.6 トラブルシューティング表

実物で問題が出た場合、`case-config.yaml` のどのパラメータを調整するかを表形式で案内:

```markdown
## トラブルシューティング

| 症状 | 原因候補 | 対処 |
|---|---|---|
| 蓋が硬すぎる | fit_clearance 不足 | `case-config.yaml` の `lid.fit_clearance` を 0.3 に上げて再生成 |
| 蓋がゆるい | fit_clearance 過多 | 0.15 に下げる |
| ラッチが効かない | bump_protrusion 不足 | `catch.bump_protrusion` を 0.8 に増やす |
| ラッチが堅すぎる | bump_protrusion 過多 | 0.4 に下げる |
| 蝶番が固い | knuckle_clearance_z 不足 | `hinge.knuckle_clearance_z` を 0.6 に増やす |
| 蝶番がガタつく | knuckle_clearance_z 過多 | 0.2 に下げる |
| 文字 emboss が潰れる | 層高が大きい | スライサーで層高 0.16mm 以下に |

調整後は `python output/design/generator.py` で再生成 → `output/print/` の 3MF/STL が更新される。
```

**重要**: トラブルシューティング表は**プロジェクトに応じて項目を追加**する。features ごとに想定される失敗モードと対処を Claude が案内する。

### Step 4: 利用者に提示

```
✓ 最終プリント用ファイルを出力しました:
  - output/print/case-body.stl / .3mf
  - output/print/case-lid.stl  / .3mf
  - output/print/latch-lever.stl / .3mf  (closure=hinge_lever のときのみ)
  - output/print/slicer-notes.md(スライサー設定推奨)

次のステップ:
  1. お使いのスライサー(3MF 対応推奨)で .3mf を開く
  2. slicer-notes.md の推奨設定を反映
  3. プリント開始

試作プリント後、不満があれば段階 1〜4 に戻って詰めてください
(README「ワークフローのリズム感」を参照)
```

## ゲート

段階 5 完了条件:

- `output/print/` に STL / 3MF が出力済み
- `output/print/slicer-notes.md` が生成済み
- 利用者にスライサー起動が案内されている

## 注意事項

- **3MF の優位性**: 3MF は印刷向きをファイルに埋め込めるため、3MF 対応スライサーではこちらが推奨
- **STL は予備**: 互換性のため両方出力
- **試作前提**: プリント後に「合わない」「干渉する」が見つかったら、段階 1 か 4 に戻ってループ(constitution §4)
- **stl/3mf は git ignore**: `.gitignore`(setup.sh で展開済み)で `output/print/*.stl` `*.3mf` を除外している。バイナリ派生物は履歴に残さない
- **slicer-notes.md は追跡対象**: テキストなので git に残し、利用者の設定判断のトレーサビリティを確保

## 関連

- `@.claude/skills/review-fix/SKILL.md` — 段階 4、設計確定の前段階
- `@.claude/skills/fit-check/SKILL.md` — 段階 4-5 橋渡し、❌ なしを確認してから export
- `@.claude/skills/hinged-lid/SKILL.md` — closure=hinge_lever のとき、本 skill が出力する 3 部品目(レバー)の責任元
- `@.claude/agents/slicer-advisor.md` — Step 3 で委譲できるサブエージェント
- `@.claude/rules/materials-catalog.md` — `slicer_recommendations` の元データ
- `src/case_blueprint/materials.py` — `slicer_recommendations(material_id)` ヘルパ
- `@.gitignore` — output/print/ のバイナリは追跡しない(setup.sh で .gitignore.template から展開済み)
