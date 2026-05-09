# my-case-project

> **case-blueprints テンプレート**から生成された 3D プリント可能なケース設計プロジェクトです。
> Claude が主導し、あなた(人間)は YAML を書くか自然言語でフィードバックするだけで設計が進みます。

🚧 **構築中**: テンプレート機能は順次拡充されます。

---

## はじめに

このディレクトリは [`case-blueprints`](https://github.com/froggugugugu/case-blueprints) の `setup.sh` で生成されました。
人間と Claude が共存して 3D プリント可能なケースを設計するためのワークスペースです。

---

## ワークフロー 5 段階 + プロジェクトリード + 機構特化

| # | 段階 | skill | 主体 | 入出力 |
|---|---|---|---|---|
| - | 進行管理 | `/lead` | Claude(対話) | 状態判定 + 次の一手 |
| 1 | オブジェクト入力 | `/measure` | 人間(対話) | → `input/objects/<id>.yaml` |
| 2 | 要件統合 | `/design` | Claude(初稿)+ 人間補正 | → `input/requirements/case-spec.yaml` |
| 3 | 設計生成 | `/design` | Claude | → `output/design/{generator.py, validator.py}` |
| 4 | 可視化レビュー | `/review-fix` | Claude → 人間 → Claude(ループ) | → `output/preview/*.step` `*.stl` |
| 4-5 | 嵌合・干渉点検 | `/fit-check` | Claude | → `output/reports/fit-check.md` |
| 5 | プリント出力 | `/export` | Claude | → `output/print/*.stl` `*.3mf` |
| 横断 | ヒンジ蓋詳細 | `/hinged-lid` | Claude | closure.method = hinge_lever の具体寸法を埋める |

---

## セットアップ — `/lead` まで

最短手順は **`claude` を起動するだけ**。`project-config.yaml` の編集 /
Python venv の作成 / git 初期化はすべて Claude にプロンプトで依頼できます。

```bash
claude
```

起動後、以下の **2 つのプロンプトを順に投げる** だけで `/lead` に到達します。

### プロンプト 1 — 環境構築を Claude に依頼

```
project-config.yaml を埋めて、Python 環境の構築(venv + pip install -e .)と
git 初期化までお願いします。
プリンタは <機種>(造形 <X×Y×Z mm>、ノズル <径> mm)、
材料は <PETG / PLA / PLA+ / ABS / TPU> をメインに使います。
```

例:

```
project-config.yaml を埋めて、Python 環境の構築と git 初期化までお願いします。
プリンタは Bambu Lab P1S(造形 256×256×256mm、ノズル 0.4mm)、
材料は PETG をメインに使います。
```

Claude が `project-config.yaml` を編集 → `venv` 作成 → `pip install -e .`
→ `git init` までを Bash ツール経由で実行(各操作の前に許可プロンプトが
出るので承認)。

### プロンプト 2 — `/lead` でプロジェクト開始

```
/lead
```

`/lead` が現状を把握(input/objects/ が空など)→ 次の一手を提示。
ここで採寸対象の **商品ページ URL** や **ノギス実測値**、用途メモを
順に貼っていけば、`/measure` → `/design` → `/review-fix` … と対話的に進みます。

### (任意)最小サンプルで動作確認

`/measure` を飛ばして `/design` から試したい場合は、`claude` 起動前か
`/lead` を呼ぶ前に examples をコピー:

```bash
cp -R examples/minimal/input/. input/         # snap_fit 名刺ケース
# または
cp -R examples/bike-navi-mvp/input/. input/   # features 7 種の総合例
```

### 利用可能な skill 一覧

- `/lead` — **プロジェクトリード(PdM 相当)**: 状態判定 + 次の一手を提示
- `/measure` — 段階 1: オブジェクトを対話的に採寸
- `/design` — 段階 2-3: 要件統合と設計生成
- `/review-fix` — 段階 4: フィードバックを反映
- `/fit-check` — 段階 4-5 橋渡し: 嵌合・干渉の点検
- `/export` — 段階 5: 最終 STL/3MF 出力
- `/hinged-lid` — **横断(機構特化)**: ヒンジ蓋ケースの closure 詳細を埋める
- `/style` — **横断(意匠)**: 意匠テーマ(futuristic / minimal / fancy 等)+ 表面パターン + 角の処理を `case-config.yaml` の `style:` セクションに翻訳

> 💡 **GitHub にプッシュする場合**: GitHub UI でリポジトリを作るときは
> 「Add a license」のみ選び、「Initialize with a README」「.gitignore 追加」は
> **選ばない**(`setup.sh` が用意済みのため)。先にローカルで作業して
> `git remote add` で push する手順なら制約なし。

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
| `output/preview/` | 4 | 可視化用 STEP / STL(任意の STEP/STL ビューアで開く) |
| `output/print/` | 5 | 最終プリント用 STL / 3MF |
| `output/reports/` | 各段階 | 寸法整合チェック等のレポート |

### その他

- `project-config.yaml` — プリンタ設定など(あなたが編集)
- `pyproject.toml` — Python 依存とツール設定
- `CLAUDE.md` — Claude Code 起動時に自動ロードされるガイド(`@` import で関連ドキュメント連結)
- `schemas/` — 機械可読 YAML スキーマ(JSON-Schema 2020-12)
- `src/case_blueprint/` — 共通実装(loader / geometry / validators / fit_check / feature_registry / materials / style / state / closures/ / features/ / silhouettes/ / data/materials/)
- `input/fonts/` — サードパーティフォント(`body_text` feature 等で使用、利用者がローカルに配置)
- `examples/` — 動く参照例(minimal / bike-navi-mvp)
- `tests/` — pytest による smoke test
- `.claude/`:
  - `settings.json` — permissions + hooks(自動ゲート執行)
  - `skills/` — 8 つの skill 定義(lead / measure / design / review-fix / fit-check / export / hinged-lid / style)
  - `agents/` — サブエージェント(cad-validator, slicer-advisor)
  - `rules/` — path-scoped ルール 11 種(constitution / cad-conventions / yaml-style / print-safety / closures-catalog / features-catalog / hardware-catalog / materials-catalog / measurement-feedback / print-orientation-reasoning / report-style)
  - `hooks/` — SessionStart / PostToolUse / Stop の自動執行スクリプト
  - `templates/` — 物理ループ用 yaml 雛形
  - `pitfalls.md` — 20 項の落とし穴(P1-P20)
  - `quality-gates.md` — 5 段階ゲート + 横断スキル

---

## サードパーティ素材(フォント等)の取り扱い

`body_text` のような features でフォントを使う場合、以下のルールに従ってください:

### 1. ライセンスファイルを併置

`input/fonts/` にフォントを置くときは、必ずライセンス情報を併置:

```
input/fonts/
├── LICENSE-<font-name>.txt      # フォントのライセンス本文(必須、追跡対象)
└── <font-name>.ttf              # フォント本体(配布可否は要確認)
```

### 2. 配布禁止フォントは Git 追跡しない

多くの商用・無料フォントは **再配布禁止**。`.gitignore` でフォント本体を除外し、ライセンスファイルのみ追跡:

```
# .gitignore に追加
input/fonts/*.ttf
input/fonts/*.otf
input/fonts/*.woff
input/fonts/*.woff2
```

利用者には「フォント本体を個別にダウンロードして `input/fonts/` に配置してください」と案内。

### 3. フォント不在時のハンドリング

`body_text` feature の実装(`src/case_blueprint/features/body_text.py`)が
`validate_body_text()` でフォントの存在を検査します。フォント不在時は
AssertionError で利用者に分かりやすく案内:

```python
# src/case_blueprint/features/body_text.py(抜粋)
fdir = font_dir or feature.get("font_dir", "input/fonts")
fpath = Path(fdir) / feature["font_file"]
if not fpath.exists():
    raise AssertionError(
        f"body_text: フォント {fpath} が見つかりません。"
        f"input/fonts/ にダウンロードして配置してください"
    )
```

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
