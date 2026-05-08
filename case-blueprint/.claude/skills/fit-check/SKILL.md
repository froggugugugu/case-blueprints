---
name: fit-check
description: 段階 4-5 の橋渡し — パーツ間の嵌合・接合面・蝶番組合せの干渉/クリアランスを点検する。リップ嵌合、蝶番ナックル組み合わせ、ねじ穴・差し込み・スナップ等の突合機構を CAD 干渉解析+ルールベースで検証。
when_to_use: 「嵌合をチェック」「干渉してないか確認」「ヒンジが組める?」「export 前の最終チェック」「ALLOWLIST を見直す」のとき。
allowed-tools: Read, Write, Edit, Glob, Bash(.venv/bin/python *), Bash(python *)
paths:
  - "output/design/fit_check.py"
  - "output/reports/fit-check.md"
model: claude-opus-4-7
---

# /fit-check — 嵌合・接合チェック skill

## 目的

`/review-fix` で確定した設計を `/export` する前に、**パーツ同士の嵌合と接合面のクリアランス・干渉**を網羅的に点検する。

ターゲットは:

- **リップ嵌合**: 蓋リップが本体内寸に収まるかの全周クリアランス
- **蝶番組み合わせ**: 本体ナックル × 蓋ナックルの噛み合い、ピン穴整合、壁埋込時の本体壁リリーフ
- **CAD 上の幾何干渉**: 閉じた状態で `body.intersect(lid)` の体積を計測し、未許容の重なりを検出
- **将来拡張**: ねじ穴と相手部品、差し込み突起と受け穴、スナップ機構、磁石マウント等の **2 パーツ以上の嵌合機構全般**

対象は body / lid に限らず、`PART_PAIRS` 定義に追加すれば任意のパーツペアに展開可能。

## 関連スキルとの違い

| スキル | 役割 |
|---|---|
| `validator.py` | 単一パーツの「設計ルール」(壁厚・蓋厚・タブ寸法等) |
| `/fit-check`(本スキル) | **複数パーツの嵌合**(クリアランス・干渉)+ 過去事例パターンの網羅 |
| `/review-fix` | 利用者からの個別フィードバックの反映 |
| `/export` | 最終 STL/3MF + スライサー設定 |

`fit-check` は validator と相補。validator は「壁が薄すぎないか」、fit-check は「組み立たないか」。

## 前提条件

- `output/design/generator.py` `validator.py` が存在
- `output/preview/case-body.step` `case-lid.step`(または対象パーツの STEP)が最新
- 利用者が CAD 上の重なりや 3D 形状を一度確認済み(段階 4 を経ている)

## 入出力

| 区分 | パス | 説明 |
|---|---|---|
| 入力 | `input/design-params/case-config.yaml` | 数値パラメータ |
| 入力 | `input/requirements/case-spec.yaml` | 構造仕様 |
| 入力 | `input/objects/*.yaml` | 対象オブジェクト寸法 |
| 入力 | `output/preview/*.step` | CAD 干渉解析の対象 |
| 出力 | `output/design/fit_check.py` | 初回生成・以降は利用者カスタムを尊重 |
| 出力 | `output/reports/fit-check.md` | 結果レポート |

## チェック項目(過去事例ベース)

### A. 内寸マージン

| 項目 | 推奨 | 警告 | 失敗 |
|---|---|---|---|
| object_clearance | ≥ 1.0 mm | ≥ 0.5 mm | < 0.5 mm |
| z_margin | ≥ 1.0 mm | ≥ 0.5 mm | < 0.5 mm |
| 内寸 X/Y/Z 各軸 vs 実測オブジェクト | + 1mm 以上 | + 0.5 〜 1mm | + 0.5mm 未満 |

理由: FDM 印刷の反り・収縮で内寸が縮む。実寸ぴったりだと収まらない事故多数。

### B. リップ嵌合クリアランス

