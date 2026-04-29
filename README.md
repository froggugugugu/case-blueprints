# case-blueprints

> 3D プリント可能なケース設計を、**人間と Claude が共存**して行うための**テンプレートを生成するプロジェクト**。
> Claude が主導し、人間は YAML を書くか自然言語でフィードバックするだけで設計が進む(L2 ワークフロー)。

🚧 **構築中**: 現在は構造のみ。詳細は構築過程で順次追加します。

---

## 何のためのリポジトリか

`case-blueprints` は、ケースを 1 つ作るたびに**別プロジェクト**を立ち上げるためのテンプレート集です。
本リポは「テンプレートを生成する側」であり、利用者は `case-blueprint/` を `setup.sh` で別プロジェクトにコピーして使います。

```text
[case-blueprints リポジトリ]
       ↓ setup.sh ./my-case-project
[my-case-project/]   ← ここで対話・採寸・モデリング・出力
       ↓
   3D プリンタ
```

---

## ワークフロー 5 段階

| # | 段階 | 主体 | 入出力 |
|---|---|---|---|
| 1 | オブジェクト入力 | 人間(対話) | → `input/objects/<name>.yaml` |
| 2 | 要件統合 | Claude(初稿)+ 人間補正 | → `input/requirements/case-spec.yaml` |
| 3 | 設計生成 | Claude | → `output/design/{generator.py, validator.py}` |
| 4 | 可視化レビュー | Claude → 人間 → Claude(ループ) | → `output/preview/*.step` `*.stl` |
| 5 | プリント出力 | Claude | → `output/print/*.stl` `*.3mf` |

詳細は [`constitution.md`](constitution.md) の原則 4 を参照。

---

## ディレクトリの歩き方

| ディレクトリ | 役割 | コピー対象? |
|---|---|---|
| `case-blueprint/` | **テンプレート本体**。setup.sh で利用者プロジェクトに展開される | ✅ |
| `docs/` | 思想・スキーマ解説(リポ専用の読み物) | ❌ |
| `examples/` | このテンプレートで作ったケースの完成例ショーケース | ❌ |
| `snippets/` | 将来のレシピ集(空) | ❌ |

詳細は各ディレクトリの README を参照。

---

## 設計判断とコンセプト

| トピック | 採用方針 |
|---|---|
| CAD ツール | **CadQuery (Python) + YAML** をソース・オブ・トゥルース。バイナリ(STEP/STL)は派生物 |
| 表示・編集 | Fusion 360 / FreeCAD は **ビューア用途**。GUI 直接編集を CadQuery に逆流させない |
| 制御レベル | **L2**: Python の読解を前提にしない。寸法は YAML、構造変更は自然言語フィードバック |
| 責務分離 | `input/` 人間管理、`output/` AI 管理。例外として `case-spec.yaml` はハイブリッドゾーン |

詳細は [`constitution.md`](constitution.md) および `docs/philosophy/`(構築中)。

---

## 関連ドキュメント

- [`constitution.md`](constitution.md) — 5 不変原則
- [`CLAUDE.md`](CLAUDE.md) — 開発ガイド(リポ保守者向け)
- [`case-blueprint/README.md`](case-blueprint/README.md) — テンプレート本体の利用ガイド(コピー先で読まれる)
- [`docs/`](docs/) — 思想とスキーマ解説(構築中)

---

## ライセンス

未定(後で決定予定)
