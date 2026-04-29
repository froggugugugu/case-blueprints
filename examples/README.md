# examples/ — 完成例ショーケース

このテンプレートを使って実際に作ったケースの完成例を蓄積する場所です。**コピー対象ではありません** — 利用者が「自分のケースに似た例」を探すための読み物です。

🚧 最初は空。`feedback-staging/` 経由で実プロジェクトの学びが整形されて並びます。

---

## 各 `examples/<name>/` の構成

| ファイル | 内容 |
|---|---|
| `README.md` | 設計の経緯・学び・つまずきポイント |
| `final-case-spec.yaml` | 確定した case-spec(オブジェクト・features) |
| `final-case-config.yaml` | 確定した case-config(壁厚・嵌合等) |
| `feedback-summary.md` | 段階 4 のループで何を直したか |
| `photos/` | 試作プリント写真(任意) |

---

## 取り込みフロー

実プロジェクトは [`feedback-staging/`](../feedback-staging/README.md) 経由で取り込まれます:

```
実プロジェクト → feedback-staging/<name>/ → Claude が分析 → examples/<name>/
```

`feedback-staging/` は Git 追跡外なので、個人情報が混じっても安心。整形後に学びだけが `examples/` に残ります。
