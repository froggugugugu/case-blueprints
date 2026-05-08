# レポート md のスタイル規約

`output/reports/` 配下と `output/print/slicer-notes.md` の表記を統一する。
利用者が複数回レポートを並べたときに見た目で迷わないことを優先する。

## 適用先

| ファイル | 主な書き手 |
|---|---|
| `output/reports/validation.md` | `validator.py`(段階 3) |
| `output/reports/fit-check.md` | `fit_check.py`(段階 4-5) |
| `output/print/slicer-notes.md` | `slicer-advisor` agent / `/export` |
| `output/reports/session-<date>.md` | `SessionEnd` hook |
| `output/reports/_audit.jsonl` | `SubagentStop` hook(JSON Lines、本規約対象外) |

## 共通ルール

### 見出し階層

- 最上位は `# <Report 名>`(1 つだけ)
- セクションは `## A. 内寸マージン` のようにアルファベット番号 + 短い名前
- 小見出しは `###`(必要なときのみ)
- `####` 以上は使わない(深さ 3 まで)

### 絵文字の使い分け

| 絵文字 | 意味 | 使う場面 |
|---|---|---|
| ✅ | Pass | 全項目クリア / 推奨値達成 |
| ⚠ | Warning | 推奨値未達だが致命ではない、要監視 |
| ❌ | Fail | 印刷前に修正必須 |
| 🚫 | Block | hook がツール実行をブロックした |
| 📐 | Stage | statusline / state summary |

その他の絵文字は使わない(過剰装飾を避ける)。

### サマリー必須

各レポートは冒頭 5 行以内に「Pass / Warning / Fail の件数」を出す。
詳細は項目ごとのセクションに。

```markdown
# Validation Report

- Pass: 14
- Warning: 1
- Fail: 0

## A. 壁厚
- ✅ thickness ≥ 2.0 mm
...
```

### 数値表記

- 単位を必ず付ける(`mm`, `mm³`, `°`)
- 数値と単位の間に **半角スペース 1 つ**: `0.4 mm`(`0.4mm` でなく)
- 角度は `°` または `deg` を統一(本プロジェクトでは `°`)
- 比率はパーセント: `density: 30%`

### コードブロック

- YAML 例は ```` ```yaml ```` で囲む
- Python 例は ```` ```python ````
- shell コマンドは ```` ```bash ````
- 出力例は ```` ```text ````

## ファイル別の追加ルール

### `validation.md`

- 各項目は `- ✅ <チェック名>` 形式
- 失敗時は `- ❌ <チェック名>: <理由>(値=X 推奨=Y)`

### `fit-check.md`

- セクション A〜F(quality-gates の表に対応)
- ALLOWLIST との照合結果を D セクションに数値で(`重なり総体積 / 許容上限 / 未許容`)

### `slicer-notes.md`

- ファイル一覧 → 印刷向き → サポート → 印刷設定 → 後処理 → トラブルシューティング の順
- 機種名・銘柄名は出さない(「お使いのスライサー」「3MF 対応スライサー」)

### `session-<date>.md`

- `## HH:MM:SS (session: <id>)` で時刻見出し
- 終了時の現在地 1 行のみ(冗長を避ける、詳細は audit.jsonl 側)

## 関連

- `@.claude/quality-gates.md` — 段階別ゲート
- `@.claude/skills/export/SKILL.md` — slicer-notes.md の中身仕様
- `@.claude/skills/fit-check/SKILL.md` — fit-check.md の中身仕様
