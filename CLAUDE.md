# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`case-blueprints` は、3D プリント可能なケース設計のための **テンプレートを生成するプロジェクト**。
本ファイルは**リポ保守者向け**のガイドであり、テンプレート利用者(`setup.sh` でコピーした先のプロジェクト)向けではない。

ドキュメントとコメントは**日本語**で書く。Claude Code の応答も**日本語**。
英語版は将来予約(本リポでは作らない)。

## Repository Structure

```text
case-blueprints/
├── README.md / LICENSE / CHANGELOG.md   # リポトップの読み物(リポ保守者・利用検討者向け)
├── CLAUDE.md                             # 本ファイル
├── constitution.md                       # 5 不変原則(変更プロトコル付き)
├── case-blueprint/                       # ★ テンプレート本体(setup.sh コピー対象)
│   ├── README.md / setup.sh
│   ├── CLAUDE.md.template / project-config.yaml.template / pyproject.toml.template / .gitignore.template
│   ├── input/{objects, requirements, design-params, feedback}/
│   ├── output/{design, preview, print, reports}/
│   ├── examples/{minimal/}                    # テンプレート同梱の動く参照例(コピーされる)
│   ├── schemas/  — JSON-Schema(object / case-spec / case-config / project-config / material)
│   ├── src/case_blueprint/{loader,geometry,exporter,feature_registry,validators,materials,fit_check,state,cli,closures/,features/,data/materials/}
│   ├── tests/  — pytest smoke
│   └── .claude/
│       ├── settings.json.template      — permissions + hooks
│       ├── skills/{lead, measure, design, review-fix, fit-check, export, hinged-lid, style}/
│       ├── agents/{cad-validator, slicer-advisor}.md
│       ├── rules/{constitution, cad-conventions, yaml-style, print-safety, closures-catalog, features-catalog, hardware-catalog, materials-catalog, measurement-feedback, print-orientation-reasoning, report-style}.md
│       ├── hooks/{session-start, post-edit-validate, stop-gate, ...}.sh
│       ├── templates/feedback-measurements.yaml  — 物理ループ雛形
│       ├── pitfalls.md
│       └── quality-gates.md
├── docs/{philosophy, schemas}/           # 思想・解説(リポ専用、コピー対象外)
├── examples/                             # 完成例ショーケース(リポ専用)
├── snippets/                             # レシピ集(将来予約、空)
└── example-for-delete/                   # 参考用、最終削除予定(本ファイル末尾参照)
```

詳細は `README.md` のディレクトリ歩き方表を参照。

## Key Design Decisions

`constitution.md` の 5 原則を運用に落とすと:

- **責務分離**(§1): `case-blueprint/input/` は人間管理、`output/` は AI 管理。例外は `input/requirements/case-spec.yaml`(Claude 初稿+人間補正のハイブリッド)
- **テキスト中心**(§2): ソース・オブ・トゥルースは CadQuery (Python) + YAML。バイナリ(STEP/STL/3MF)は派生物で、逆流させない
- **L2 ワークフロー**(§3): 利用者は Python を読まずに使える前提で設計する。skill が「人間に Python を書かせる」前提を取らないこと
- **5 段階ゲート**(§4): 採寸 → 要件統合 → 設計生成 → 可視化レビュー → プリント出力。skill は `case-blueprint/.claude/skills/{measure, design, review-fix, fit-check, export}` の 5 つでカバー、加えて進行管理の `lead`(PdM 相当)、横断スキル `hinged-lid`(機構特化)/ `style`(意匠)を含めて計 8 つ
- **テンプレート境界**(§5): `case-blueprint/` 配下のみコピー対象。リポ専用リソース(`docs/`, `examples/`, `snippets/`)とテンプレート本体を混ぜない

## Build / Test / Lint

現時点では**ビルド・テスト・lint コマンドはなし**(構造のみのスケルトン)。

将来:
- `case-blueprint/` 配下に `pyproject.toml.template` を置き、利用者プロジェクトで `pytest` / `ruff` を実行できるようにする
- 本リポ自体には CI を入れない方針(サンプル集の規模)。必要なら `case-blueprint/` 配下の YAML スキーマ検証のみに絞る

## Editing Guidelines

### `constitution.md`
- 単独で書き換えない。変更プロトコル(`constitution.md` 末尾)に従う
- 5 原則の数を増減させる変更は特に慎重に。PR で明示的に議論する

### `case-blueprint/` 配下(コピー対象)
- 「**コピー先で動く**」前提で書く。リポトップへの絶対パス参照は禁止
- 自己参照は `./` または相対パスで書く
- 利用者プロジェクト固有の判断(プリンタ機種、材料、特定ケースの寸法)を埋め込まない — それは `project-config.yaml.template` のサンプル値や `input/objects/` の例として隔離する
- `.template` 拡張子付きファイルは `setup.sh` で展開時に拡張子を取って配置する想定

### `case-blueprint/.claude/skills/`
- 新規 skill 追加時は既存の構造に揃える(frontmatter + 「目的」「入出力」「手順」「ゲート」)
- skill 数は最小に保つ(現在 8: lead / measure / design / review-fix / fit-check / export / hinged-lid / style)。安易に増やさない
- 5 段階ワークフローのいずれかに対応する、または明確に補完する skill のみ追加。横断スキル(`hinged-lid` 機構特化 / `style` 意匠)は段階に属さず、各々の責務(closure 詳細 / 美的方針)を埋める用途に限定する

### リポトップの `docs/`, `examples/`, `snippets/`(コピー対象外)
- ここに置いたファイルは利用者プロジェクトにはコピーされない
- 利用者が必要とするドキュメントは `case-blueprint/README.md` か `case-blueprint/.claude/` 配下に置く
- **`case-blueprint/examples/` とは別物**。後者はテンプレート同梱の動く参照例で、`setup.sh` でコピーされる

### CLAUDE.md(本ファイル)のサイズ管理
- **目安**: 200 行以内
- **ハード上限**: 220 行(超過したら次回の編集で必ず切り出し)
- **切り出し先**: `case-blueprint/.claude/rules/<topic>.md`(将来) または `docs/<topic>.md`

## Migration: `example-for-delete/`

このリポジトリには `example-for-delete/` ディレクトリがあり、以下を含む:

- `project-blueprints/` — `froggugugugu/project-blueprints` のクローン(参考用)
- `case-blueprints-handoff/` — Claude.ai セッションからの引継ぎ資料一式
- `case-blueprints-handoff.tar.gz` — 同上の元アーカイブ

**このディレクトリは最終的に削除する。Git 履歴には残さない**(`.gitignore` で除外済み)。

- 削除タイミング: テンプレート本体(`case-blueprint/`)が最低限動くようになり、引継ぎ資料の意図がリポ内ドキュメントに織り込まれた段階
- 削除方法: 物理削除のみ(`rm -rf example-for-delete/`)。Git 履歴には現れない
- `example-for-delete/` 配下のファイルを `case-blueprint/` や `docs/` に**コピー**するのではなく、**意図を抽出して再構成**する(decisions.md D3 の精神に沿う)

## Language

- このリポジトリのドキュメントは**日本語**で書く
- Claude Code の応答も**日本語**
- 例外: 機械可読ファイル(YAML キー、Python 識別子)は英語

## 関連ドキュメント

- `@constitution.md` — 5 不変原則
- `@README.md` — リポジトリの目的・使い方(利用検討者向け)
- `@case-blueprint/README.md` — テンプレート本体の利用ガイド(コピー先で読まれる、構築中)
- `@docs/` — 思想・スキーマ解説(構築中)
