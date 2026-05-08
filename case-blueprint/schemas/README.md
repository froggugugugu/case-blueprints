# schemas/ — 機械可読 YAML スキーマ

JSON-Schema(Draft 2020-12)で各 YAML の構造を検証するスキーマ群。
`src/case_blueprint/loader.py` がロード時に自動検証する。

## ファイル一覧

| ファイル | 検証対象 | 編集者 |
|---|---|---|
| `object.schema.yaml`         | `input/objects/<id>.yaml`                  | /measure |
| `case-spec.schema.yaml`      | `input/requirements/case-spec.yaml`        | /design + 人間補正 |
| `case-config.schema.yaml`    | `input/design-params/case-config.yaml`     | /design + 人間補正 |
| `project-config.schema.yaml` | `project-config.yaml`                      | 人間のみ |

## 設計方針

- **オープン構造を許容**: `case-spec.yaml` の `features[].type` や
  `case-config.yaml` の features 別パラメータブロックは
  `additionalProperties: true` で拡張可能。Claude が新 type を追加できる
- **必須項目は厳密に**: `id` の正規表現、`dimensions` の正値、`printer_bed`
  の 3 要素配列等は `required` + 制約で固定
- **機械検証 + 人間レビュー**: スキーマ違反は CI でも /lead でも検出可能。
  ただし「設計上の妥当性」(壁が薄すぎる等)は validator.py / fit_check.py
  の責務であり、スキーマでは扱わない

## 使い方(Python)

```python
from case_blueprint.loader import load_case_spec

spec = load_case_spec("input/requirements/case-spec.yaml")
# 内部でスキーマ検証 + 構造化 dict 返却。違反は ValidationError で raise
```

## 使い方(CLI)

```bash
python -m case_blueprint.cli validate-schema input/requirements/case-spec.yaml
```

## 拡張時の注意

- スキーマを変更したら `tests/test_schema.py` を更新
- features の `type` を新規追加する場合、`case-spec.schema.yaml` 側は
  そのまま(オープン)で OK。`case-config.schema.yaml` に対応キーが必要なら
  `additionalProperties` の運用で吸収する
