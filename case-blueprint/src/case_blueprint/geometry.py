"""内寸 / 外寸 / 配置計算。

CadQuery 非依存(純 Python)。generator.py が CadQuery で実装する形状
構築の前段で、寸法決定の根拠ロジックを提供する。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BoundingBox:
    width: float    # X
    depth: float    # Y
    height: float   # Z

    @property
    def volume(self) -> float:
        return self.width * self.depth * self.height


def object_bbox(obj: dict) -> BoundingBox:
    """object.yaml から bounding box を取り出す。tolerance を加算する。"""
    dims = obj["dimensions"]
    tol = float(obj.get("tolerance", 0.0))
    if obj["shape"] == "cylindrical":
        d = float(dims["diameter"]) + 2 * tol
        return BoundingBox(width=d, depth=d, height=float(dims["height"]) + 2 * tol)
    return BoundingBox(
        width=float(dims["width"]) + 2 * tol,
        depth=float(dims["depth"]) + 2 * tol,
        height=float(dims["height"]) + 2 * tol,
    )


def internal_bbox_stacked(objects: list[dict], object_clearance: float, z_margin: float = 0.0) -> BoundingBox:
    """stacked 配置(縦積み):各オブジェクトを Z 方向に積み、X/Y は最大値"""
    if not objects:
        raise ValueError("objects が空です")
    bboxes = [object_bbox(o) for o in objects]
    return BoundingBox(
        width=max(b.width for b in bboxes) + 2 * object_clearance,
        depth=max(b.depth for b in bboxes) + 2 * object_clearance,
        height=sum(b.height for b in bboxes) + 2 * object_clearance + z_margin,
    )


def internal_bbox_side_by_side(
    objects: list[dict], object_clearance: float, z_margin: float = 0.0, axis: str = "Y"
) -> BoundingBox:
    """side_by_side 配置:指定軸方向に並べ、他 2 軸は最大値"""
    if not objects:
        raise ValueError("objects が空です")
    bboxes = [object_bbox(o) for o in objects]
    if axis == "Y":
        return BoundingBox(
            width=max(b.width for b in bboxes) + 2 * object_clearance,
            depth=sum(b.depth for b in bboxes) + 2 * object_clearance,
            height=max(b.height for b in bboxes) + 2 * object_clearance + z_margin,
        )
    if axis == "X":
        return BoundingBox(
            width=sum(b.width for b in bboxes) + 2 * object_clearance,
            depth=max(b.depth for b in bboxes) + 2 * object_clearance,
            height=max(b.height for b in bboxes) + 2 * object_clearance + z_margin,
        )
    raise ValueError(f"未対応の axis: {axis}")


def external_bbox(internal: BoundingBox, wall_thickness: float, bottom_thickness: float | None = None) -> BoundingBox:
    """外寸 = 内寸 + 壁厚 × 2(底厚は別指定可)"""
    bt = bottom_thickness if bottom_thickness is not None else wall_thickness
    return BoundingBox(
        width=internal.width + 2 * wall_thickness,
        depth=internal.depth + 2 * wall_thickness,
        height=internal.height + bt + wall_thickness,  # 上=壁厚相当(蓋無視時)
    )


def fits_in_bed(external: BoundingBox, printer_bed: list[float]) -> bool:
    """造形領域に収まるか(向き考慮なし、最大長軸での判定推奨)"""
    bx, by, bz = printer_bed
    dims = sorted([external.width, external.depth, external.height], reverse=True)
    bed = sorted([bx, by, bz], reverse=True)
    return all(d <= b for d, b in zip(dims, bed))


def _placement_aabb(
    obj_dim: dict, position: tuple[float, float, float]
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """objects(寸法 yaml)と case-spec の position から AABB の (min, max) を返す。

    position は **オブジェクト中心** の座標として扱う(generator.py の build と
    一貫させるため)。bounding box は object_bbox(obj_dim) を流用。
    """
    bb = object_bbox(obj_dim)
    cx, cy, cz = float(position[0]), float(position[1]), float(position[2])
    half = (bb.width / 2, bb.depth / 2, bb.height / 2)
    return (
        (cx - half[0], cy - half[1], cz - half[2]),
        (cx + half[0], cy + half[1], cz + half[2]),
    )


def _aabb_overlap(
    a_min: tuple[float, float, float], a_max: tuple[float, float, float],
    b_min: tuple[float, float, float], b_max: tuple[float, float, float],
) -> bool:
    """3D AABB が重なるか(接触は重なり扱いせず)。"""
    return all(a_max[i] > b_min[i] and b_max[i] > a_min[i] for i in range(3))


def detect_collisions(
    objects: list[dict], placements: list[dict]
) -> list[tuple[str, str]]:
    """objects(input/objects/*.yaml の dict)と placements(case_spec.objects[])
    を突き合わせ、AABB 重なりがあるペアの (id_a, id_b) を返す。

    Args:
        objects: 寸法情報を持つ object yaml のリスト(`id` と `dimensions` 必須)
        placements: case-spec.objects[](`id` と `position[x,y,z]`)

    Returns:
        重なるペアの id タプルのソート済みリスト。空なら衝突なし。

    placement に対応する object が見つからない場合は無視(/measure 未完了の
    可能性。validator 側で別途検出する)。
    """
    # id -> object 寸法
    by_id = {o["id"]: o for o in objects if "id" in o}
    # placements に寸法を紐付けて AABB を計算
    boxes: list[tuple[str, tuple, tuple]] = []
    for p in placements:
        pid = p.get("id")
        pos = p.get("position")
        if pid not in by_id or pos is None or len(pos) < 3:
            continue
        mn, mx = _placement_aabb(by_id[pid], tuple(pos))
        boxes.append((pid, mn, mx))

    pairs: list[tuple[str, str]] = []
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a_id, a_mn, a_mx = boxes[i]
            b_id, b_mn, b_mx = boxes[j]
            if _aabb_overlap(a_mn, a_mx, b_mn, b_mx):
                pairs.append(tuple(sorted([a_id, b_id])))
    return sorted(set(pairs))


def internal_bbox_manual(
    objects: list[dict],
    placements: list[dict],
    object_clearance: float,
    z_margin: float = 0.0,
) -> BoundingBox:
    """layout=manual のとき、各 placement の AABB を集約して内寸を逆算。

    objects(寸法 yaml)と placements(case-spec.objects[])を突き合わせ、
    全 AABB の合成 min/max を取って境界に object_clearance を足した内寸を返す。
    """
    if not placements:
        raise ValueError("placements が空です(layout=manual には position が必要)")

    by_id = {o["id"]: o for o in objects if "id" in o}
    mins = [float("inf")] * 3
    maxs = [float("-inf")] * 3
    found = False
    for p in placements:
        pid = p.get("id")
        pos = p.get("position")
        if pid not in by_id or pos is None or len(pos) < 3:
            continue
        mn, mx = _placement_aabb(by_id[pid], tuple(pos))
        for i in range(3):
            mins[i] = min(mins[i], mn[i])
            maxs[i] = max(maxs[i], mx[i])
        found = True
    if not found:
        raise ValueError(
            "placements の id がいずれも objects と一致しない。"
            "/measure を完了させるか、case-spec.objects[].id を確認してください"
        )
    return BoundingBox(
        width=(maxs[0] - mins[0]) + 2 * object_clearance,
        depth=(maxs[1] - mins[1]) + 2 * object_clearance,
        height=(maxs[2] - mins[2]) + 2 * object_clearance + z_margin,
    )
