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
- **嵌合 + 蝶番 + ラッチ + 壁埋込ナックル**: 工具なしで開閉、脱落防止、確実な閉鎖
- **カラビナタブ**: 本体側面に台形タブ + 貫通穴で吊り下げ
- **body_text**: +Z 面に "RIBBIT GPS module" の盛り上げ加工
- **5 オブジェクトを 1 ケースに集約**: USB ケーブル取り回し + Grove 接続を含む

## 段階 4 で起きたこと(2 ラウンド)

### 第 1 ラウンド(2026-04-30)— 蓋方向とカラビナ

初稿(`carabiner_hole`、蓋方向 +Z)→ 利用者から feedback:
- 蓋: +Z(横持ち上面) → **+X**(縦持ち上端、タバコ箱型)
- カラビナ穴 → **カラビナタブ**(本体側面の突起 + 穴)

Claude の対応:
- `case-spec.yaml` の `closure.lid_axis` を追加、features の type を `carabiner_hole` → `carabiner_tab` に置換
- `case-config.yaml` に `carabiner_tab` パラメータブロックを追加
- `generator.py` の `build_case_body` / `build_lid` を書き直し、`apply_carabiner_tab` 関数を追加

詳細: [`input/feedback/2026-04-30.md`](input/feedback/2026-04-30.md)

### 第 2 ラウンド(2026-05-02)— 嵌合・蝶番・リリーフカット

実際にプリントして組み立てたところ:
- **蝶番ピン挿入後、嵌合リップが本体に入らない**(全周クリアが不足)
- **本体壁の埋込部に蓋シリンダーが干渉**(蓋ナックル Z 位置に本体壁が solid で残る)
- **蝶番側だけ非対称にクリア欲しい**(ピンが拘束 → 印刷誤差吸収マージンが必要)

制約: 本体は印刷 10 時間で再印刷不可。**蓋のみで吸収**したい。

Claude の対応:
- `lid.fit_clearance`: 0.2 → **0.4 mm**(全周共通)
- `hinge.lid_knuckle_extra_clearance_z: 0.3` 新設(蓋ナックルだけ縮小、本体ナックル不変)
- `hinge.body_relief_clearance: 0.3` 新設(**本体壁の円筒リリーフカット**)
- `lip_hinge_side_extra_clearance: 1.1` 新設(蝶番側のみ追加クリア → -Y クリア = 1.5mm)
- 本体 STL ハッシュが変更前後で一致することを確認

これらの教訓から **`/fit-check` skill が誕生** し、case-blueprint テンプレートに反映されました。

詳細: [`input/feedback/2026-05-02.md`](input/feedback/2026-05-02.md)

## ファイル構成

| ファイル | 内容 |
|---|---|
| `input/objects/*.yaml`(5 件) | 採寸記録 |
| `input/requirements/case-spec.yaml` | ケース全体仕様(closure + features) |
| `input/design-params/case-config.yaml` | 寸法パラメータ(L2 主要編集対象) |
| `input/feedback/2026-04-30.md` | 第 1 ラウンド: 蓋方向 + カラビナ変更 |
| `input/feedback/2026-05-02.md` | 第 2 ラウンド: 嵌合 + リリーフカット |
| `output/design/generator.py` | CadQuery 実装(教材) |
| `output/design/validator.py` | 単一パーツの検証ロジック |
| `output/design/fit_check.py` | **嵌合・干渉チェック実装**(`/fit-check` skill 由来) |
| `output/reports/validation.md` | 検証結果(全 pass) |
| `output/reports/fit-check.md` | 嵌合チェック結果(15 pass / 0 fail) |
| `output/print/slicer-notes.md` | スライサー設定推奨 |

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
python output/design/validator.py
python output/design/fit_check.py
```

## このプロジェクトから case-blueprints へのフィードバック

実例分析の結果、以下が `case-blueprint/` に反映されました。

### 第 1 ラウンドの反映(コミット `b57847f`〜`97c90f4`)

- `/measure` Step 6 notes: 「接続関係」「運用方針」「サイズ最適化方針」を追記
- `/design` case-spec.yaml: `lid_axis`, `closure.snap_fit/hinge/catch`, `layout.notes`, `objects[].note` を例示
- `/design` case-config.yaml: **「オープン構造」を明示**(features 別パラメータブロック)
- `/export` slicer-notes: ファイル一覧 / サポート部位別 / 印刷設定表 / 後処理 / トラブルシューティング表
- `/review-fix`: type 置換と case 構造変更を分類に追加
- `quality-gates.md` 新設(5 段階ゲート + Validator 13 項目)
- `pitfalls.md` 新設(印刷・設計・運用の落とし穴 12 件)
- `src/fonts/` ライセンス管理ルール追加

### 第 2 ラウンドの反映(コミット `101138b`)

- **`/concierge` skill 新規追加**(対話オーケストレータ、6 skill 体制へ)
- **`/fit-check` skill 新規追加**(段階 4-5 橋渡し、CAD 干渉解析 + 過去事例ルール)
- `pitfalls.md` に追加 4 件: P13 リリーフカット忘れ / P14 蝶番側非対称クリア / P15 本体固定運用 / P16 ALLOWLIST 暗黙許容禁止
- `quality-gates.md` に fit-check ゲート追加
- `review-fix`: fit-check 連携 + 本体固定運用の指針
- `export`: fit-check 推奨を前提に追加
- `constitution.md` §4: fit-check と concierge を 5 段階の補完として位置づけ
