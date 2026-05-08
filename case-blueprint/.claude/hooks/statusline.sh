#!/usr/bin/env bash
# statusLine command: 現在地を 1 行で返す。
# Claude Code が定期的にこのスクリプトを呼び、stdout の 1 行を UI に表示する。
# stdin から session info の JSON が渡されるが、ここでは未使用。

set -uo pipefail

# stdin を捨てる(blocking 回避)
cat >/dev/null 2>&1 || true

PYBIN="${PYBIN:-.venv/bin/python}"
[[ ! -x "$PYBIN" ]] && PYBIN="python3"

if ! "$PYBIN" -c "import case_blueprint" 2>/dev/null; then
    echo "case-blueprint | (環境未構築: pip install -e .[dev])"
    exit 0
fi

if ! out=$("$PYBIN" -m case_blueprint.cli summary 2>/dev/null); then
    echo "case-blueprint | (state エラー)"
    exit 0
fi

echo "$out"
