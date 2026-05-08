# features カタログ — `case-spec.features[].type` 一覧

`case-spec.yaml` の `case.features[]` に登場し得る型(オープン構造の type 名)の
標準カタログ。`generator.py` 側で `@register("<type>")` を付けたハンドラを
書けば自動的に dispatcher に乗る。

## 標準 type 一覧

| type | 配置面の例 | 主なパラメータ | 出力 |
|---|---|---|---|
| `ventilation` | `top` / `+Z` | `pattern`(grid/slots/honeycomb), `density` | 通気孔の配列 |
| `cable_port` | `back` / `+X` 等 | `position[x,y]`, `diameter`, `oblong[w,h]` | 円 or 長穴 |
| `display_window` | `front` | `size[w,h]`, `position[x,y]`, `bezel` | 矩形抜き |
| `carabiner_hole` | `top` / `+Z` | `diameter`, `position` | 単純円穴 |
| `carabiner_tab` | `+Y` 等 | `shape`(trapezoid), `base_width_x`, `tip_width_x`, `extend_y`, `thickness_z`, `hole_diameter`, `tip_fillet_radius` | 突き出しタブ + 穴 |
| `mounting_bracket` | 内部 | `target`(object id), `style`(ribs/clip/screw_post) | 内部マウント |
| `body_text` | `+Z` 等 | `text`, `font_file`, `emboss_depth`, `side` | 凸文字(ローカルフォント) |
| `magnet_pocket` | 任意 | `outer_diameter`, `depth`, `position`, `count` | 磁石埋込ポケット |
| `velcro_loop` | `+Y` / `+X` | `width`, `length`, `thickness` | ベルクロ通しループ |

「以上」を超える type を Claude が必要に応じて命名(snake_case)できる。

## サイド指定の規則

`side` は以下のいずれか:

- 軸記法: `+X` / `-X` / `+Y` / `-Y` / `+Z` / `-Z`
- 通称: `top` (= `+Z`), `bottom` (= `-Z`), `front`, `back`, `left`, `right`
- 内部: `internal` (内寸面)

通称 ↔ 軸記法のマッピングはケース毎の `case-spec.yaml` の文脈で確定する。
`generator.py` の側で揺れがないように **どちらか一方に正規化** すること(推奨: 軸記法)。

## 推奨パラメータ

### `ventilation`

```yaml
features:
  - type: ventilation
    side: "+Z"
    pattern: grid             # grid / slots / honeycomb
    density: 0.3              # 開口面積比 0.0-0.5、印刷強度を考慮
    hole_diameter: 3.0        # grid の場合
```

### `cable_port`

```yaml
features:
  - type: cable_port
    side: "+X"
    position: [50.0, 16.0]    # [x, y] 内寸面基準
    diameter: 8.0             # 円形
    # oblong: [w, h]          # 長穴の場合
    chamfer: 0.5              # ケーブル擦れ防止
```

### `body_text`

```yaml
features:
  - type: body_text
    side: "+Z"
    text: "MY DEVICE"
    font_file: ToaHI-Rg.ttf   # input/fonts/ にローカル配置必須(README フォント節参照)
    emboss_depth: 0.6         # 0.4-0.8 mm 推奨(層高 0.2 で 2 層相当)
    position: center
    size: 8.0                 # 高さ mm
```

### `carabiner_tab`

```yaml
features:
  - type: carabiner_tab
    side: "+Y"
    shape: trapezoid
    base_width_x: 22.0
    tip_width_x: 14.0
    extend_y: 14.0
    thickness_z: 5.0
    hole_diameter: 6.0
    tip_fillet_radius: 4.0
```

## 新しい type を追加するとき

1. `generator.py` に `@register("<type>")` を付けた `apply_<type>(part, feature, case_config)` を実装
2. `case-config.yaml` に必要なら type と同名のパラメータブロックを追加(慣習)
3. 本カタログに行を追加
4. `validator.py` に該当チェック関数を `@check` で追加(寸法・配置の妥当性)

## 関連

- `@.claude/skills/design/SKILL.md` — features 推論と generator.py 雛形
- `@.claude/skills/review-fix/SKILL.md` — 段階 4 で type 追加・置換
- `@schemas/case-spec.schema.yaml` — features は additionalProperties: true
