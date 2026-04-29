# feedback-staging/ — 実プロジェクトのフィードバック投入領域

実際にこのテンプレートを使って作成したプロジェクトを **丸ごと放り込む** 場所です。
**Git 履歴には残らない**(`.gitignore` で除外)ため、個人情報・特定機種情報が混じっても気にせず投入できます。

---

## 使い方

```bash
# 実プロジェクトをコピー(.git, .venv, __pycache__ は除外推奨)
rsync -a --exclude='.git' --exclude='.venv' --exclude='__pycache__' \
    ~/path/to/my-real-project/ ./feedback-staging/<project-name>/

# rsync が無い場合は cp -R + 削除でも可
# cp -R ~/path/to/my-real-project ./feedback-staging/<project-name>/
# rm -rf ./feedback-staging/<project-name>/{.git,.venv,__pycache__}

# Claude を起動し、分析を依頼
claude
```

**.git を除外する理由**: 実プロジェクトの履歴は分析に不要、サイズが膨らむ、誤って Git 履歴が混乱する可能性を避ける。

Claude へのプロンプト例:

```
feedback-staging/<project-name>/ を分析して、
テンプレート(case-blueprint/)に反映すべき改善点をまとめてください。
学びは examples/<project-name>/ に整形して保存してください。
```

---

## Claude が行うこと

1. 実プロジェクトの `input/`, `output/`, `feedback/` を読む
2. 段階 1〜5 で起きた問題・学びを整理
3. 改善点を `case-blueprint/` の skill / テンプレートに反映(必要なら)
4. 試行で残しておく価値のある情報を `examples/<project-name>/` に整形して保存
5. 整形完了後、`feedback-staging/<project-name>/` は削除しても良い旨を案内

---

## このディレクトリの方針

- **`.gitignore` で除外**: 実プロジェクトのファイルは Git 履歴に残らない
- **個人情報の混入 OK**: ここで気にせず投入できる
- **整形後は削除可能**: 学びが `examples/<name>/` に抽出された後、staging を削除しても OK
- **追跡されるのはこの README だけ**: その他のファイルは全て untracked

---

## ファイル/ディレクトリの追跡可否

| パス | 追跡 |
|---|---|
| `feedback-staging/README.md`(本ファイル) | ✅ |
| `feedback-staging/<project-name>/` 配下 | ❌ |

ルート `.gitignore` のパターン:

```
/feedback-staging/*
!/feedback-staging/README.md
```
