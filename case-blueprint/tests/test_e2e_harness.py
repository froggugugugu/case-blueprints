"""harness 自身の E2E テスト — setup.sh で展開しても動作することを保証する。

利用者プロジェクトを実際に tmp dir に展開して:
  - 期待通りのファイル構成になる
  - hooks が実行可能
  - closures が 5 種類登録される
  - state.summary_line() / CLI `summary` が動く
を確認する。テンプレ更新で利用者プロジェクトを壊さないための保険。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

TEMPLATE_ROOT = Path(__file__).resolve().parent.parent  # case-blueprint/
SETUP_SH = TEMPLATE_ROOT / "setup.sh"


@pytest.fixture
def expanded_project(tmp_path: Path) -> Path:
    """setup.sh で利用者プロジェクトを tmp_path 配下に展開する。"""
    target = tmp_path / "my-project"
    result = subprocess.run(
        ["bash", str(SETUP_SH), str(target)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"setup.sh failed (rc={result.returncode})\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    return target


def test_setup_creates_expected_structure(expanded_project: Path):
    p = expanded_project

    # コア
    assert (p / "CLAUDE.md").exists()
    assert (p / "project-config.yaml").exists()
    assert (p / "pyproject.toml").exists()
    assert (p / ".gitignore").exists()

    # .claude/ skill / rule / hook / agent
    for skill in ("lead", "measure", "design", "review-fix", "fit-check", "export", "hinged-lid"):
        assert (p / f".claude/skills/{skill}/SKILL.md").exists(), f"missing skill: {skill}"
    for rule in ("constitution", "cad-conventions", "yaml-style", "print-safety",
                 "closures-catalog", "features-catalog", "hardware-catalog", "report-style"):
        assert (p / f".claude/rules/{rule}.md").exists(), f"missing rule: {rule}"
    for hook in ("session-start", "session-end", "stop-gate", "pre-tool-guard",
                 "post-edit-validate", "subagent-stop", "statusline"):
        assert (p / f".claude/hooks/{hook}.sh").exists(), f"missing hook: {hook}"
    for agent in ("cad-validator", "slicer-advisor"):
        assert (p / f".claude/agents/{agent}.md").exists(), f"missing agent: {agent}"

    # settings.json
    assert (p / ".claude/settings.json").exists()

    # plugin / mcp 雛形
    assert (p / ".claude-plugin/plugin.json").exists()
    assert (p / ".mcp.json").exists()

    # setup.sh は target に残らない
    assert not (p / "setup.sh").exists()

    # .template 拡張子が残っていない
    leftover = list(p.rglob("*.template"))
    assert not leftover, f"unexpanded templates: {leftover}"


def test_hooks_are_executable(expanded_project: Path):
    p = expanded_project
    for h in ("session-start.sh", "session-end.sh", "stop-gate.sh",
              "pre-tool-guard.sh", "post-edit-validate.sh",
              "subagent-stop.sh", "statusline.sh"):
        path = p / ".claude/hooks" / h
        assert path.exists(), f"missing: {h}"
        assert os.access(path, os.X_OK), f"not executable: {h}"


def test_settings_json_includes_new_hooks(expanded_project: Path):
    """settings.json に PreToolUse / SubagentStop / SessionEnd / statusLine が組み込まれている。"""
    text = (expanded_project / ".claude/settings.json").read_text()
    assert "PreToolUse" in text
    assert "SubagentStop" in text
    assert "SessionEnd" in text
    assert "statusLine" in text
    assert "pre-tool-guard.sh" in text


def test_closures_all_registered():
    """closures パッケージを import すると 5 種類の method が CLOSURE_HANDLERS に乗る。"""
    from case_blueprint import closures
    methods = set(closures.registered_methods())
    expected = {"snap_fit", "screws", "magnetic", "hinge_lever", "snap_lip_with_hinge"}
    assert expected.issubset(methods), f"missing: {expected - methods}"


def test_state_summary_empty_dir(tmp_path: Path):
    from case_blueprint import state
    line = state.summary_line(tmp_path)
    assert "0:start" in line
    assert "📐" in line


def test_state_summary_with_objects(tmp_path: Path):
    (tmp_path / "input/objects").mkdir(parents=True)
    (tmp_path / "input/objects/foo.yaml").write_text("id: foo\n")
    from case_blueprint import state
    line = state.summary_line(tmp_path)
    assert "1:measure" in line
    assert "obj:1" in line


def test_cli_summary_runs_in_expanded_project(expanded_project: Path):
    """利用者プロジェクト直下で `python -m case_blueprint.cli summary` が動く。"""
    src_path = expanded_project / "src"
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env.get('PYTHONPATH', '')}"
    result = subprocess.run(
        [sys.executable, "-m", "case_blueprint.cli", "summary"],
        cwd=expanded_project,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert "📐" in result.stdout


def test_cli_state_runs_in_expanded_project(expanded_project: Path):
    src_path = expanded_project / "src"
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env.get('PYTHONPATH', '')}"
    result = subprocess.run(
        [sys.executable, "-m", "case_blueprint.cli", "state"],
        cwd=expanded_project,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    import json
    snap = json.loads(result.stdout)
    assert "stage_1_measure" in snap
    assert snap["stage_1_measure"]["objects_count"] == 0


def test_pre_tool_guard_blocks_print_without_validation(expanded_project: Path):
    """validation.md が無い状態で output/print/x.stl への Write を試みると exit 2 を返す。"""
    p = expanded_project
    hook = p / ".claude/hooks/pre-tool-guard.sh"
    payload = (
        '{"tool_input": {"file_path": "output/print/case-body.stl"}, '
        '"hook_event_name": "PreToolUse"}'
    )
    result = subprocess.run(
        ["bash", str(hook)],
        input=payload,
        capture_output=True,
        text=True,
        cwd=p,
    )
    assert result.returncode == 2, (
        f"expected exit 2 (block), got {result.returncode}; stderr: {result.stderr}"
    )
    assert "🚫" in result.stderr or "ブロック" in result.stderr


def test_pre_tool_guard_allows_other_writes(expanded_project: Path):
    """output/print/ 配下でなければ素通し(exit 0)。"""
    p = expanded_project
    hook = p / ".claude/hooks/pre-tool-guard.sh"
    payload = (
        '{"tool_input": {"file_path": "input/objects/foo.yaml"}, '
        '"hook_event_name": "PreToolUse"}'
    )
    result = subprocess.run(
        ["bash", str(hook)],
        input=payload,
        capture_output=True,
        text=True,
        cwd=p,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"


def test_pre_tool_guard_allows_print_when_validation_passes(expanded_project: Path):
    """validation.md が ❌ 0 の状態なら output/print/x.stl 書き込みを許容。"""
    p = expanded_project
    (p / "output/reports").mkdir(parents=True, exist_ok=True)
    (p / "output/reports/validation.md").write_text(
        "# Validation Report\n\n- Pass: 14\n- Fail: 0\n\n- ✅ all good\n"
    )
    hook = p / ".claude/hooks/pre-tool-guard.sh"
    payload = (
        '{"tool_input": {"file_path": "output/print/case-body.stl"}, '
        '"hook_event_name": "PreToolUse"}'
    )
    result = subprocess.run(
        ["bash", str(hook)],
        input=payload,
        capture_output=True,
        text=True,
        cwd=p,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
