---
paths:
  - "output/print/**"
  - "output/design/fit_check.py"
---

# 印刷安全規約

実物プリント / 試作プリント前に守るゲート群。pitfalls.md と quality-gates.md の関連項を要約。

## 印刷前チェック

1. **validator が ❌ 0**(`output/reports/validation.md`)
2. **fit-check が ❌ 0** または明示許容のみ(`output/reports/fit-check.md`)
3. `output/print/slicer-notes.md` が最新(generator.py より新しい)
4. ALLOWLIST に登録された意図的重なりは label / max_mm3 / 理由が併記されている(P16)

## 印刷向きの物理 bake

- `case-spec.yaml` の `print_orientation` に従って `generator.py` が物理的に回転して STL/3MF を出力
- スライサーで再配置不要にする(利用者の手間と誤配置を排除)

## 嵌合がきつい/ゆるい場合

- **やすりで対処しない**(P6, P10): CAD で解決して再生成 → 再印刷で再現性を保つ
- 全周一律にきつい → `lid.fit_clearance` を増やす(0.3 推奨)
- 蝶番側だけ擦る → `lid.lip_hinge_side_extra_clearance` を導入(P14)
- 蝶番ナックルが本体壁と干渉 → `hinge.body_relief_clearance` を設定(P13)

## 本体再印刷不可な状況での対応(P15)

- 本体 STL ハッシュ(`shasum` / `md5sum`)を変更前後で比較し、不変性を確認
- 蓋のみで吸収できるパラメータを優先:
  - `lid.fit_clearance` の蓋側のみ縮小
  - `hinge.lid_knuckle_extra_clearance_z`
  - `hinge.lid_relief_clearance`

## マルチパーツ印刷時の注意(closure=hinge_lever)

- `case-body.stl`, `case-lid.stl`, `latch-lever.stl` は別オブジェクト
- レバーは底面接地、サポート不要(本体・蓋とは別設定でよい)
- 組立時はレバーピン → catch ピン → 本体ヒンジピン の順で挿入
