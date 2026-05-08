# materials カタログ — `print_settings.default_material` で参照される材料 ID 一覧

`project-config.yaml` の `print_settings.default_material` に書ける材料 ID と、
それぞれの**寸法・嵌合・耐環境・印刷設定**の標準値カタログ。

データ正典は `src/case_blueprint/data/materials/<id>.yaml`。validators / closures
/ /fit-check はこの値を引いて推奨範囲をチェックする。

## 標準材料一覧(2026-05 時点)

| id | 用途の主軸 | 屋外可 | 耐熱 | 推奨 snap_fit クリア | 線収縮 |
|---|---|---|---|---|---|
| `pla` | 屋内ケース・小物入れ・装飾 | ❌ | 〜55 °C | 0.15-0.30 mm | 0.3 % |
| `pla_plus` | 反復動作のヒンジ・ラッチ・落下リスク | ❌ | 〜60 °C | 0.15-0.30 mm | 0.3 % |
| `petg` | 屋外・濡れ環境・ヒンジ繰返動作 | ✅ | 〜75 °C | 0.20-0.35 mm | 0.6 % |
| `abs` | 高温環境・耐衝撃・蒸気研磨仕上げ | ✅ | 〜95 °C | 0.25-0.40 mm | 0.8 % |
| `tpu` | パッキン/グリップ/緩衝(サブパーツ専用) | ✅ | 〜80 °C | 0.30-0.50 mm | 0.8 % |

詳細値(印刷温度・層高・無収縮率・耐 UV・後処理難度)は各 yaml を参照。

## 機構別の推奨 fit_clearance(片側 mm)

| material | snap_fit | hinge_pin | magnet_pocket |
|---|---|---|---|
| pla       | 0.15-0.30 | 0.15-0.25 | 0.10-0.20 |
| pla_plus  | 0.15-0.30 | 0.15-0.25 | 0.10-0.20 |
| petg      | 0.20-0.35 | 0.20-0.30 | 0.10-0.20 |
| abs       | 0.25-0.40 | 0.20-0.30 | 0.15-0.25 |
| tpu       | 0.30-0.50 | 0.25-0.40 | 0.15-0.30 |

`closures/*.py` の validate_* は **closure.method の機構 + project の material id** から
範囲を引き、`case-config.yaml` の値が範囲外なら ⚠ で警告(❌ ではない、印刷ばらつき次第で
許容できるため)。

## 材料選定の決定木

```
Q1. 屋外で使う?
  YES → Q2. 高温(車内・夏季屋外)?
    YES → ABS
    NO  → PETG
  NO  → Q3. 落下/反復動作?
    YES → PLA+
    NO  → PLA(寸法精度・印刷容易さで最有力)

サブパーツに弾性が必要 → TPU(パッキン・グリップ・緩衝)
```

## 新材料を追加するとき

1. `src/case_blueprint/data/materials/<id>.yaml` を追加(`material.schema.yaml` 準拠)
2. 本カタログに行を追加(主要数値のみ、詳細は yaml 参照)
3. `tests/test_materials.py` の `EXPECTED_IDS` に追加
4. 関連する pitfall を `pitfalls.md` に追記

## 関連

- `@schemas/material.schema.yaml` — 機械可読スキーマ
- `@.claude/pitfalls.md` — P5(嵌合クリア)、P1(印刷向き)
- `@.claude/skills/export/SKILL.md` — slicer-notes に材料別印刷設定を反映
- `@.claude/skills/fit-check/SKILL.md` — 嵌合チェックで material 別レンジを参照
