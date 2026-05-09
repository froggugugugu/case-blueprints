# bike-navi-mvp — バイクナビ統合ケース(複合 features 参照例)

ディスプレイ + ラズパイ + GPS を 1 体に組み付けたバイクナビ用ケースの **動く参照例**。
features 7 種、closure = screws、PETG + heat-set + RAM ボール B サイズ + 防水
ガスケット溝という、屋外・車載・振動を全部受ける構成。

## 何が組み込まれているか

| 要素 | 設定 | pitfalls / catalog 連動 |
|---|---|---|
| closure | `screws` × 6 点(振動冗長) | P19 振動 |
| 材料 | PETG(屋外可、UV 安定剤入りグレード推奨) | materials-catalog.md / P20 熱 |
| ねじ締結 | M3 heat-set 真鍮インサート(`heatset_m3_brass`) | hardware-catalog.md / P19 |
| マウント | RAM ボール B サイズ(`mount_ram_ball_b`、PCD 38.1mm) | hardware-catalog.md |
| 防水 | リップ + ガスケット溝(O-リング φ2)+ cable_port flange | P18 |
| ディスプレイ | 155 × 90 mm 開口、bezel(段差 1.2mm)で IPS パネル保持 | features-catalog.md |
| 物理ボタン | 14mm 円形 × 2、`gloves_compatible: true` | P19 / button_cutout |
| 放熱 | slots パターン、density 0.25、+Y 面 | P20 / ventilation |
| 刻印 | "BIKE NAV"(0.6mm 凸)、+Z 終層 | P4 / body_text |
| 印刷向き | body bottom_down、lid top_down | print-orientation-reasoning.md |
| heat-set | 振動下のねじ緩み対策(P19) | pitfalls P19 |

## 使い方

プロジェクトルート(`setup.sh` 展開後)で以下を実行:

```bash
# 1. 入力をコピー
cp -R examples/bike-navi-mvp/input/. input/

# 2. project-config.yaml を屋外用に書き換え(material: petg、bed サイズ等)
$EDITOR project-config.yaml

# 3. body_text を使う場合はフォントを配置(配布禁止フォントは LICENSE 確認)
mkdir -p input/fonts
cp /path/to/your-font.ttf input/fonts/PLACEHOLDER.ttf

# 4. Claude Code を起動して /design 以降を回す
claude
```

```
/design       # case-spec / case-config が既にあるので generator.py 生成へ直行
/fit-check    # features 干渉 + CAD 干渉 + closure ガード
/review-fix   # 必要なら寸法調整(物理ループの 1 回目想定)
/export       # 印刷ファイル + slicer-notes
```

## 想定される出力

- 外寸 約 181 × 116 × 47 mm(printer_bed 220 × 220 × 250 に余裕)
- PETG 推奨、印刷時間 8-12 時間程度(本体)+ 蓋 3-5 時間
- 後処理: heat-set インサート圧入(ハンダごて 250-280℃)、ねじ穴 6 点でロック剤
- 試走後の運用: 50km / 200km / 500km で再締結確認

## このサンプルの限界(Phase 2 で改善予定)

- **1 オブジェクト構成**: 本サンプル自体は単一ボックスだが、複数 objects の
  3D 配置(`layout: manual` + `objects[].position[x, y, z]`)は src 側で実装済。
  実案件ではディスプレイ・ラズパイ・GPS を別 object として置ける
- **mounting_bracket の clip / screw_post**: ribs / m5_screw_holes /
  ram_ball_b の 3 style のみ実装済み(他 style は generator.py 末尾で
  `@register` 追記する形で拡張)

## 関連

- `@.claude/rules/materials-catalog.md` — PETG の屋外用注釈
- `@.claude/rules/hardware-catalog.md` — heatset / mount_ram_ball_b
- `@.claude/rules/features-catalog.md` — 7 features の実装ファイル
- `@.claude/pitfalls.md` — P18 防水 / P19 振動 / P20 熱変形
