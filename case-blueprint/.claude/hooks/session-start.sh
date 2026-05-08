#!/usr/bin/env bash
# SessionStart hook: 起動時に
#   (1) YAML スキーマを検証
#   (2) state.py の 1 行サマリ(現在地)を取得
#   (3) CLAUDE.md の 200 行縛りをチェック
# し、まとめて additionalContext で Claude に渡す。
# 失敗してもブロックしない(警告のみ、JSON で additionalContext 出力)。

set -uo pipefail

PYBIN="${PYBIN:-.venv/bin/python}"
[[ ! -x "$PYBIN" ]] && PYBIN="python3"

# ----- (1) YAML スキーマ検証 -----
result_lines=()
fail_count=0

check_one() {
    local path="$1"
    [[ ! -f "$path" ]] && return 0
    if out=$("$PYBIN" -m case_blueprint.cli validate-schema "$path" 2>&1); then
        result_lines+=("✅ $path")
    else
        result_lines+=("❌ $path: ${out//$'\n'/ }")
        fail_count=$((fail_count + 1))
    fi
}

check_one "project-config.yaml"
check_one "input/requirements/case-spec.yaml"
check_one "input/design-params/case-config.yaml"
for obj in input/objects/*.yaml; do
    [[ -f "$obj" ]] || continue
    check_one "$obj"
done

if [[ ${#result_lines[@]} -eq 0 ]]; then
    schema_block="(YAML 未配置:setup 直後の状態)"
else
    schema_block=$(printf '%s\n' "${result_lines[@]}")
fi

# ----- (2) state summary -----
summary_line=""
if "$PYBIN" -c "import case_blueprint" 2>/dev/null; then
    summary_line=$("$PYBIN" -m case_blueprint.cli summary 2>/dev/null || true)
fi

# ----- (3) CLAUDE.md 200 行縛り -----
md_warning=""
if [[ -f CLAUDE.md ]]; then
    n=$(wc -l <CLAUDE.md | tr -d ' ')
    if (( n > 200 )); then
        md_warning="⚠ CLAUDE.md=${n} 行(目安 200 行超過)。.claude/rules/ や docs/ への切り出しを検討してください。"
    fi
fi

# ----- まとめて出力 -----
{
    echo "## SessionStart"
    [[ -n "$summary_line" ]] && echo "現在地: ${summary_line}"
    echo ""
    echo "### スキーマ検証"
    echo "${schema_block}"
    echo "fail=${fail_count}"
    [[ -n "$md_warning" ]] && { echo ""; echo "${md_warning}"; }
} | python3 -c '
import json, sys
text = sys.stdin.read()
out = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}
json.dump(out, sys.stdout, ensure_ascii=False)
'
