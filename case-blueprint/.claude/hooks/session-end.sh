#!/usr/bin/env bash
# SessionEnd hook: セッションの最終状態を output/reports/session-<YYYY-MM-DD>.md に追記。
# その日の作業の流れを後から追えるようにする(再現性確保)。

set -uo pipefail

INPUT=$(cat)

PYBIN="${PYBIN:-.venv/bin/python}"
[[ ! -x "$PYBIN" ]] && PYBIN="python3"

mkdir -p output/reports 2>/dev/null || true
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M:%S)
TARGET="output/reports/session-${DATE}.md"

# 1 行サマリ
summary=""
if "$PYBIN" -c "import case_blueprint" 2>/dev/null; then
    summary=$("$PYBIN" -m case_blueprint.cli summary 2>/dev/null || true)
fi

# session_id 抽出
session_id=$(echo "$INPUT" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get("session_id", "?"))
except Exception:
    print("?")
')

{
    if [[ ! -f "$TARGET" ]]; then
        echo "# Session log — ${DATE}"
        echo ""
    fi
    echo "## ${TIME} (session: ${session_id})"
    [[ -n "$summary" ]] && echo "- 終了時の現在地: \`${summary}\`"
    echo ""
} >> "$TARGET"

exit 0
