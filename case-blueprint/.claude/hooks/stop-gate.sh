#!/usr/bin/env bash
# Stop hook: ターン終了時に validator/fit-check で ❌ が残っていれば警告。
# 利用者が認知できるよう additionalContext で出力。block はしない。

set -uo pipefail

warnings=()

if [[ -f output/reports/validation.md ]]; then
    if grep -q '^- ❌' output/reports/validation.md 2>/dev/null; then
        fails=$(grep -c '^- ❌' output/reports/validation.md)
        warnings+=("validator: ${fails} 件の ❌ が残存(output/reports/validation.md を参照)")
    fi
fi

if [[ -f output/reports/fit-check.md ]]; then
    if grep -q '❌' output/reports/fit-check.md 2>/dev/null; then
        warnings+=("fit-check: ❌ が残存(output/reports/fit-check.md を参照)。/review-fix で対応推奨")
    fi
fi

if [[ ${#warnings[@]} -eq 0 ]]; then
    exit 0
fi

joined=$(printf '%s\n' "${warnings[@]}")
cat <<EOF
{
  "hookSpecificOutput": {
    "additionalContext": "⚠ Stop ゲート警告:\n${joined//$'\n'/\\n}"
  }
}
EOF
