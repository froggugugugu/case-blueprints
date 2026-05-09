#!/usr/bin/env bash
# case-blueprint/setup.sh
# Initialize a new 3D-printable case design project from this template.

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: bash case-blueprint/setup.sh <target-dir>

case-blueprint/ の中身を <target-dir> に展開し、
3D プリント可能なケース設計プロジェクトを初期化します。

Arguments:
  <target-dir>   作成するプロジェクトのディレクトリパス(存在しないこと)

Example:
  bash case-blueprint/setup.sh ./my-router-case
EOF
}

if [[ $# -ne 1 || "$1" == "-h" || "$1" == "--help" ]]; then
    usage
    [[ $# -eq 1 && ( "$1" == "-h" || "$1" == "--help" ) ]] && exit 0
    exit 1
fi

TARGET="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 既存ディレクトリの許容: 空 or .git のみ、または .git + LICENSE のみ
# (GitHub UI で「Add a license」した clone 直後の状態に対応)
if [[ -e "$TARGET" ]]; then
    if [[ ! -d "$TARGET" ]]; then
        echo "Error: $TARGET はディレクトリではありません。" >&2
        exit 1
    fi
    unexpected=$(find "$TARGET" -mindepth 1 -maxdepth 1 \
        -not -name '.git' \
        -not -name 'LICENSE' | wc -l | tr -d ' ')
    if [[ "$unexpected" -gt 0 ]]; then
        echo "Error: $TARGET に予期しないファイルがあります(.git と LICENSE 以外)。" >&2
        echo "  GitHub UI でリポジトリを作成する場合、'Add a license' のみ選択してください。" >&2
        echo "  README や .gitignore は追加しないでください(setup.sh が用意します)。" >&2
        exit 1
    fi
    [[ -f "$TARGET/LICENSE" ]] && echo "Note: 既存の LICENSE を保持します"
fi

# Create target directory if not exists
mkdir -p "$TARGET"

# LICENSE を保持するためコピー前にバックアップ
LICENSE_BACKUP=""
if [[ -f "$TARGET/LICENSE" ]]; then
    LICENSE_BACKUP=$(mktemp)
    cp "$TARGET/LICENSE" "$LICENSE_BACKUP"
fi

# Copy everything from case-blueprint/ to target
cp -R "$SCRIPT_DIR/." "$TARGET/"

# Remove setup.sh itself from target (template should not include the installer)
rm -f "$TARGET/setup.sh"

# Strip Python build artifacts that may have been generated during testing
find "$TARGET" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
find "$TARGET" -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
find "$TARGET" -type d -name '.ruff_cache' -exec rm -rf {} + 2>/dev/null || true

# Restore LICENSE if it was preserved
if [[ -n "$LICENSE_BACKUP" ]]; then
    mv "$LICENSE_BACKUP" "$TARGET/LICENSE"
fi

# Expand .template files: foo.ext.template -> foo.ext
find "$TARGET" -type f -name '*.template' | while IFS= read -r tmpl; do
    expanded="${tmpl%.template}"
    mv "$tmpl" "$expanded"
done

cat <<EOF

✓ プロジェクトを $TARGET に初期化しました。

次のステップ:
  cd $TARGET
  claude     # Claude Code を起動

起動後、以下のプロンプトを順に投げると /lead まで到達します:

  ① 環境構築:
     project-config.yaml を埋めて、Python 環境の構築(venv + pip install -e .)と
     git 初期化までお願いします。プリンタは <機種>(造形 <X×Y×Z mm>、
     ノズル <径> mm)、材料は <PETG / PLA など> をメインに使います。

  ② プロジェクト開始:
     /lead

skill 早見表:
  /lead         進行管理(現在地と次の一手を提示、初心者はこれだけで OK)
  /measure      オブジェクトの採寸(URL や実測値を貼る)
  /design       設計仕様統合 + CadQuery 生成
  /review-fix   STEP/STL を見たフィードバック反映(ループ)
  /fit-check    嵌合・干渉点検
  /export       最終 STL/3MF 出力

横断スキル(段階に属さず、必要なときに呼ぶ):
  /hinged-lid   蓋がヒンジで開閉する「ヒンジ蓋ケース」を作るとき。
                /design で closure.method = hinge_lever を選んだ後に
                /hinged-lid init で蝶番・レバーラッチ・ピンの詳細を埋める。
                通常の snap_fit / screws / magnetic 等のケースでは不要。
  /style        意匠(未来感 / ミニマル / ファンシー / 角の処理 / 表面パターン)を
                /style theme <name> で指定。/design 前後どちらでも呼べる。

すぐ動く参照を見たい場合は claude 起動前に:
  cp -R examples/minimal/input/. input/         # snap_fit 名刺ケース(最小)
  cp -R examples/bike-navi-mvp/input/. input/   # features 7 種の総合例
EOF
