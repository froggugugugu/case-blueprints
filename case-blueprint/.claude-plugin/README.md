# `.claude-plugin/`

このディレクトリは将来、本プロジェクトを Claude Code の **plugin として配布** したいときの受け皿です。

## 必須ではない

通常の利用(自分のケース 1 個を設計するだけ)では plugin 化は不要です。
このディレクトリを無視しても支障ありません。

## plugin 化したいとき

1. `plugin.json` の `name` / `description` / `version` を編集
2. `.claude/` 配下(skills, agents, hooks, rules)はそのまま plugin に含まれる
3. リポジトリを GitHub に push し、Claude Code の plugin marketplace に submit
4. または `claude --plugin-dir <path>` でローカル試験

## 参考

公式ドキュメント: https://code.claude.com/docs/en/plugins.md
