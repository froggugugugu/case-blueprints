# 実測フィードバック様式 — 物理ループの規約

CAD 上の `/fit-check`(段階 4-5)が **干渉/クリアランスの「設計上の」検査**であるのに対し、
本ファイルは **試作後の「物理的な」検査**を Claude に取り込むための様式を定義する。

`/fit-check` までの全チェックを通過した STL を印刷し、ノギスで実測し、CAD と差分を取り、
次のイテレーションで CAD を補正する — これが本リポが想定する **物理ループ**である。

## ファイル配置

```text
.claude/templates/feedback-measurements.yaml   ← 雛形(編集禁止)
input/feedback/
  ├─ 2026-05-08-measurements.yaml              ← イテレーション 1 の実測
  ├─ 2026-05-08-notes.md                       ← 自由記述フィードバック(従来通り)
  └─ 2026-05-15-measurements.yaml              ← イテレーション 2
```

## 起動シナリオ

利用者が試作を印刷し、計測を始める時:

1. `cp .claude/templates/feedback-measurements.yaml input/feedback/$(date +%Y-%m-%d)-measurements.yaml`
   - skill から呼ぶ場合は `/review-fix measurements` で自動コピー(SKILL.md 参照)
2. 利用者がノギスで本体・蓋・嵌合を測り、yaml を埋める
3. `/review-fix` を呼ぶと Claude が `adjustments_applied` を `case-config.yaml` に反映 → `generator.py` 再実行

## yaml の主要セクション

| キー | 役割 |
|---|---|
| `iteration` | この本体に対する試作回数(1, 2, 3, ...) |
| `print_id` | 本体識別。同じ本体を再使用する間は不変(P15) |
| `material` | `data/materials/<id>` の id。validators が引いて推奨範囲を出す |
| `measurements[]` | 1 行 1 測定。`action` は `ok` / `loose` / `tight` / `interfere` / `gap` |
| `adjustments_applied[]` | 採用する補正。`requires_body_reprint` が true のものは P15 で要警戒 |
| `unresolved[]` | 解消できなかった問題。次イテレーションに持ち越す候補 |
| `allowlist_changes` | `fit_check.py` の ALLOWLIST 追加・削除履歴(P16) |

## `action` の取り得る値

| 値 | 意味 | 典型的な対処 |
|---|---|---|
| `ok` | 範囲内 / 許容内 | adjustments 不要 |
| `tight` | 嵌合が固い / 入りづらい | fit_clearance を +0.05 |
| `loose` | 嵌合が緩い / 抜けやすい | fit_clearance を −0.05 |
| `interfere` | 完全干渉(物理的に組めない) | 構造変更 / 蓋寸法 / リリーフカット見直し |
| `gap` | 合わせ面に隙間ができる | 蓋寸法 / fit_clearance / 印刷向き見直し |

## 原則

### 「本体不変」原則(P15)

`requires_body_reprint: true` が必要な変更は警戒する。本体は印刷時間が長く、
再印刷は最後の手段。可能な限り **蓋側で吸収できるパラメータ** を選ぶ:

- ✅ 蓋側のみ: `lid.fit_clearance`(蓋を縮めて吸収)、`lid.lip_height`、`lid_knuckle_extra_clearance_z`
- ⚠ 両側影響: `walls.thickness`、`hinge.knuckle.outer_diameter`
- ❌ 本体パラメータ: `internal.*`、本体壁周りの `body_relief_clearance`、`hinge.geometry.*`

### 「明示許容」原則(P16)

実物で削って合わせた、やすりで成形した — などの **暗黙許容を action に書かない**。
そういう状況になった場合は次のいずれかを取る:

1. CAD 側でその箇所を直す → `adjustments_applied` に書く
2. CAD 解消が困難 → `fit_check.py` の `ALLOWLIST` に label / max_mm³ / 理由を登録 → `allowlist_changes` に履歴

## /review-fix が yaml を読むとき

1. `measurements[]` の各行の `action` から、対応する `case-config.yaml` キーを推論
2. `adjustments_applied[]` がある場合はそれを採用、無い場合は推論結果を**提案して同意を取る**
3. `case-config.yaml` を編集 → `python output/design/generator.py` を再実行
4. `validator.py` を再実行 → `output/reports/validation.md` を更新
5. `iteration` をインクリメントして次の試作へ

## 関連

- `@.claude/templates/feedback-measurements.yaml` — 雛形
- `@.claude/skills/review-fix/SKILL.md` — `/review-fix measurements` モード
- `@.claude/skills/fit-check/SKILL.md` — CAD 側の検査(物理ループの前段)
- `@.claude/pitfalls.md` — P5 / P15 / P16
- `@.claude/rules/materials-catalog.md` — 材料別の fit_clearance 推奨範囲
