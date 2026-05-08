---
paths:
  - "input/**/*.yaml"
  - "project-config.yaml"
---

# YAML スタイル規約

人間と Claude が共同編集するため、可読性 > 簡潔性。

## コメント

- **値の単位を必ず併記**: `thickness: 2.4  # mm`
- **変更履歴は inline**: `fit_clearance: 0.4  # 2026-05-02 修正: 0.2 → 0.4(P14 適用)`
- **理由が長い場合は複数行コメント**: 数値だけでなく「なぜ」を残す

## 構造

- ネスト 3 段以上は避ける(深いツリーは構造設計を見直す合図)
- 配列要素はオブジェクトで `{ type: ..., ... }` 形式 or 複数行 `-` 形式に統一
- features 配列は **オープン**:type 名は文字列、enum 固定なし

## ハイブリッドゾーンの尊重

- `input/requirements/case-spec.yaml` と `input/design-params/case-config.yaml` は
  Claude 初稿 + 人間補正のハイブリッド(constitution §1)
- 利用者が直接編集した内容を Claude が **上書きしてはならない**
- 不安なら `git diff` で変更を確認してから書き換える

## スキーマ準拠

- `project-config.yaml` は `schemas/project-config.schema.yaml` に準拠(必須キー固定)
- `case-spec.yaml` は `schemas/case-spec.schema.yaml`(features はオープン構造)
- `case-config.yaml` は `schemas/case-config.schema.yaml`(features 別ブロックを許容)
- `input/objects/<id>.yaml` は `schemas/object.schema.yaml`(`id` は `^[a-z0-9][a-z0-9-]*$`)

## ファイル命名

- `input/objects/<id>.yaml` の `<id>` は `id:` フィールドと一致
- `input/feedback/<YYYY-MM-DD>.md` 形式で日付順
