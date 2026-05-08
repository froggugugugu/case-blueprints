#!/usr/bin/env bash
# SessionStart hook: 起動時に YAML スキーマを検証して状況を additionalContext で渡す。
# 失敗しても block しない(警告のみ、JSON で additionalContext 出力)。

set -uo pipefail

PYBIN="${PYBIN:-.venv/bin/python}"
[[ ! -x "$PYBIN" ]] && PYBIN="python3"

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

# 主要 YAML を検証
check_one "project-config.yaml"
check_one "input/requirements/case-spec.yaml"
check_one "input/design-params/case-config.yaml"
for obj in input/objects/*.yaml; do
    [[ -f "$obj" ]] || continue
    check_one "$obj"
done

if [[ ${#result_lines[@]} -eq 0 ]]; then
    additional="(YAML 未配置:setup 直後の状態)"
else
    additional=$(printf '%s\n' "${result_lines[@]}")
fi

cat <<EOF
{
  "hookSpecificOutput": {
    "additionalContext": "## SessionStart スキーマ検証\n${additional//$'\n'/\\n}\n\nfail=${fail_count}"
  }
}
EOF