| 項目 | 推奨 | 警告 | 失敗 |
|---|---|---|---|
| fit_clearance(全周共通) | ≥ 0.4 mm | ≥ 0.3 mm | < 0.3 mm |
| 蝶番側追加クリア(蝶番がある場合) | ≥ 1.0 mm | ≥ 0.5 mm | < 0.3 mm |
| ラッチ側 / 反対側 | 0.3-0.5 mm | 0.2 or 0.7 | < 0.2 or > 1.0 |

理由: 蝶番ピンが蓋位置を Y 方向に拘束するため、蝶番側だけ非対称に大きいクリアランスが必要。ラッチ側はラッチ自体の弾性で吸収できるので標準値で十分。

### C. 蝶番設計

| 項目 | 推奨 | 警告 | 失敗 |
|---|---|---|---|
| ナックル肉厚 = (knuckle_d - pin_d - pin_clear) / 2 | ≥ 1.5 mm | ≥ 1.0 mm | < 1.0 mm |
| ナックル Z 高さ | ≥ 5 mm | ≥ 3 mm | < 3 mm |
| pin_clearance | 0.4-0.6 mm | 0.3 or 0.7 | < 0.3 or > 1.0 |
| knuckle_clearance_z | 0.4-0.6 mm | 0.3 or 0.8 | < 0.3 |
| **body_relief_clearance**(壁埋込時) | ≥ 0.3 mm | ≥ 0.2 mm | < 0.2(または未設定) |
| **lid_knuckle_extra_clearance_z**(本体固定運用で蓋のみ縮める場合) | 0.3-0.5 mm | 0.2 or 0.6 | — |

理由:
- ピン挿入容易性、回転自由度、壁埋込時のリリーフカット干渉、本体固定運用への対応
- **壁埋込型蝶番の落とし穴**: 本体側ナックル円柱が壁に食い込んでいる場合、**蓋ナックル Z 位置でも本体壁が solid に存在する**ため、リリーフカット(円筒状の除去)が必要。これを忘れると蓋シリンダーが壁と干渉して蓋が収まらない

### D. CAD 上の干渉(closed state)

CadQuery で本体と蓋を閉じた位置で重ね、`body.intersect(lid)` の体積を計算:

| 体積 | 判定 |
|---|---|
| ≥ 100 mm³ | ❌ 重大な干渉 |
| 1 - 100 mm³ | ⚠ 小さな干渉(意図的か確認、`ALLOWLIST` に登録すれば pass) |
| < 1 mm³ | ✅ |

`ALLOWLIST` は `fit_check.py` 内に宣言。例:

```python
ALLOWLIST = [
    {
        "label": "本体ナックル右半円×蓋プレート -Y 端",
        "max_mm3": 50.0,
        "where": "蝶番付近、構造上避けられない 1mm 帯",
    },
]
```

ALLOWLIST の合計を超える分が「未許容の干渉」として ❌ 扱い。

**ALLOWLIST の運用ルール**:
- 意図的な重なりは label / max_mm3 / 理由を必ず併記
- 解消した重なりは ALLOWLIST から削除し、コメントで「いつ・どう解消したか」を残す(例: `# 旧エントリ「○○」は 2026-XX-XX に lid_relief_clearance を導入し CAD レベルで解消したため削除`)
- 「動作確認後の手削り対応」も ALLOWLIST 外で許容することは避ける(明示的な許容 vs 暗黙の許容を区別)

### E. 印刷可能性(他カテゴリと重複しないもの)

- 各部品が printer_bed に収まる
- 全壁が min_wall_thickness を満たす
- print_orientation が定義されている
- 蓋 axis(closure.lid_axis)が本体形状と整合

### F.(将来拡張)他の嵌合機構

`PART_PAIRS` / `MECHANISMS` に追加することで以下も対象化:

