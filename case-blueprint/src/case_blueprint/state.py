"""/lead 用の現在地スナップショット。

`python -m case_blueprint.state` で JSON を stdout に吐く。
/lead skill はこの JSON を読んで状態判定する(Glob/Read を毎回撃つより一貫)。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


def _exists(p: Path) -> bool:
    return p.exists()


def _mtime(p: Path) -> float | None:
    try:
        return p.stat().st_mtime
    except FileNotFoundError:
        return None


def _newer(a: Path, b: Path) -> bool | None:
    """a が b より新しいか。両方無ければ None。"""
    ma, mb = _mtime(a), _mtime(b)
    if ma is None or mb is None:
        return None
    return ma > mb


def _read_yaml_keys(p: Path, *keys: str) -> Any:
    """簡易 YAML 読み(yaml が無い環境でも動くフォールバックを持つ)"""
    try:
        import yaml  # type: ignore
    except ImportError:
        return None
    try:
        with p.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        return None
    cur = data
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def snapshot(root: str | os.PathLike[str] = ".") -> dict[str, Any]:
    r = Path(root)
    objects = sorted(p.name for p in (r / "input/objects").glob("*.yaml"))
    feedback = sorted(p.name for p in (r / "input/feedback").glob("*.md"))

    spec_path = r / "input/requirements/case-spec.yaml"
    cfg_path = r / "input/design-params/case-config.yaml"
    gen_path = r / "output/design/generator.py"
    val_py_path = r / "output/design/validator.py"
    fit_py_path = r / "output/design/fit_check.py"
    preview_step = r / "output/preview/case-body.step"
    val_md = r / "output/reports/validation.md"
    fit_md = r / "output/reports/fit-check.md"
    print_3mf = sorted(p.name for p in (r / "output/print").glob("*.3mf"))
    slicer_notes = r / "output/print/slicer-notes.md"

    closure_method = _read_yaml_keys(spec_path, "case", "closure", "method")

    return {
        "stage_1_measure": {
            "objects_count": len(objects),
            "objects": objects,
        },
        "project_config": {
            "exists": _exists(r / "project-config.yaml"),
        },
        "stage_2_requirements": {
            "case_spec_exists": _exists(spec_path),
            "closure_method": closure_method,
        },
        "stage_2_3_params": {
            "case_config_exists": _exists(cfg_path),
        },
        "stage_3_design": {
            "generator_exists": _exists(gen_path),
            "validator_exists": _exists(val_py_path),
            "preview_up_to_date": _newer(preview_step, gen_path),
        },
        "stage_3_validation": {
            "report_exists": _exists(val_md),
            "report_up_to_date": _newer(val_md, gen_path),
        },
        "stage_4_5_fit_check": {
            "script_exists": _exists(fit_py_path),
            "report_exists": _exists(fit_md),
            "report_up_to_date": _newer(fit_md, gen_path),
        },
        "stage_5_export": {
            "print_files": print_3mf,
            "slicer_notes_exists": _exists(slicer_notes),
        },
        "feedback": {
            "files": feedback,
            "latest": feedback[-1] if feedback else None,
        },
        "horizontal_hinged_lid_applicable": closure_method == "hinge_lever",
    }


def _count_marks(path: Path) -> tuple[int, int] | None:
    """md レポートの ✅/❌ をカウント。無ければ None。"""
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return None
    return text.count("✅"), text.count("❌")


def summary_line(root: str | os.PathLike[str] = ".") -> str:
    """statusline 向け 1 行サマリ。「いまどの段階・どこに ❌ があるか」を端的に返す。"""
    r = Path(root)
    snap = snapshot(r)

    has_print = bool(snap["stage_5_export"]["print_files"])
    has_gen = snap["stage_3_design"]["generator_exists"]
    spec_exists = snap["stage_2_requirements"]["case_spec_exists"]
    objects_n = snap["stage_1_measure"]["objects_count"]

    val_status = _count_marks(r / "output/reports/validation.md")
    fit_status = _count_marks(r / "output/reports/fit-check.md")

    if has_print:
        stage = "5:export"
    elif fit_status and fit_status[1] == 0 and val_status and val_status[1] == 0:
        stage = "4-5:fit ✓"
    elif has_gen:
        stage = "3:design"
    elif spec_exists:
        stage = "2:spec"
    elif objects_n > 0:
        stage = "1:measure"
    else:
        stage = "0:start"

    parts: list[str] = [f"📐 {stage}"]
    if objects_n:
        parts.append(f"obj:{objects_n}")
    if val_status:
        p, f = val_status
        parts.append(f"val:❌{f}" if f else f"val:✓{p}")
    if fit_status:
        p, f = fit_status
        parts.append(f"fit:❌{f}" if f else "fit:✓")
    closure = snap["stage_2_requirements"]["closure_method"]
    if closure:
        parts.append(f"closure:{closure}")
    return " | ".join(parts)


def main() -> int:
    json.dump(snapshot("."), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
