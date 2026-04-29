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

`output/print/slicer-notes.md` に以下を記述:

#### 3.1 印刷向き

`case-spec.yaml` の `print_orientation` から各パーツの向きを記述:

```markdown
## 印刷向き
- **case-body.stl**: 底面を Z=0(底を下、`bottom_down`)
- **case-lid.stl**: 天面を Z=0(天を下、`top_down`)。フタの内側がベッドに接する
```

#### 3.2 サポート

- `generator.py` で生成した形状を解析し、オーバーハング部位を検出
- 一般的な閾値(45° 以上)を超える箇所があるか
- 結果例:

```markdown
## サポート
- 不要(主要なオーバーハングなし)
```

または:

```markdown
## サポート
- 必要(ヒンジ部の張り出し、カラビナ穴の上端)
- 推奨設定: ツリーサポート、サポート角度 45°
```

#### 3.3 インフィル

```markdown
## インフィル
- 推奨: 20%(一般用途)
- 屋外・耐衝撃用途: 40-60%
```

#### 3.4 印刷温度

`project-config.yaml` の `default_material` から推測:

```markdown
## 印刷温度(PLA の場合)
- ノズル: 210℃
- ベッド: 60℃
```

PETG / ABS / TPU の場合の値を併記。

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