- **ねじ穴 vs 相手ボス**: 雌ねじクリアランス、ボス肉厚
- **差し込み突起 vs 受け穴**: 突起径と穴径の差、挿入長
- **スナップフック vs 受けリブ**: フック撓み量、引っ掛かり代
- **磁石マウント**: 磁石ポケット深さ、引き合い距離
- **複数オブジェクト間の接触面**: 例: バッテリーホルダーと本体ホルダーの接合面

各機構のチェック関数を `fit_check.py` 内で定義し、`MECHANISMS` レジストリに登録する設計。

## 処理フロー

### Step 1: fit_check.py(shim)の準備

本体ロジックは `src/case_blueprint/fit_check.py` に集約済み。利用者プロジェクトの
`output/design/fit_check.py` は **薄い shim** として、ALLOWLIST と generator が
組んだ parts を渡して `main()` を呼ぶだけにする:

```python
"""fit_check.py — src/case_blueprint.fit_check の shim。

本ファイルでカスタマイズするのは ALLOWLIST(意図的な微小重なりの登録)と
プロジェクト固有チェッカーのみ。MECHANISMS の登録は @register_mechanism で。
"""
from case_blueprint import fit_check, loader, closures, features  # noqa: F401

# ----- ALLOWLIST(明示許容のみ。理由を必ず併記、P16)-----
ALLOWLIST = [
    # {"label": "本体ナックル右半円×蓋プレート -Y 端",
    #  "max_mm3": 50.0,
    #  "where": "蝶番付近、構造上避けられない 1mm 帯"},
]


# ----- プロジェクト固有チェッカー(必要なら追加)-----
# @fit_check.checker("F. プロジェクト固有")
# def _check_xxx(cfg): ...


def _build_parts(cfg):
    """generator.py と同じ手順でパーツを再構築して dict で返す。
    CAD 干渉解析(D)に渡す。"""
    import cadquery as cq
    from case_blueprint.geometry import (
        internal_bbox_stacked, internal_bbox_side_by_side, external_bbox,
    )
    case_spec, case_config, objects = cfg["case_spec"], cfg["case_config"], cfg["objects"]
    layout = case_spec["case"].get("layout", {})
    arrangement = layout.get("arrangement", "stacked")
    fn = internal_bbox_stacked if arrangement == "stacked" else internal_bbox_side_by_side
    internal = fn(
        objects,
        object_clearance=case_config.get("internal", {}).get("object_clearance", 1.0),
        z_margin=case_config.get("internal", {}).get("z_margin", 0.0),
    )
    walls = case_config.get("walls", {})
    eb = external_bbox(internal, wall_thickness=walls.get("thickness", 2.0))
    body = cq.Workplane("XY").box(eb.width, eb.depth, eb.height).cut(
        cq.Workplane("XY").box(internal.width, internal.depth, internal.height)
    )
    lid = cq.Workplane("XY").box(eb.width, eb.depth, case_config.get("lid", {}).get("thickness", 2.0))
    method = case_spec["case"]["closure"]["method"]
    parts = closures.build(method, body, lid, case_spec, case_config)
    return parts


if __name__ == "__main__":
    cfg = loader.load_all()
    parts = None
    try:
        parts = _build_parts(cfg)
    except Exception as e:
        print(f"⚠ パーツ再構築に失敗、CAD 干渉解析をスキップ: {e}")
    raise SystemExit(fit_check.main(cfg=cfg, parts=parts, allowlist=ALLOWLIST))
```

shim が無ければ skill が初回生成。**既に存在する shim は上書きしない**
(ALLOWLIST など利用者編集を尊重)。

### Step 2: チェック実行

```bash
python output/design/fit_check.py
```

実行内容:

1. case-config / case-spec / objects を読み込む
2. ルールベースチェック(A-C, E)を実施
3. CAD パーツ(`output/preview/*.step`)を読み込み、`PART_PAIRS` で定義された組み合わせを閉じた位置で intersect
4. `ALLOWLIST` と照合して未許容部分を特定
5. レポート組み立て、`output/reports/fit-check.md` へ出力

