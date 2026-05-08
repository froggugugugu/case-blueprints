#!/usr/bin/env bash
# PreToolUse hook: 危険な状態のまま print 段に進むのを実ブロックする。
# - output/print/ への Write|Edit 直前に validation/fit-check に ❌ が残っていれば exit 2
# - validation.md が無い(設計未確定)なら exit 2
#
# 通常の Write|Edit は pass-through。判定対象外なら exit 0 で素通し。

set -uo pipefail

INPUT=$(cat)

# tool_input.file_path を抜き取る(jq 非依存)
file_path=$(echo "$INPUT" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    fp = d.get("tool_input", {}).get("file_path") or d.get("tool_input", {}).get("path", "")
    print(fp)
except Exception:
    pass
')

[[ -z "$file_path" ]] && exit 0

# output/print/ への書き込みのみ検査(他は素通し)
case "$file_path" in
    *output/print/*) ;;
    *) exit 0 ;;
esac

# slicer-notes.md は report 系なので、設計確定後の更新を許す。
# 検査対象は STL/3MF/STEP 等の派生バイナリ。
case "$file_path" in
    *.stl|*.STL|*.3mf|*.3MF|*.step|*.STEP|*.gcode|*.GCODE) ;;
    *) exit 0 ;;
esac

reasons=()

if [[ ! -f output/reports/validation.md ]]; then
    reasons+=("validation.md が無い(/design 未実行)")
elif grep -q '^- ❌' output/reports/validation.md 2>/dev/null; then
    n=$(grep -c '^- ❌' output/reports/validation.md)
    reasons+=("validation.md に ${n} 件の ❌ が残存")
fi

if [[ -f output/reports/fit-check.md ]]; then
    if grep -q '❌' output/reports/fit-check.md 2>/dev/null; then
        reasons+=("fit-check.md に ❌ が残存")
    fi
fi

if [[ ${#reasons[@]} -eq 0 ]]; then
    exit 0
fi

joined=$(printf '%s; ' "${reasons[@]}")
joined=${joined%; }

# exit 2 で本気ブロック(Claude Code 仕様: stderr が Claude に表示される)
echo "🚫 output/print/ への ${file_path##*/} 書き込みをブロック: ${joined}" >&2
echo "対処: /review-fix で ❌ を解消し、/fit-check で確認してから /export を呼び直してください。" >&2
exit 2
