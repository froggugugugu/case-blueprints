from __future__ import annotations

from pathlib import Path

from case_blueprint import state


def test_snapshot_empty_dir(tmp_path: Path):
    snap = state.snapshot(tmp_path)
    assert snap["stage_1_measure"]["objects_count"] == 0
    assert snap["project_config"]["exists"] is False
    assert snap["stage_2_requirements"]["case_spec_exists"] is False
    assert snap["horizontal_hinged_lid_applicable"] is False


def test_snapshot_with_objects(tmp_path: Path):
    (tmp_path / "input/objects").mkdir(parents=True)
    (tmp_path / "input/objects/foo.yaml").write_text("id: foo\n")
    (tmp_path / "input/objects/bar.yaml").write_text("id: bar\n")
    snap = state.snapshot(tmp_path)
    assert snap["stage_1_measure"]["objects_count"] == 2
    assert "foo.yaml" in snap["stage_1_measure"]["objects"]
