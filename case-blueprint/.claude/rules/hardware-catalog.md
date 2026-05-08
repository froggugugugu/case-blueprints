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

### 外部マウント系(`mounting_bracket` feature の `style` で参照)

バイク/車載/三脚等への外部固定用。`feature.type = mounting_bracket` の
`style` と対応するハードウェアセットを定義する。

| preset | 用途 | ボール径 | ねじ規格 | PCD |
|---|---|---|---|---|
| `mount_ram_ball_b` | RAM ボール B サイズ(汎用バイク・電子機器) | 1 inch (25.4 mm) | M5 × 4 点 | 38.1 mm |
| `mount_ram_ball_d` | RAM ボール D サイズ(大型機器) | 2.25 inch (57.2 mm) | M6 × 4 点 | 50.0 mm |
| `mount_gopro_3prong` | GoPro 規格 3 ツメ式 | — | M5 軸ねじ × 1 | — |
| `mount_quarter_inch` | 1/4-20 UNC(三脚 / カメラリグ) | — | 1/4-20 UNC × 1 | — |
| `mount_panel_4_corner` | パネル 4 隅 M3 取付 | — | M3 × 4 点 | プロジェクト依存 |

### 振動対策(車載・バイク等)

| preset | 用途 | 内容 |
|---|---|---|
| `heatset_m3_brass` | 振動環境のねじ締結 | M3 真鍮 heat-set インサート(5.0 × L 4.0 / 5.0 / 6.0)|
| `heatset_m4_brass` | 同上 M4 | M4 真鍮 heat-set インサート(6.0 × L 5.0 / 6.0 / 8.0)|
| `m5_lock_assembly` | RAM ベース等の M5 締結 | M5 ねじ + 平ワッシャ + スプリングワッシャ + ナット |

heat-set 系プリセットは **PETG / ABS** を前提にした寸法。PLA/PLA+ では
熱で穴が広がりやすいので推奨しない(P19 参照)。

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

### `mount_ram_ball_b`(RAM ボール B サイズ・バイクナビ標準)

```yaml
hardware:
  preset: mount_ram_ball_b
  mount:
    ball:
      type: ram_ball
      size: B                           # 1 inch (25.4 mm) 球
      diameter: 25.4
    base:
      pcd: 38.1                         # 4 点ねじ取付ピッチ円直径
      screw:
        nominal: M5
        diameter: 5.0
        length: 12.0                    # 12 / 16 / 20 のいずれか
      washer: spring_washer_m5          # ロックワッシャ前提(P19)
      nut: nyloc_m5                     # 緩み止めナット(あれば)
    locking_compound: medium            # ロックタイト中強度推奨(利用者作業)
```

`mounting_bracket` feature の `style: ram_ball_b` と組み合わせると、本体 -Z
面に円盤ベース + 4 点 M5 PCD 38.1mm を自動配置する。

### `heatset_m3_brass`(振動環境用 M3 真鍮 heat-set)

```yaml
hardware:
  preset: heatset_m3_brass
  closure:
    fastener:
      type: heatset_insert
      nominal: M3
      diameter: 3.0
      insert_outer_diameter: 5.0      # 圧入穴径基準
      insert_length: 6.0              # 4 / 5 / 6 mm
      length: 8.0                     # ねじ自体の長さ
      engagement: heatset_thread
  notes:
    install: ハンダごて 250-280℃ で圧入(PETG 推奨、PLA は熱変形)
    torque_max_nm: 0.5                # 真鍮インサートの限界
```

## 新しいプリセットを追加するとき

1. **物理的な同定** が可能な命名(規格 + 主要寸法)を選ぶ。`big_screws` のような曖昧名は禁止
2. 本カタログに行を追加
3. `closures/` 該当モジュールの `validate_<method>()` で参照される値が揃うように YAML 雛形を書く
4. `pitfalls.md` に該当する失敗例があれば併記(例: P17 ピン長制約)

## 関連

- `@.claude/skills/hinged-lid/SKILL.md` — ヒンジ蓋プリセット運用
- `@.claude/rules/closures-catalog.md` — closure.method との対応
- `@.claude/rules/features-catalog.md` — `mounting_bracket` feature の style
- `@.claude/pitfalls.md` — P17 ピン長制約 / P18 防水 / P19 振動緩み / P20 熱変形
- `@src/case_blueprint/features/mounting_bracket.py` — `mount_ram_ball_b` 等の実装本体
