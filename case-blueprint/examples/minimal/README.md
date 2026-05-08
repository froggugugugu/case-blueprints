# minimal — 名刺ケース最小サンプル

snap_fit closure の **2 部品ケース** 1 件。`/measure` を飛ばして `/design` から
試せる、テンプレートの **動く参照例** です。

## 構成

| ファイル | 用途 |
|---|---|
| `input/objects/business-cards.yaml` | 91 × 55 × 10mm の名刺束 1 オブジェクト |
| `input/requirements/case-spec.yaml` | `closure.method = snap_fit` / `lid_axis = +Z` |
| `input/design-params/case-config.yaml` | 壁 2.4mm、fit_clearance 0.25mm(PLA 標準) |

## 使い方

プロジェクトルートで以下を実行(`setup.sh` 展開直後の状態を想定):

```bash
cp -R examples/minimal/input/. input/
```

その後 Claude Code を起動して:

```
/design        # case-spec / case-config が既にあるので generator.py 生成へ直行
/review-fix    # 必要なら数値調整
/export        # 印刷ファイルに書き出す
```

## 想定される結果

- 外寸 約 100 × 64 × 16mm(printer_bed 220 × 220 × 250 に十分余裕)
- PLA 推奨、印刷時間 1-2 時間程度
- 蓋は snap_fit、後処理ほぼ不要

## なぜ最小サンプルが同梱されているか

テンプレートは「思想とルールの密度」が高く、最初の利用者は **「どこから手を
付ければ preview が出るか」** を掴みにくい。本サンプルを `input/` にコピーして
`/design` を呼べば **30 分以内に最初の STEP/STL が出る** ことを保証する目的で
同梱しています。慣れたら `/measure` から自前のオブジェクトで設計を始めてください。

## 関連

- `@.claude/skills/design/SKILL.md` — `/design` の入出力
- `@.claude/rules/closures-catalog.md` — snap_fit の選び方
- `@.claude/rules/materials-catalog.md` — PLA の推奨値
