# hardware カタログ — `hardware:` プリセット一覧

`case-config.yaml` の `hardware:` セクションで指定できるプリセットの標準カタログ。
プリセット名は **物理的に同定できる規約**(規格名 + 主要寸法)。

## 標準プリセット

### ヒンジ + レバーラッチ系(`/hinged-lid` で使用)

| preset | 用途 | ピン | ねじ | 数 |
|---|---|---|---|---|
| `m2_long` | デフォルト・標準ヒンジ蓋 | M2 × 28 mm | M2 × 30 mm | ピン 1 + ねじ 2 |
| `m2_short` | 幅狭ラッチ・小型ケース | M2 × 14 mm | M2 × 16 mm | ピン 1 + ねじ 2 |
| `m2.5_long` | 中型・若干強度向上 | M2.5 × 30 mm | M2.5 × 32 mm | ピン 1 + ねじ 2 |
| `custom` | 任意値(scale/hardware 切替時に上書きされない) | 任意 | 任意 | 任意 |

### ねじ closure 系(`closure.method = screws`)

| preset | ねじ | 用途 |
|---|---|---|
| `m3_short` | M3 × 8 mm セルフタップ | 標準肉厚ケース |
| `m3_long` | M3 × 16 mm 貫通 + ナット | 防水・厚壁 |
| `m2_short_screws` | M2 × 6 mm セルフタップ | 薄壁・小型 |
| `heatset_m3` | M3 × 12 mm + heat-set インサート | 繰り返し開閉 |

### 磁石 closure 系(`closure.method = magnetic`)

| preset | 磁石 | 鉄板 |
|---|---|---|
| `magnet_d6_t3` | ネオジム N52 φ6 × t3 | SS400 t1.0 φ12 |
| `magnet_d8_t3` | ネオジム N52 φ8 × t3 | SS400 t1.0 φ15 |
| `magnet_d10_t2` | ネオジム N52 φ10 × t2 | SS400 t1.0 φ18 |
| `mag_to_mag` | 同上 + 蓋側にも磁石(両側磁石) | — |

## プリセットの YAML 例

### `m2_long`(ヒンジ蓋デフォルト)

```yaml
hardware:
  preset: m2_long
  hinge:
    fastener:
      type: screw_pan_head
      nominal: M2
      length: 30.0
      diameter: 2.0
      head_diameter: 4.0
      head_height: 1.6
      engagement: self_tap         # 末端ナックルでセルフタップ
    count: 2
  latch:
    pivot_pin:
      type: parallel_pin
      nominal: M2
      length: 28.0
      diameter: 2.0
    catch_pin:
      type: parallel_pin
      nominal: M2
      length: 28.0
      diameter: 2.0
    count: 1
```

### `m3_short`(ねじ closure 標準)

```yaml
hardware:
  preset: m3_short
  closure:
    fastener:
      type: screw_pan_head
      nominal: M3
      length: 8.0
      diameter: 3.0
      head_diameter: 5.6
      head_height: 1.86
      engagement: self_tap
```

### `magnet_d6_t3`(磁石 closure 標準)

```yaml
hardware:
  preset: magnet_d6_t3
  closure:
    magnet:
      type: neodymium_n52
      outer_diameter: 6.0
      thickness: 3.0
      max_pull_force_n: 8.0          # 参考値、対向距離 0 mm
    counter_plate:
      material: SS400
      thickness: 1.0
      outer_diameter: 12.0
```

## 新しいプリセットを追加するとき

1. **物理的な同定** が可能な命名(規格 + 主要寸法)を選ぶ。`big_screws` のような曖昧名は禁止
2. 本カタログに行を追加
3. `closures/` 該当モジュールの `validate_<method>()` で参照される値が揃うように YAML 雛形を書く
4. `pitfalls.md` に該当する失敗例があれば併記(例: P17 ピン長制約)

## 関連

- `@.claude/skills/hinged-lid/SKILL.md` — ヒンジ蓋プリセット運用
- `@.claude/rules/closures-catalog.md` — closure.method との対応
- `@.claude/pitfalls.md` — P17 ピン長制約