### Step 3: レポート確認

```markdown
# Fit-Check Report

## サマリー
- ✅ Pass: N
- ⚠ Warning: M
- ❌ Fail: K

## A. 内寸マージン
- ✅ object_clearance: 1.5 mm (推奨 ≥ 1.0)
- ⚠ z_margin: 0.5 mm (推奨 ≥ 1.0)

## D. CAD 干渉解析
- pair: case-body × case-lid (closed)
  - 重なり総体積: 35.6 mm³
  - allowlist 合計: 50.0 mm³
  - 未許容: 0 mm³  ✅
```

### Step 4: 利用者に提示

判定:

- **❌ がある**: 印刷前に修正を推奨。`/review-fix` に戻って調整
- **⚠ のみ**: 印刷可能。ただし以下の点を確認(リスト)
- **✅ のみ**: 印刷準備 OK。`/export` に進めます

## ゲート

`/export` 前に推奨:

1. `output/reports/fit-check.md` が最新
2. ❌ がない(または利用者が明示的に「許容」を宣言)

## 物理ループ(印刷後の実測フィードバック)

本スキルは **CAD 上の検査**であり、ここを通っても**実測との差**は別途取り込む必要がある。
試作を印刷したら **物理ループ** に移る:

1. `/export` で STL/3MF を出して印刷
2. 利用者が組み立て・ノギス計測・操作確認を行う
3. `/review-fix measurements` を呼ぶと、`.claude/templates/feedback-measurements.yaml` が
   `input/feedback/<date>-measurements.yaml` にコピーされる
4. 利用者が CAD 値 vs 実測値 vs 採用補正を埋める
5. `/review-fix` がそれを `case-config.yaml` に反映 → `generator.py` 再実行 → 本スキルで再点検

詳細は `@.claude/rules/measurement-feedback.md` を参照。CAD 検査と物理検査の **両輪**で
品質を担保する設計。本体不変原則(P15)・暗黙許容禁止(P16)は物理ループでも適用。

## 注意事項

- **利用者カスタムの尊重**: `fit_check.py` を利用者が編集していたら上書きしない。チェック項目の追加は `ALLOWLIST` / `PART_PAIRS` / `MECHANISMS` への追記で対応
- **ALLOWLIST の運用**: 意図的な重なりは label・max_mm3・理由を併記して登録。「なぜ許容したか」を残す。CAD で解消したら削除し、コメントで履歴を残す
- **基準値はチューニング可能**: 推奨値は経験則ベース。プロジェクト特性で見直し可。緩める場合は理由をコメントに残す
- **拡張容易性**: 新しい嵌合機構が登場したら `MECHANISMS` 辞書に追加するだけで取り込める設計を維持
- **段階 4 と 5 の橋渡し**: review-fix では「直近フィードバック反映」、fit-check では「過去事例網羅+CAD 干渉」と役割分離
- **本体固定運用への対応**: 印刷時間が長く本体を再印刷したくない場合、本体パラメータを変えずに蓋のみ調整する余地(`lid_knuckle_extra_clearance_z` など)を残す

## 関連

- `@.claude/skills/review-fix/SKILL.md` — 段階 4 + 物理ループ反映
- `@.claude/skills/export/SKILL.md` — 段階 5
- `@.claude/skills/hinged-lid/SKILL.md` — closure=hinge_lever 時、本スキルの C/F カテゴリに固有チェックを追加する
- `@.claude/quality-gates.md` — 5 段階ゲート条件
- `@.claude/pitfalls.md` — リリーフカット忘れなどの落とし穴
- `@.claude/rules/measurement-feedback.md` — 物理ループの様式
- `@.claude/rules/materials-catalog.md` — 材料別 fit_clearance 推奨範囲
- `output/design/validator.py` — 単一パーツの設計ルール検証
- `output/design/fit_check.py` — このスキルが管理する嵌合チェック実装
