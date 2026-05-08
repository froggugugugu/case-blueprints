# Constitution — 不変原則(Inviolable Principles)

このファイルは `case-blueprints` リポジトリの**変えてはいけない 5 原則**を定義する。
個別ドキュメント(`README.md`, `CLAUDE.md`, `case-blueprint/` 配下の設定)の上位に位置する。

> 変更が必要な場合は、PR で明示的に議論し、レビューで合意してからマージする。
> AI が単独で書き換えることは禁止。変更プロトコルは末尾を参照。

---

## 1. 人間と AI の責務分離(ハイブリッドゾーンを明示)

`case-blueprint/input/` は人間管理、`case-blueprint/output/` は AI 管理。
この境界を曖昧にしない。

- **人間管理**: `input/objects/`, `input/design-params/`, `input/feedback/`、および本ファイル
- **AI 管理**: `output/design/`, `output/preview/`, `output/print/`, `output/reports/`
- **ハイブリッドゾーン**: `input/requirements/case-spec.yaml` は **Claude が初稿を生成し、人間が補正できる** 例外。
  「Claude が書いたが、人間が編集権限を持つ」という第 3 ゾーンとして明示的に許容する。

---

## 2. テキスト中心とソース・オブ・トゥルース

設計の真実は **CadQuery(Python)+ YAML(テキスト)** である。

- ソース・オブ・トゥルース: `output/design/generator.py` と `input/design-params/case-config.yaml`
- バイナリ派生物: `output/preview/*.step` `*.stl`、`output/print/*.stl` `*.3mf`
- バイナリを直接編集して上流に逆流させてはならない(GUI で形をいじって CadQuery に戻す道は閉じる)
- 人間が形を修正したいときは、YAML の数値を変えるか、`input/feedback/` に文章で書く

この原則により、Git 差分が読める / Claude が変更を意味として理解できる / Fusion 等の独自フォーマット依存を避けられる。

---

## 3. L2 ワークフロー — Python 読解を前提にしない

利用者は CadQuery / Python のコードを読めなくてもワークフローを回せる。

- **寸法・選択肢の変更**: `input/design-params/case-config.yaml` の値を直接編集
- **構造変更や曖昧な要望**: `input/feedback/<date>.md` に自然言語で記述 → Claude が CadQuery を更新
- 人間が触る編集対象は `input/` 4 ディレクトリ(`objects/`, `requirements/`, `design-params/`, `feedback/`)に**完全に集約**する
- skill 設計はこの前提を崩さない。「人間に Python を書かせる」を前提にする skill は作らない

---

## 4. 5 段階ワークフローのゲートを削減しない

ワークフローには 5 つの段階がある:

1. **オブジェクト入力**(人間 → `input/objects/`)
2. **要件統合**(Claude → `input/requirements/case-spec.yaml`、人間補正可)
3. **設計生成**(Claude → `output/design/`)
4. **可視化レビュー**(Claude → 人間 → Claude のループ)
5. **プリント出力**(Claude → `output/print/`)

段階 4 と 5 の橋渡しとして `/fit-check` skill(嵌合・干渉点検)が存在し、これも必要なゲートを構成する。
全段階を束ねるプロジェクトリード(PdM 相当)として `/lead` skill が存在するが、各段階の責務を侵さない。

各段階の境界は人間の介入機会として残す。介入は任意だが、**ゲートそのものを削ってはならない**。
段階を統合・スキップして「全自動化」する変更は禁止。

---

## 5. テンプレートとリポ固有資料の境界を守る

`case-blueprints` リポジトリは **テンプレートを生成するためのプロジェクト**である。

- **コピー対象(テンプレート本体)**: `case-blueprint/` 配下のみ。`setup.sh` で利用者プロジェクトに展開される
- **コピー対象外(リポ専用の読み物)**: `README.md`, `CLAUDE.md`, `constitution.md`, `docs/`, `examples/`, `snippets/`
- 利用者プロジェクト固有の判断(プリンタ機種、材料、特定ケースの寸法)を `case-blueprint/` 配下に書き込んではならない
- 逆に、テンプレート利用に必要なファイルを `docs/` 等のコピー対象外領域に置いてはならない

この境界が崩れると、setup.sh の挙動が予測不能になり、利用者プロジェクトと本リポの責務が曖昧になる。

---

## 変更プロトコル

1. 本ファイルの変更を提案する PR を作成
2. PR 内で変更理由・影響範囲・関連ドキュメントへの波及を明示
3. レビューで合意 → マージ

将来 hooks を導入した場合、本ファイルの sha256 hash 監視を追加する余地はあるが、現時点では運用ルールとレビューに依拠する。

---

## 関連ドキュメント

- `@README.md` — リポジトリの目的・使い方
- `@CLAUDE.md` — 開発ガイド(横断ルール、200 行以内)
- `@case-blueprint/README.md` — テンプレート本体の利用ガイド(コピー先で読まれる)

## 将来予約

- 英語版 constitution(`constitution-en.md`)は当面作成しない。本セッションで「英語版は後回し」と合意済み
- hooks / scan-harness / sha256 監視は規模が必要になった段階で再検討
