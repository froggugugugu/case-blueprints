---
paths:
  - "output/design/**/*.py"
---

# CAD ソース規約(generator.py / validator.py / fit_check.py)

CadQuery 実装時に守るルール。

## モジュール構造

- `generator.py` は単体実行可能(`python output/design/generator.py`)
- 主要関数を分離: `load_configs() / calculate_internal_dimensions() / build_case_body() / build_lid() / apply_features()`
- 共通実装は `case_blueprint.*` から import(loader, geometry, exporter, feature_registry, validators, closures)

## features dispatcher

- `feature_registry.register("type名")` デコレータでハンドラ登録
- 未登録 type が現れたら警告 print + 素通し(再現性のため)
- 新 type は generator.py 内に追加(SKILL.md /design の方針に従う)

## closure dispatcher

- `closures.register("method名")` で登録
- `hinge_lever` は `case_blueprint.closures.hinge_lever` をインポートすれば自動登録

## validator のスタイル

- `@check("人間に読める名前")` decorator
- 失敗は `assert` で表現(理由を式に含める)
- 副作用なし(状態変更しない)

## 印刷向きの physical bake

- `print_orientation` を読み、`generator.py` で物理的に回転して STEP/STL 出力
- スライサーで再配置不要にする

## 禁則

- `from cadquery import *` のような wildcard import は禁止(`import cadquery as cq` で固定)
- バイナリ(STEP/STL/3MF)を上流(input/)に書き戻すコード禁止(constitution §2)
- 利用者直接編集ゾーン(input/)を書き換えるコードは generator/validator/fit_check には書かない
