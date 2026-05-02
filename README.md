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

## ワークフロー 5 段階 + 司会

5 段階の設計ワークフローと、それを束ねる対話オーケストレータ `/concierge` で構成。

| # | 段階 | skill | 主体 | 入出力 |
|---|---|---|---|---|
| - | 司会 | `/concierge` | Claude(対話) | 状態判定 + 次の一手を AskUserQuestion で提示 |
| 1 | オブジェクト入力 | `/measure` | 人間(対話) | → `input/objects/<id>.yaml` |
| 2 | 要件統合 | `/design` | Claude(初稿)+ 人間補正 | → `input/requirements/case-spec.yaml` |
| 3 | 設計生成 | `/design` | Claude | → `output/design/{generator.py, validator.py}` |
| 4 | 可視化レビュー | `/review-fix` | Claude → 人間 → Claude(ループ) | → `output/preview/*.step` `*.stl` |
| 4-5 | 嵌合・干渉点検 | `/fit-check` | Claude | → `output/reports/fit-check.md` |
| 5 | プリント出力 | `/export` | Claude | → `output/print/*.stl` `*.3mf` |

`/concierge` で対話を始めるか、各 skill を直接呼ぶか、どちらでも可。
詳細は [`constitution.md`](constitution.md) の原則 4 を参照。

---

## ワークフローのリズム感

このワークフローは **「完璧な初回提案」を目指しません**。Claude と人間が反復的に詰めていく前提です:

1. **初回(`/measure` → `/design`)**: Claude が input から **約 50%** の合理的な初稿
2. **段階 4(`/review-fix`)**: 利用者が Fusion で確認 → feedback で **約 80%**
3. **試作プリント(`/export`)**: 実物を手に取って評価
4. **さらに反復**: 段階 1 に戻るか、段階 4 を繰り返す

「ポン出し」で完成するシステムではありません。**設計を育てる** ためのプロセスです(constitution §4 の 5 段階ゲートはこの反復を想定)。

---

## フィードバックループ — 実プロジェクトをテンプレートに還元

実際に作ったプロジェクトの学びをテンプレートに還元する仕組みがあります:

```
[my-gps-logger-case/]               ← setup.sh で生成した実プロジェクト
       ↓ 丸ごとコピー
[case-blueprints/feedback-staging/gps-logger-case/]   ← Git 追跡外、個人情報 OK
       ↓ Claude が分析
[case-blueprints/case-blueprint/]   ← skill / テンプレートを改善
[case-blueprints/examples/gps-logger-case/]   ← 学びを整形して保存
```

詳細は [`feedback-staging/README.md`](feedback-staging/README.md) を参照。

---

## ディレクトリの歩き方

| ディレクトリ | 役割 | コピー対象? |
|---|---|---|
| `case-blueprint/` | **テンプレート本体**。setup.sh で利用者プロジェクトに展開される | ✅ |
| `docs/` | 思想・スキーマ解説(リポ専用の読み物) | ❌ |
| `examples/` | このテンプレートで作ったケースの完成例ショーケース(整形済み) | ❌ |
| `snippets/` | 将来のレシピ集(空) | ❌ |
| `feedback-staging/` | 実プロジェクトのフィードバック投入領域(Git 追跡外) | ❌ |

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
