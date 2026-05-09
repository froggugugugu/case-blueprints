---
name: style
description: 意匠(美的センス)を扱う横断スキル。利用者の自然言語要求(「未来感を出したい」「ファンシーに」「角を丸めて」「ヘキサ柄を表面に」「アニメ ○○ のイメージで」)を case-config.yaml の `style:` セクションに翻訳する。/design 前後どちらでも呼べる。
when_to_use: 「未来感」「ファンシー」「ミニマル」「インダストリアル」「キュート」「レトロ」「角の処理」「表面パターン」「装飾」「アニメ風」「印刷物の見た目を整える」のとき。設計確定後の意匠変更にも使う。
argument-hint: "[theme <name> | refine | from-image <url>]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash(.venv/bin/python *), Bash(python *)
paths:
  - "input/design-params/case-config.yaml"
model: claude-opus-4-7
---

# /style — 意匠(美的センス)skill

## 目的

ケース全体の意匠(角の処理、表面パターン、装飾、テーマ)を、利用者の
**自然言語要求** や **参考画像** から `case-config.yaml` の `style:`
セクションに翻訳する。

横断スキル — 5 段階(measure / design / review-fix / fit-check / export)に
属さず、`/design` の前後どちらでも呼べる:

- `/design` の **前** に呼ぶ → 初稿に意匠が乗る
- `/design` の **後** に呼ぶ → 設計はそのまま、意匠だけ変える

## モード

利用者は以下のサブコマンドで操作する。引数なしの `/style` は対話で
モードを問う。

### `/style theme <name>`

主要テーマを 1 つ選び、関連パラメータ群を `style:` に書き込む。
利用可能なテーマ(`src/case_blueprint/style.py` の `THEMES` 辞書):

| theme | 角 | 表面パターン | 雰囲気 |
|---|---|---|---|
| `futuristic` | sharp + chamfered_edge | hex_grid 0.35 / 0.4mm | 機械的、未来的 |
| `minimal` | medium fillet | none | シンプル、無装飾 |
| `fancy` | large fillet | dot_pattern 0.5 / 0.6mm | 装飾的、可愛い(L1 では未実装) |
| `industrial` | sharp + mixed | linear_groove 0.3 / 0.5mm | 工業製品風 |
| `cute` | extra_large fillet | none | 柔らかい、丸い |
| `retro` | medium fillet | linear_groove 0.25 / 0.6mm | ノスタルジック |

例:

```
/style theme futuristic
```

→ `case-config.yaml` の `style:` を以下のように書く:

```yaml
style:
  theme: futuristic
  # 個別値は `style.py` の THEMES["futuristic"] から派生する
```

### `/style refine`

既存の `style.theme` がある状態で、利用者の自然言語要求から個別パラメータを
微調整する。例:

- 「もう少し角を鋭く」 → `style.fillets.outer_corners: medium → sharp`
- 「ヘキサ密度を下げて」 → `style.surface.density: 0.35 → 0.20`
- 「emboss を凸に」 → `style.surface.depth: 0.4 → -0.4`(負値は凸)
- 「天面じゃなく前面に」 → `style.surface.side: "+Z" → "-Y"`

明示値は theme 由来より優先される(deep merge)ため、利用者が refine した
内容は theme を後で変えても残る(再 merge される)。

### `/style from-image <url|path>`

参考画像(アニメのスクリーンショット、他社製品の写真等)を渡すと、Claude
Vision で解釈してスタイルパラメータを提案する。**L1 では未実装**(将来予約、
`reference_images` 配列に URL/path を保存するのみ)。

将来 L3 で実装するときは:
1. 画像を Vision で解釈し、形状特徴・色調・装飾要素を抽出
2. 「スタイル DNA」中間表現に整理
3. 既存の theme + パラメータ群に翻訳

## 利用フロー

```
1. /style theme <name>          ← 大枠を決める
       ↓
2. /design(または既存設計)      ← 設計に style が乗る(case-config.yaml 経由)
       ↓
3. /review-fix(or /style refine) ← STEP/STL を見て微調整
       ↓
4. /fit-check → /export
```

意匠は **試行錯誤の領域** なので、ゲートは設けない(/review-fix と同じ精神)。

## case-config.yaml への追記スキーマ

```yaml
style:
  theme: futuristic              # futuristic / minimal / fancy / industrial / cute / retro / custom
  silhouette: rectangular        # rectangular / rounded(角丸)/ hex(六角プリズム)/ capsule(両端半円)
  fillets:
    outer_corners: sharp         # sharp / medium / large / extra_large
    edge_treatment: chamfered_edge  # chamfered_edge / fillet / mixed / none
  surface:
    pattern: hex_grid            # hex_grid / linear_groove / dot_pattern / none
    density: 0.35                # 0.0-1.0
    depth: 0.4                   # 正値=凹彫り、負値=凸 emboss
    side: "+Z"
    pitch: 8.0                   # パターン間隔(任意、未指定なら density から逆算)
  reference_images: []           # L3 で使う(URL or local path)
```

## generator.py との連動

`src/case_blueprint/style.py` の以下の関数を generator が呼ぶ:

- `apply_style_to_case_config(case_config)`: theme + 明示値を解決し、
  `case_config.fillet.outer_radius` 等の派生値を埋める(未指定のみ)
- `derive_decorative_features(style_cfg)`: `style.surface.pattern` から
  `decorative_pattern` feature を生成し、`features[]` に追加する

これにより利用者は **style.theme: futuristic と書くだけ** で
`fillet.outer_radius: 0.5` と `decorative_pattern (hex_grid)` の両方が
ケースに乗る。

## 装飾と機能の競合を避ける

- `body_text` と `decorative_pattern` の `side` が同じだと両者重なる
  恐れあり。`/fit-check` の D カテゴリ(features 干渉)が bbox 重なりを検出
- `ventilation` と `decorative_pattern` の `side` が同じだと、貫通孔と
  装飾凹みが共存して見栄えが損なわれる場合あり。Claude が利用者に確認

## 注意事項

- **過剰装飾を避ける**: `density > 0.5` や `depth > 1.5` は印刷困難 +
  寸法影響大(P3 過剰フィレットと同じ精神)
- **ハイブリッドゾーンの尊重**: 利用者が `case-config.yaml` の `style:` を
  直接編集している場合、Claude は theme の再適用で上書きしない
- **試走前の `style` 切替**: `/export` 後の物理ループで意匠を変えると
  本体再印刷が必要(P15 本体不変原則)。蓋面のみの装飾なら蓋だけで済む
- **視認性 vs 装飾**: 屋外用ケースで dark color + 凹凸過多は熱吸収を増やす
  (P20 熱変形)。屋外なら明色 + 装飾は控えめに

## 関連

- `@.claude/skills/design/SKILL.md` — 段階 2-3、style と設計の連動
- `@.claude/skills/review-fix/SKILL.md` — 段階 4、style の微調整
- `@schemas/case-config.schema.yaml` — `style:` セクション
- `@src/case_blueprint/style.py` — `THEMES` 辞書 + resolve_style + derive_decorative_features
- `@.claude/rules/features-catalog.md` — `decorative_pattern` feature
- `@.claude/pitfalls.md` — P3(過剰装飾)、P20(熱変形と色)
