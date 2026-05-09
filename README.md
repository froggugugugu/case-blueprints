# case-blueprints

> Amazon の部材 URL と自由記述メモを Claude に渡すと、3D プリント可能な
> **ケース設計を生成・反復できる** Claude Code 用テンプレート。
> 採寸 → 仕様統合 → CadQuery 生成 → 可視化レビュー → 嵌合点検 → 印刷ファイル
> までの 5 段階を、ヒューマンインザループで回す前提で設計されている。

**前提**: [Claude Code](https://docs.claude.com/en/docs/claude-code) と Python 3.11+ が `PATH` にインストール済みであること。

---

## 5 行で動かす

```bash
git clone https://github.com/froggugugugu/case-blueprints.git
bash case-blueprints/case-blueprint/setup.sh ./my-case
cp -R ./my-case/examples/bike-navi-mvp/input/. ./my-case/input/   # 動く参照例で始める場合
cd ./my-case && python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/claude   # → プロンプトで /lead 等を呼ぶ
```

`bike-navi-mvp` の入力をコピーして始めれば、最初から **features 7 種・PETG・
heat-set + RAM ボール** までセットされた状態で `/design` を呼べます。
ゼロから始める場合は `examples/minimal/`(snap_fit 名刺ケース)推奨。

---

## なぜこれ? — 5 つの差別化要素

| | 強み | 概要 |
|---|---|---|
| 🎯 | **L2 ワークフロー** | 利用者は CadQuery を読まなくていい。寸法は YAML、構造変更は自然言語 |
| 📐 | **5 段階ゲート + 物理ループ** | measure / design / review-fix / fit-check / export の各段階で人間介入。試作後の実測フィードバックも yaml 様式で取り込み |
| 🧩 | **オープン構造の closure / features** | 5 closure × 6 features を `@register` でプラガブル化、新規追加は src/features/ にファイル 1 つ |
| 🛡️ | **20 pitfalls + materials/hardware カタログ** | 屋外・車載・振動・防水まで pitfalls(P1-P20)で言語化。材料別 fit_clearance 推奨範囲を validator が自動チェック |
| 🪶 | **`/lead` で迷わない** | プロジェクトリード skill が状態判定 → 次の一手を提示。L2 利用者はこれだけで進める |

---

## いま入っているもの

```text
 7 skills   /lead, /measure, /design, /review-fix, /fit-check,
            /export, /hinged-lid
 5 closures snap_fit, screws, magnetic, snap_lip_with_hinge, hinge_lever
 6 features ventilation, cable_port, display_window, button_cutout,
            mounting_bracket, body_text
 5 materials pla, pla_plus, petg, abs, tpu (機構別 fit_clearance 推奨範囲付き)
 2 agents   cad-validator, slicer-advisor
20 pitfalls P1-P20(印刷向き / オーバーハング / 嵌合 / 物理ループ /
            本体不変 / 屋外 / 振動 / 熱変形 ほか)
11 rules    constitution / cad-conventions / yaml-style / print-safety /
            closures-catalog / features-catalog / hardware-catalog /
            materials-catalog / measurement-feedback /
            print-orientation-reasoning / report-style
 2 examples examples/minimal/(snap_fit 名刺ケース)
            examples/bike-navi-mvp/(features 7 種、屋外・車載総合参照)
```

---

## 使い方の流れ — 部材 URL からヒューマンインザループまで

このリポは「ポン出し」ではなく **設計を育てるプロセス** を回すためのものです。
利用者が用意するもの・Claude が生成するもの・人間が補正するものが明確に分離。

```text
[利用者が用意するもの]
  ├─ 部材の Amazon / 公式仕様 URL(寸法・コネクタ・発熱情報の出所)
  ├─ デザインのイメージ URL(他のケース写真、参考になる類例)
  └─ 自由記述メモ(用途、運用環境、必須要件)
                    ↓
       /measure — Claude が URL を読み 採寸結果を yaml 化
                  人間は AskUserQuestion で正面・寸法・公差を確認
                    ↓
       /design  — case-spec.yaml(初稿) + generator.py 生成
                  ハイブリッドゾーンで人間が yaml 補正可
                    ↓
[ヒューマンインザループ ↓↑]
       /review-fix — STEP/STL を見て自然言語フィードバック
                     "ここを厚く" "USB を反対側に" "タブを大きく"
                     → case-config.yaml / generator.py を更新 → 再描画
                    ↓
       /fit-check — 嵌合・features 干渉・CAD 干渉を機械的に点検
                    AABB 干渉(D)で位置の被り、ALLOWLIST で明示許容
                    ↓
       /export   — 最終 STL / 3MF + slicer-notes.md 出力
                    ↓
        🖨 試作プリント
                    ↓
       /review-fix measurements — 実測 yaml で物理ループ
                                  本体不変原則(P15)を守って蓋側で吸収
```

進行管理は **`/lead`**(PdM 相当)が現状把握 → 次の一手を提示。L2 利用者は
`/lead` だけ呼べば十分なケースが多い。

詳細は [`case-blueprint/README.md`](case-blueprint/README.md) と
[`case-blueprint/.claude/quality-gates.md`](case-blueprint/.claude/quality-gates.md) を参照。

---

## 段階的に使う

| ステップ | 入力 | 動くようになるもの |
|---|---|---|
| **最小** | examples/minimal/ をコピー | snap_fit 名刺ケース、`/design` から確認 |
| **典型** | `/measure` で 1-3 オブジェクトを採寸 | snap_fit / screws / magnetic / hinge 系の任意 closure |
| **複合** | examples/bike-navi-mvp を参考に features 7 種 | 屋外・車載案件、heat-set + RAM ボール + 防水 |
| **3D 配置** | `case-spec.layout.arrangement: manual` | 複数 objects を [x,y,z] で配置、AABB 干渉自動検出 |

---

## ディレクトリの歩き方

| ディレクトリ | 役割 | コピー対象? |
|---|---|---|
| `case-blueprint/` | **テンプレート本体**。`setup.sh` で利用者プロジェクトに展開される | ✅ |
| `case-blueprint/examples/` | 動く参照例(minimal / bike-navi-mvp)。コピー先で `cp -R` して使う | ✅ |
| `docs/` | 思想・スキーマ解説(リポ保守者・読者向け) | ❌ |
| `examples/`(リポトップ) | 完成例ショーケース(将来予約) | ❌ |
| `feedback-staging/` | 実プロジェクトのフィードバック投入領域(Git 追跡外) | ❌ |

---

## 設計判断とコンセプト

| トピック | 採用方針 |
|---|---|
| CAD ツール | **CadQuery (Python) + YAML** をソース・オブ・トゥルース。バイナリ(STEP/STL)は派生物 |
| 表示・編集 | Fusion 360 / FreeCAD は **ビューア用途**。GUI 直接編集を CadQuery に逆流させない |
| 制御レベル | **L2**: Python の読解を前提にしない。寸法は YAML、構造変更は自然言語フィードバック |
| 責務分離 | `input/` 人間管理、`output/` AI 管理。例外として `case-spec.yaml` はハイブリッドゾーン |

詳細は [`constitution.md`](constitution.md) を参照。

---

## フィードバックループ — 実プロジェクトをテンプレートに還元

実際に作ったプロジェクトの学びをテンプレートに還元する仕組み:

```
[my-real-project/]                                  ← setup.sh で生成した実プロジェクト
       ↓ 丸ごとコピー
[case-blueprints/feedback-staging/<project-name>/]  ← Git 追跡外、個人情報 OK
       ↓ Claude が分析
[case-blueprints/case-blueprint/]                   ← skill / テンプレートを改善
[case-blueprints/case-blueprint/examples/]          ← 学びを整形して保存
```

詳細は [`feedback-staging/README.md`](feedback-staging/README.md) を参照。

---

## 📚 さらに知る

- [`case-blueprint/README.md`](case-blueprint/README.md) — テンプレート本体の利用ガイド
- [`case-blueprint/.claude/skills/`](case-blueprint/.claude/skills/) — 7 skill の SKILL.md
- [`case-blueprint/.claude/pitfalls.md`](case-blueprint/.claude/pitfalls.md) — 20 件の落とし穴(P1-P20)
- [`case-blueprint/.claude/rules/`](case-blueprint/.claude/rules/) — closures / features / materials / hardware カタログ
- [`constitution.md`](constitution.md) — 5 不変原則(変更プロトコル付き)
- [`CLAUDE.md`](CLAUDE.md) — リポ保守者向け開発ガイド

---

## ライセンス

未定(後で決定予定)
