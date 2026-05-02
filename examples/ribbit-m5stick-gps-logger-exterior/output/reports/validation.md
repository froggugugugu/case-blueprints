# Validation Report

## 計算結果
- 内寸 (X×Y×Z): **126.0 × 55.5 × 24.0** mm
- 本体外形 (X×Y×Z): 128.0 × 59.5 × 28.0 mm
- 蓋: 上板 2.5mm + 嵌合リップ 2.0mm(fit_clearance 0.4mm) + ラッチ壁(板 +Y 拡張 2.5mm × -X 深さ 6.0mm)
- 蓋方向 (lid_axis): **+X**
- カラビナタブ(台形): 基部 22.0mm → 先端 14.0mm, 突出 14.0mm, 厚 5.0mm, 穴径 6.0mm, 先端R 4.0mm
- 蝶番: ナックル外径 6.0mm × (本体 2 + 蓋 1), ピン径 2.0mm, 取付面 -Y, Z基準クリア 0.4mm (蓋ナックル追加縮小 0.3mm/片側)
- ラッチ: bump 径 3.0mm × 突出 0.6mm, 取付面 +Y
- body_text: 'RIBBIT GPS module' on +Z, font=ToaHI-Rg.ttf, size≈8.46mm(width_ratio=1/φ=0.618), emboss 0.6mm
- printer_bed: [210, 210, 205] mm

## チェック結果
- ✅ 壁厚が min_wall_thickness 以上
- ✅ 蓋厚が min_wall_thickness 以上
- ✅ 嵌合クリアランスが正の値
- ✅ ケース外寸 + 蓋(嵌合 + ラッチ壁)が printer_bed に収まる
- ✅ カラビナタブ: 穴周りに最低マージン確保
- ✅ カラビナタブ: 形状が台形(基部広・先端狭)
- ✅ オブジェクト最大長軸が内寸 X に収まる
- ✅ USB-C ケーブル長で M5↔バッテリー間距離をカバー可能
- ✅ 蓋方向(lid_axis)が想定範囲
- ✅ 蝶番: ナックル肉厚が最低 1mm 以上(ピン穴 - knuckle_d)
- ✅ 蝶番: 全ナックル + クリアランスが oz に収まる
- ✅ 嵌合クリアランス: FDM 推奨範囲(片側 0.3mm 以上)
- ✅ ラッチ: bump_protrusion が PLA 弾性域(0.3-1.0mm)
- ✅ body_text: フォントファイル存在 + emboss_depth が FDM 推奨範囲(0.4-1.5mm)

**合計: 14 passed, 0 failed**
