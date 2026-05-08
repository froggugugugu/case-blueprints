#!/usr/bin/env bash
# SubagentStop hook: subagent 完了時の監査ログを output/reports/_audit.jsonl に追記。
# CAD は再現性が命なので、どの判断がどの subagent context でなされたかを後で追える状態にする。

set -uo pipefail

INPUT=$(cat)

mkdir -p output/reports 2>/dev/null || true

echo "$INPUT" | python3 -c '
import json, sys, datetime
try:
    d = json.load(sys.stdin)
    rec = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "event": d.get("hook_event_name", "SubagentStop"),
        "session_id": d.get("session_id"),
        "agent_id": d.get("agent_id"),
        "agent_name": d.get("agent_name"),
        "cwd": d.get("cwd"),
    }
    print(json.dumps(rec, ensure_ascii=False))
except Exception:
    sys.exit(0)
' >> output/reports/_audit.jsonl 2>/dev/null || true

exit 0
