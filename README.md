# case-blueprints

> 収納したい機器の **商品ページ URL** や **ノギスでの実測値**、自由記述メモを
> Claude Code に渡すと、3D プリント可能な **ケース設計を生成・反復できる**
> テンプレート。
> 採寸 → 仕様統合 → CadQuery 生成 → 可視化レビュー → 嵌合点検 → 印刷ファイル
> までの 5 段階を、ヒューマンインザループで回す前提で設計されている。

**前提条件**: [Claude Code](https://docs.claude.com/en/docs/claude-code)、Git、Python 3.11+ が `PATH` にインストール済みであること(これらの導入手順は本書の対象外)。

---

## 最短手順 — `/lead` まで

```bash
git clone https://github.com/froggugugugu/case-blueprints.git
bash case-blueprints/case-blueprint/setup.sh ./my-case
cd ./my-case && claude
```

Claude Code 起動後、最初のプロンプトは **2 段階** で投げる想定:

**段階 1.** 環境設定(`project-config.yaml` を Claude に書かせる):

```
私のプリンタは Bambu Lab P1S(造形 256×256×256mm、ノズル 0.4mm)、
材料は PETG をメインに使います。
project-config.yaml を埋めて、Python 環境も用意してください。
```

Claude が `project-config.yaml` を編集し、`pip install -e .` 等の環境構築を
提案 → 承認すれば cadquery 含む依存が入る。

**段階 2.** プロジェクト開始(`/lead` で進行管理 + 対話):

```
/lead
```

`/lead` が現状を把握(input/objects/ が空など)→ 次の一手を提示。
ここで採寸対象の **商品ページ URL** や **実測値**、用途メモを順に貼れば、
`/measure` → `/design` → `/review-fix` … と対話的に進む。

> 動く参照例から始める場合は、`claude` 起動前に
> `cp -R ./my-case/examples/minimal/input/. ./my-case/input/`(snap_fit
> 名刺ケース)または `cp -R ./my-case/examples/bike-navi-mvp/input/. ./my-case/input/`
> (features 7 種の総合例)を実行すると、`/design` から確認できる。

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

## 使い方の流れ — 入力からヒューマンインザループまで

このリポは「ポン出し」ではなく **設計を育てるプロセス** を回すためのものです。
利用者が用意するもの・Claude が生成するもの・人間が補正するものが明確に分離。

```text
[利用者が用意するもの — 何でもよい組み合わせ]
  ├─ 商品ページや公式仕様の URL(寸法・コネクタ・発熱情報の出所として)
  ├─ ノギス等での実測値(URL が無い / 寸法が信用できないとき)
  ├─ 参考になるデザインのイメージ URL(類例の写真・図面)
  └─ 自由記述メモ(用途、運用環境、必須要件)
                    ↓
       /measure — Claude が URL や実測値から 採寸結果を yaml 化
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

入力は「URL だけ」「実測値だけ」「両方」のいずれでも始められます。
URL は寸法情報の出所として便利ですが、商品ページの寸法表記が信用できない
場合は **実測が優先** されます(`/measure` で実測値で上書きする運用)。

進行管理は **`/lead`**(PdM 相当)が現状把握 → 次の一手を提示。L2 利用者は
`/lead` だけ呼べば十分なケースが多い。

詳細は [`case-blueprint/README.md`](case-blueprint/README.md) と
[`case-blueprint/.claude/quality-gates.md`](case-blueprint/.claude/quality-gates.md) を参照。

---

## 段階的に使う

| ステップ | 入力 | 動くようになるもの |
|---|---|---|
| **最小** | 1 オブジェクト + 単純 closure | snap_fit / 名刺ケース相当(参考: examples/minimal/) |
| **典型** | 1-3 オブジェクト + closure 選択 | snap_fit / screws / magnetic / hinge_lever / snap_lip_with_hinge |
| **複合** | features 多用 + 屋外・車載対応 | display_window + cable_port + button_cutout + ventilation 等(参考: examples/bike-navi-mvp/) |
| **3D 配置** | 複数 objects を `position: [x, y, z]` で配置 | `layout.arrangement: manual`、AABB 干渉自動検出 |

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
