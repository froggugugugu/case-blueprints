#!/usr/bin/env bash
# PostToolUse hook (Write|Edit): 編集対象が input/ 配下の YAML なら
# スキーマ検証、output/design/*.py なら validator を再実行。

set -uo pipefail

# stdin から JSON を読む(tool_input 等)
INPUT=$(cat)

# tool_input.file_path を抜き取る(jq が無い環境向け)
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

PYBIN="${PYBIN:-.venv/bin/python}"
[[ ! -x "$PYBIN" ]] && PYBIN="python3"

# input/ 配下の YAML → スキーマ検証
if [[ "$file_path" == *.yaml && ( "$file_path" == */input/* || "$file_path" == "project-config.yaml" ) ]]; then
    if ! out=$("$PYBIN" -m case_blueprint.cli validate-schema "$file_path" 2>&1); then
        cat <<EOF
{
  "hookSpecificOutput": {
    "additionalContext": "⚠ スキーマ検証失敗: ${out//$'\n'/ }"
  }
}
EOF
    fi
    exit 0
fi

# output/design/*.py → validator 再実行
if [[ "$file_path" == */output/design/*.py ]]; then
    if [[ -f output/design/validator.py ]]; then
        if ! out=$("$PYBIN" output/design/validator.py 2>&1 | tail -20); then
            cat <<EOF
{
  "hookSpecificOutput": {
    "additionalContext": "⚠ validator.py の実行で警告: ${out//$'\n'/ }"
  }
}
EOF
        fi
    fi
fi

exit 0
