# my-case-project

> **case-blueprints テンプレート**から生成された 3D プリント可能なケース設計プロジェクトです。
> Claude が主導し、あなた(人間)は YAML を書くか自然言語でフィードバックするだけで設計が進みます。

🚧 **構築中**: テンプレート機能は順次拡充されます。

---

## はじめに

このディレクトリは [`case-blueprints`](https://github.com/froggugugugu/case-blueprints) の `setup.sh` で生成されました。
人間と Claude が共存して 3D プリント可能なケースを設計するためのワークスペースです。

---

## ワークフロー 5 段階

| # | 段階 | 主体 | 入出力 |
|---|---|---|---|
| 1 | オブジェクト入力 | 人間(対話) | → `input/objects/<name>.yaml` |
| 2 | 要件統合 | Claude(初稿)+ 人間補正 | → `input/requirements/case-spec.yaml` |
| 3 | 設計生成 | Claude | → `output/design/{generator.py, validator.py}` |
| 4 | 可視化レビュー | Claude → 人間 → Claude(ループ) | → `output/preview/*.step` `*.stl` |
| 5 | プリント出力 | Claude | → `output/print/*.stl` `*.3mf` |

---

## セットアップ

### 1. プロジェクト設定の編集

最初に `project-config.yaml` を開き、プリンタ機種・材料・設計ルールを記入してください:

```yaml
print_settings:
  printer_bed: [220, 220, 250]    # ご使用のプリンタの造形領域
  nozzle_diameter: 0.4
  default_material: PLA
```

### 2. Python 環境の準備

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"            # cadquery + pytest + ruff
```

### 3. Git 初期化(推奨)

`/review-fix` skill が `case-config.yaml` の差分を検出するために Git を使います。

```bash
git init
git add .
git commit -m "Initial: case-blueprints テンプレートから生成"
```

`.gitignore` は `setup.sh` で展開済みなので、バイナリ派生物(STEP/STL/3MF)は自動的に除外されます。

### 4. Claude Code 起動

```bash
claude
```

起動後、以下の skill を使用します:

- `/measure` — 段階 1: オブジェクトを対話的に採寸
- `/design` — 段階 2-3: 要件統合と設計生成
- `/review-fix` — 段階 4: フィードバックを反映
- `/export` — 段階 5: 最終 STL/3MF 出力

---

## ファイルとディレクトリ

### あなた(人間)が編集する場所 — すべて `input/` 配下に集約

| ディレクトリ | 段階 | 役割 |
|---|---|---|
| `input/objects/` | 1 | ケースに収納するオブジェクトの採寸記録 |
| `input/requirements/` | 2 | ケース全体への要件(Claude 初稿+補正) |
| `input/design-params/` | 3 | 寸法・選択肢のパラメータ(主要編集対象) |
| `input/feedback/` | 4 | 構造変更や曖昧な要望を日本語で記述 |

### Claude が生成する場所 — すべて `output/` 配下、人間は読むのみ

| ディレクトリ | 段階 | 役割 |
|---|---|---|
| `output/design/` | 3 | CadQuery ソース(generator.py / validator.py) |
| `output/preview/` | 4 | 可視化用 STEP / STL(Fusion 等で開く) |
| `output/print/` | 5 | 最終プリント用 STL / 3MF |
| `output/reports/` | 各段階 | 寸法整合チェック等のレポート |

### その他

- `project-config.yaml` — プリンタ設定など(あなたが編集)
- `pyproject.toml` — Python 依存とツール設定
- `schemas/` — 機械可読 YAML スキーマ
- `src/` — Claude が実装する Python パッケージ
- `tests/` — Claude が書くテスト

---

## L2 ワークフロー — Python を読まずに使えます

寸法を変えたいときは `input/design-params/case-config.yaml` を直接編集:

```yaml
walls:
  thickness: 2.0                 # ← 数値を変えるだけ
lid:
  fit_clearance: 0.3             # ← フタの嵌合をゆるくしたいときも数値だけ
```

構造変更や曖昧な要望は `input/feedback/<date>.md` に日本語で記述:

```markdown
左奥と右手前に M3 ねじ穴を 4 個追加してください。
```

Claude が CadQuery を更新し、設計に反映します。

---

## 関連ドキュメント

- `.claude/skills/` — 各 skill の詳細
- `.claude/pitfalls.md` — 3D プリント特有の落とし穴(構築中)
- `.claude/quality-gates.md` — 5 段階ゲート(構築中)
