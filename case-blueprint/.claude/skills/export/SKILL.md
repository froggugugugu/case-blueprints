---
name: export
description: 段階 5 — 確定済みの設計から最終プリント用 STL/3MF を出力し、スライサー設定の推奨を slicer-notes.md に記述する。
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
| | `output/print/slicer-notes.md` | スライサー設定推奨 |

## 処理フロー

### Step 1: 確定確認

- `/review-fix` skill のゲートが通過しているか確認
- 通過していなければ「先に `/review-fix` で設計を確定してください」と促す

### Step 2: 最終 generator.py 実行

- `python output/design/generator.py` を実行(エクスポート機能を含む形に拡張)
- STL を `output/print/` に出力
- 可能なら 3MF も出力(印刷向きを埋め込める)

### Step 3: スライサー設定の推奨を生成

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

3MF を推奨。Bambu Studio / PrusaSlicer / OrcaSlicer などで開けば配置済み。
STL を使う場合も既に印刷向きに回転済みなので、スライサーで再配置不要。
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

#### 3.4 印刷設定(材料別)

```markdown
## 印刷設定(PLA 推奨)

| 項目 | 推奨値 |
|---|---|
| ノズル温度 | 210℃(初層 215℃) |
| ベッド温度 | 60℃(初層 65℃) |
| 層高 | 0.2mm |
| 初層高 | 0.24mm |
| 壁周回数 | 3(0.4mm ノズル × 3 = 1.2mm 壁厚) |
| インフィル密度 | 20%(屋外・ハードユース時 40%) |
| インフィルパターン | gyroid または cubic |
| 印刷速度 | 50 mm/s(壁・トップ層は 30 mm/s) |
| ファン | 100%(初層 0%) |
| Brim / Skirt | 蓋は brim 5mm 推奨(接地面が小さい場合) |

### PETG の場合
- ノズル: 235℃、ベッド: 80℃、ファン: 30〜50%、速度: 40 mm/s

### ABS の場合
- ノズル: 245℃、ベッド: 100℃、エンクロージャ推奨
```

#### 3.5 後処理

```markdown
## 後処理

### 必須
1. **蝶番ピン挿入**(蝶番がある場合): M2 釘または φ2.0mm 真鍮線/ステンレス線
2. **嵌合のすり合わせ**: 蓋を初回はめる際、リップ縦エッジが擦るかも → 200 番やすりで軽く落とす

### 既知の小さな干渉(印刷後の調整推奨)

generator.py で意図的に作った微小な幾何重なりがあれば明示:
- 例:「蝶番ナックル付近で 35.6 mm³ の重なり(本体ナックル +X 半円 と 蓋上板の -Y 端 1mm 帯)」
- **対処**: 該当箇所を実物でやすり調整。CAD 上の問題ではなく、動作確認後の微調整

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
  - output/print/slicer-notes.md(スライサー設定推奨)

次のステップ:
  1. お使いのスライサー(Bambu Studio / PrusaSlicer / Cura)で .3mf を開く
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

- **3MF の優位性**: 3MF は印刷向きをファイルに埋め込めるため、Bambu Studio / PrusaSlicer ではこちらが推奨
- **STL は予備**: 互換性のため両方出力
- **試作前提**: プリント後に「合わない」「干渉する」が見つかったら、段階 1 か 4 に戻ってループ(constitution §4)
- **stl/3mf は git ignore**: `.gitignore`(setup.sh で展開済み)で `output/print/*.stl` `*.3mf` を除外している。バイナリ派生物は履歴に残さない
- **slicer-notes.md は追跡対象**: テキストなので git に残し、利用者の設定判断のトレーサビリティを確保

## 関連

- `@.claude/skills/review-fix/SKILL.md` — 段階 4、設計確定の前段階
- `@.gitignore` — output/print/ のバイナリは追跡しない(setup.sh で .gitignore.template から展開済み)
