# closures カタログ — `closure.method` 一覧

`case-spec.yaml` の `case.closure.method` に指定できる closure 方式の標準カタログ。
オープン構造のため、新しい method は `src/case_blueprint/closures/<name>.py` に
`@register("<name>")` 付き関数を追加するだけで増やせる。

## 標準実装一覧(2026-05 時点)

| method | 部品数 | 蝶番 | ラッチ | ねじ | 磁石 | 主な用途 |
|---|---|---|---|---|---|---|
| `snap_fit` | 2(本体/蓋) | — | リップ嵌合の摩擦 | — | — | 最も簡単、小物入れ |
| `screws` | 2(本体/蓋)+ ねじ | — | ねじ締結 | M2/M3/M4 | — | 堅牢、防水との相性 |
| `magnetic` | 2(本体/蓋)+ 磁石 | — | 磁力吸着 | — | ネオジム | 最薄、頻繁開閉 |
| `snap_lip_with_hinge` | 2(本体/蓋)+ ピン | あり | リップ嵌合の摩擦 | — | — | 開閉ヒンジ + レバー無しで完結 |
| `hinge_lever` | 3(本体/蓋/レバー)+ ピン | あり | レバー式フック | — | — | 確実なロック、開閉容易 |

## 推奨パラメータ

各 method を選んだとき、`case-config.yaml` で最低限揃えるべき値。

### `snap_fit`

```yaml
lid:
  thickness: 2.0
  fit_clearance: 0.2          # P5 参照、0.2-0.4 mm 推奨
  lip_height: 3.0             # 1.0 mm 以上(validate_snap_fit が assert)
```

### `screws`

```yaml
hardware:
  preset: m3_screws            # 利用者プリセットを hardware-catalog.md から選ぶ
  closure:
    fastener: { nominal: M3, length: 12, diameter: 3.0 }
closure:
  screws:
    count: 4                   # 2 本以上(対角配置を assert)
    boss_outer_diameter: 6.0
    pilot_diameter: 2.55       # M3 セルフタップ下穴
    countersink: { enabled: true, top_diameter: 6.5, depth: 1.6 }
```

### `magnetic`

```yaml
hardware:
  preset: magnet_d6_t3
  closure:
    magnet: { outer_diameter: 6.0, thickness: 3.0, type: neodymium_n52 }
closure:
  magnetic:
    count: 4
    pocket_depth: 3.4          # magnet.thickness + 0.2 以上
    air_gap: 0.15              # 0.1-0.3 mm 推奨
    polarity_alternating: false
```

### `snap_lip_with_hinge`

```yaml
hardware:
  preset: m2_long              # hardware-catalog.md
hinge:
  knuckle: { outer_diameter: 6.0, pattern: [body, lid, body], z_clearance: 0.4 }
  fit_clearance_extra: 0.5     # P14、0.3 以上(validate が assert)
lid:
  fit_clearance: 0.2
  lip_height: 3.0
```

### `hinge_lever`

`/hinged-lid init` で全パラメータ生成。詳細は `@.claude/skills/hinged-lid/SKILL.md`。

## 新しい method を追加するとき

1. `src/case_blueprint/closures/<name>.py` を作成
2. ヘッダで `from . import register`
3. `validate_<name>(case_config, hardware)` を実装(P5 等の落とし穴対策)
4. `@register("<name>")` を付けた `build_<name>_closure(body, lid, case_spec, case_config) -> dict[str, Any]` を実装
5. `closures/__init__.py` の末尾 import に `from . import <name>` を追加
6. 本カタログに行を追加
7. `quality-gates.md` の closure 別ゲートも見直す

## 関連

- `@.claude/skills/design/SKILL.md` — `closure.method` を抽象的に決める
- `@.claude/skills/hinged-lid/SKILL.md` — `hinge_lever` 専用詳細
- `@.claude/rules/hardware-catalog.md` — ハードウェアプリセット
- `@.claude/pitfalls.md` — P5(嵌合クリア)、P13(リリーフ)、P14(非対称)
