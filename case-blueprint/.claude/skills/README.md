# skills/ — 6 つの skill

5 段階ワークフローと、その上に乗る対話オーケストレータの計 6 つの skill を定義します。

## オーケストレータ

| スキル | 役割 |
|---|---|
| `/concierge` | さっぱりした設計者として現状を確認し、次の選択肢を AskUserQuestion で提示しながらワークフローを回す。途中での採寸し直しや方針転換も受け入れる |

## 各段階のスキル

| スキル | 段階 | 役割 |
|---|---|---|
| `/measure` | 1 | AskUserQuestion で対話的に採寸 → `input/objects/<id>.yaml` |
| `/design` | 2-3 | 要件統合 + CadQuery 生成 + validator |
| `/review-fix` | 4 | フィードバックを読み取り設計を更新 |
| `/fit-check` | 4-5 (橋渡し) | パーツ間の嵌合・接合面・蝶番組合せの干渉/クリアランスを点検 |
| `/export` | 5 | 最終 STL / 3MF + スライサー設定 |

## 推奨フロー

```
/concierge を起動 → 状態判定 → 必要な skill を都度呼ぶ
                       ↑
       ユーザーは「もう良い」と言うまで対話継続
```

または直接 skill を呼ぶ:

```
measure → design → review-fix(必要に応じ反復)→ fit-check → export
                       ↑                             ↓
                       └─── 失敗時は review-fix へ ──┘
```

`/concierge` は司会に徹し、各 skill の責務は侵しません。
詳細は各 SKILL.md を参照。
