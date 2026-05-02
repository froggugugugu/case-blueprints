# 実例: ribbit-m5stick-gps-logger-exterior

このディレクトリは `case-blueprints` テンプレートを使って実際に設計・試作した **GPS ロガーケースの完成例** です。

## プロジェクト概要

| 項目 | 内容 |
|---|---|
| 収納対象 | M5StickS3 + GPS モジュール + モバイルバッテリー(+ USB-C ケーブル + Grove ケーブル) |
| 用途 | アウトドア用の GPS ロガー(カラビナで吊るす) |
| プリンタ | ANYCUBIC MEGA-S(bed 210 × 210 × 205mm) |
| 材料 | PLA |

## 設計の特徴

- **タバコの箱型**: 縦持ち、長軸 X = 125mm が垂直、+X 端が蓋
- **嵌合 + 蝶番 + ラッチ**: 工具なしで開閉、脱落防止、確実な閉鎖
- **カラビナタブ**: 本体側面に台形タブ + 貫通穴で吊り下げ
- **body_text**: +Z 面に "RIBBIT GPS module" の盛り上げ加工
- **5 オブジェクトを 1 ケースに集約**: USB ケーブル取り回し + Grove 接続を含む

## 段階 4 で起きたこと

初稿(`carabiner_hole`、蓋方向 +Z)→ 段階 4 で利用者から feedback:

- 蓋の方向: +Z(横持ち上面) → **+X**(縦持ち上端、タバコ箱型)
- カラビナ穴ではなく **カラビナタブ**(本体側面の突起 + 穴)に変更

これを受けて Claude が:
- `case-spec.yaml` の `closure.lid_axis` を追加、features の type を `carabiner_hole` → `carabiner_tab` に置換
- `case-config.yaml` に `carabiner_tab` パラメータブロックを追加
- `generator.py` の `build_case_body` / `build_lid` を書き直し、`apply_carabiner_tab` 関数を追加

詳細: [`input/feedback/2026-04-30.md`](input/feedback/2026-04-30.md)

## ファイル構成

| ファイル | 内容 |
|---|---|
| `input/objects/*.yaml`(5 件) | 採寸記録 |
| `input/requirements/case-spec.yaml` | ケース全体仕様(closure + features) |
| `input/design-params/case-config.yaml` | 寸法パラメータ(L2 主要編集対象) |
| `input/feedback/2026-04-30.md` | 段階 4 のフィードバック |
| `output/design/generator.py` | CadQuery 実装(教材) |
| `output/design/validator.py` | 検証ロジック(13 項目) |
| `output/reports/validation.md` | 検証結果(全 pass) |
| `output/print/slicer-notes.md` | スライサー設定推奨(部位別サポート / トラブルシューティング含む) |

## 削除済み(配布できないもの)

整形時に以下を削除:

- `output/preview/*.step` `*.stl`(バイナリ派生物)
- `output/print/*.stl` `*.3mf` `*.gcode`(同上)
- `src/fonts/ToaHI-Rg.ttf`(配布禁止フォント本体、`LICENSE-ToaHI.txt` のみ残す)
- `.git/`, `.venv/`, `*.egg-info/`(環境固有)
- `.claude/skills/`(古いテンプレのスナップショット、最新は `case-blueprint/.claude/skills/` 参照)

## この実例を再現したい場合

```bash
# 1. テンプレートを展開
bash case-blueprints/case-blueprint/setup.sh ./my-gps-logger-case

# 2. このディレクトリの input/, project-config.yaml, output/design/*.py を参考に編集

# 3. フォントを配置(配布禁止のため個別ダウンロード)
mkdir -p src/fonts && cp ~/path/to/ToaHI-Rg.ttf src/fonts/

# 4. Python 環境
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 5. 生成
python output/design/generator.py
```

## このプロジェクトから case-blueprints へのフィードバック

実例分析の結果、以下の改善が `case-blueprint/` に反映されました(コミット `b57847f`〜`97c90f4`):

- `/measure` Step 6 notes: 「接続関係」「運用方針」「サイズ最適化方針」を追記
- `/design` case-spec.yaml: `lid_axis`, `closure.snap_fit/hinge/catch`, `layout.notes`, `objects[].note` を例示
- `/design` case-config.yaml: **「オープン構造」を明示**(features 別パラメータブロックを追加可能)
- `/export` slicer-notes: ファイル一覧 / サポート部位別 / 印刷設定表 / 後処理 / トラブルシューティング表を追加
- `/review-fix`: type 置換と case 構造変更を分類に追加
- `case-blueprint/.claude/quality-gates.md` 新設(5 段階ゲート + Validator 13 項目)
- `case-blueprint/.claude/pitfalls.md` 新設(印刷・設計・運用の落とし穴 12 件)
- `case-blueprint/` に `src/fonts/` ライセンス管理ルール追加(`.gitignore.template` で `*.ttf` 除外)
