# minimal — 最小ケース例

`case-blueprint` テンプレートで生成可能な最小構成の動作例。

- **オブジェクト 1 個**(直方体 80 × 50 × 20 mm)
- **closure: snap_fit**(蓋付き箱、最も単純)
- **features 1 つ**(ventilation のみ)

## 何のための例か

- `setup.sh` でテンプレートを展開した直後の状態を、利用者が「動く形」で確認できる
- スキーマ検証 / loader / geometry / state スナップショットの最小入力例
- `/measure` `/design` を通したらどんな YAML になるかの参考

## 構成

```
examples/minimal/
├── README.md
├── project-config.yaml                         # プリンタ・材料設定
├── input/
│   ├── objects/sample-device.yaml              # /measure 出力例
│   ├── requirements/case-spec.yaml             # /design 出力例(段階 2)
│   └── design-params/case-config.yaml          # /design 出力例(段階 3)
└── output/
    └── (空 — 利用者プロジェクトで生成される)
```

## 試し方

```bash
# このリポをチェックアウトして minimal を試す
cd examples/minimal

# スキーマ検証(generator/validator は無いが、入力 YAML の妥当性は確認できる)
python -m case_blueprint.cli validate-schema input/objects/sample-device.yaml
python -m case_blueprint.cli validate-schema input/requirements/case-spec.yaml
python -m case_blueprint.cli validate-schema input/design-params/case-config.yaml
python -m case_blueprint.cli validate-schema project-config.yaml

# 状態スナップショット
python -m case_blueprint.cli state
```

## 学べること

- input ディレクトリ構造の最小形
- features がオープン構造であること(`type: ventilation` を増やせば `feature_registry.register("ventilation")` のハンドラが呼ばれる)
- 「何もない」状態から `/lead` を呼んだ時の状態判定の入力
