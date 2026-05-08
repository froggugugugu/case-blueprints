"""CLI エントリポイント。

サブコマンド:
  validate-schema <yaml-path>  -- スキーマ検証
  state                          -- /lead 用の状態 JSON 出力
  summary                        -- statusline 向け 1 行サマリ
  load-all [<root>]              -- 4 種一括ロードして dict ダンプ(デバッグ用)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _validate_schema(args: list[str]) -> int:
    if not args:
        print("Usage: python -m case_blueprint.cli validate-schema <yaml-path>", file=sys.stderr)
        return 2
    target = Path(args[0])
    if not target.exists():
        print(f"Error: {target} が存在しません", file=sys.stderr)
        return 1

    # ファイル名/パスから schema を推定
    name = target.name
    parent = target.parent.name
    if parent == "objects":
        schema = "object"
    elif name == "case-spec.yaml" or parent == "requirements":
        schema = "case-spec"
    elif name == "case-config.yaml" or parent == "design-params":
        schema = "case-config"
    elif name == "project-config.yaml":
        schema = "project-config"
    else:
        print(f"Error: {target} のスキーマを推定できません", file=sys.stderr)
        return 1

    from . import loader
    try:
        if schema == "object":
            loader.load_object(target)
        elif schema == "case-spec":
            loader.load_case_spec(target)
        elif schema == "case-config":
            loader.load_case_config(target)
        else:
            loader.load_project_config(target)
    except loader.ValidationError as e:
        print(f"❌ {target} {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"⚠ {e}", file=sys.stderr)
        return 1
    print(f"✅ {target} ({schema}.schema.yaml に準拠)")
    return 0


def _state(args: list[str]) -> int:
    del args
    from . import state as state_mod
    json.dump(state_mod.snapshot("."), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


def _summary(args: list[str]) -> int:
    del args
    from . import state as state_mod
    sys.stdout.write(state_mod.summary_line(".") + "\n")
    return 0


def _load_all(args: list[str]) -> int:
    root = args[0] if args else "."
    from . import loader
    try:
        data = loader.load_all(root)
    except (loader.ValidationError, FileNotFoundError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    print(json.dumps(
        {
            "objects_count": len(data["objects"]),
            "case_name": data["case_spec"]["case"]["name"],
            "closure_method": data["case_spec"]["case"]["closure"]["method"],
            "printer_bed": data["project"]["print_settings"]["printer_bed"],
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


COMMANDS = {
    "validate-schema": _validate_schema,
    "state": _state,
    "summary": _summary,
    "load-all": _load_all,
}


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__, file=sys.stderr)
        return 0
    cmd, *rest = argv
    handler = COMMANDS.get(cmd)
    if handler is None:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(f"Available: {', '.join(COMMANDS)}", file=sys.stderr)
        return 2
    return handler(rest)


if __name__ == "__main__":
    sys.exit(main())
