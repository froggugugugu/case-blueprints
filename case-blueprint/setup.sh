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

if [[ -e "$TARGET" ]]; then
    echo "Error: $TARGET は既に存在します。別のパスを指定してください。" >&2
    exit 1
fi

# Create target directory
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
