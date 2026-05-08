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


def main() -> int:
    json.dump(snapshot("."), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
