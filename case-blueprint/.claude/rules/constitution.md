# 不変原則(プロジェクト固定)

このファイルは利用者プロジェクトに `setup.sh` で展開され、CLAUDE.md から
`@` import される。**変更禁止**。

---

## 1. 人間と AI の責務分離

- **人間管理**: `input/objects/`, `input/design-params/`, `input/feedback/`
- **AI 管理**: `output/design/`, `output/preview/`, `output/print/`, `output/reports/`
- **ハイブリッド**: `input/requirements/case-spec.yaml`(Claude 初稿+人間補正)

## 2. テキスト中心とソース・オブ・トゥルース

- 真実は CadQuery (Python) + YAML
- バイナリ(STEP/STL/3MF)は派生物。逆流させない

## 3. L2 ワークフロー

- 利用者は CadQuery を読まなくて良い
- 寸法調整は `case-config.yaml` 直接編集
- 構造変更や曖昧な要望は `input/feedback/<date>.md` に自然言語で

## 4. 5 段階ゲート + 横断スキル

- 段階: measure → design → review-fix → fit-check → export
- ゲートを削減しない。全自動化禁止
- 進行管理: `/lead`(PdM 相当)
- 機構特化: `/hinged-lid` 等の横断スキル

## 5. テンプレート境界

- このプロジェクトは `case-blueprints` テンプレートから生成された
- 元テンプレートに利用者プロジェクト固有の判断を持ち込まない
