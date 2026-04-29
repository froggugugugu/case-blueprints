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

# 既存ディレクトリの許容: 空 or .git のみ なら展開可
# (GitHub clone 直後など .git だけある状態で利用するケースに対応)
if [[ -e "$TARGET" ]]; then
    if [[ ! -d "$TARGET" ]]; then
        echo "Error: $TARGET はディレクトリではありません。" >&2
        exit 1
    fi
    count=$(find "$TARGET" -mindepth 1 -maxdepth 1 -not -name '.git' | wc -l | tr -d ' ')
    if [[ "$count" -gt 0 ]]; then
        echo "Error: $TARGET は空ではありません(.git を除く)。" >&2
        echo "  既存ファイルを移動するか、別のパスを指定してください。" >&2
        exit 1
    fi
    echo "Note: 既存ディレクトリ $TARGET に展開します(.git があれば保持)"
fi

# Create target directory if not exists
mkdir -p "$TARGET"

# Copy everything from case-blueprint/ to target
cp -R "$SCRIPT_DIR/." "$TARGET/"

# Remove setup.sh itself from target (template should not include the installer)
rm -f "$TARGET/setup.sh"

# Expand .template files: foo.ext.template -> foo.ext
find "$TARGET" -type f -name '*.template' | while IFS= read -r tmpl; do
    expanded="${tmpl%.template}"
    mv "$tmpl" "$expanded"
done

cat <<EOF

✓ プロジェクトを $TARGET に初期化しました。

次のステップ:
  cd $TARGET
  \$EDITOR project-config.yaml          # プリンタ機種・材料を記入
  python -m venv .venv && source .venv/bin/activate
  pip install -e ".[dev]"               # cadquery + pytest + ruff
  claude                                 # → /measure オブジェクトを採寸
EOF
