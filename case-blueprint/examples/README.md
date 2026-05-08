# examples — テンプレート同梱の動く参照例

`setup.sh` で展開された **利用者プロジェクト側** に同梱される最小サンプル群です。
コピーするだけで `/design` から試せる入力一式が入っています。

## 一覧

| サンプル | closure | 用途 |
|---|---|---|
| [`minimal/`](minimal/README.md) | `snap_fit` | 名刺ケース 1 部品オブジェクト、最小構成 |
| [`bike-navi-mvp/`](bike-navi-mvp/README.md) | `screws` + heat-set + ガスケット | バイクナビ統合ケース。features 7 種、屋外・車載・振動対策の総合参照 |

## 使い方

各サンプルの `input/` をプロジェクト直下の `input/` にコピーします:

```bash
cp -R examples/<sample>/input/. input/
```

その後 `/design` 以降を回します。詳細は各サンプルの README を参照。

## リポトップの `examples/` との違い

- リポトップ(`case-blueprints/examples/`):リポ保守者向けの **完成例ショーケース**。
  テンプレートにはコピーされない
- ここ(`case-blueprint/examples/`):**テンプレート同梱**、利用者プロジェクトに
  そのままコピーされ、`/design` から試せる動く参照例
