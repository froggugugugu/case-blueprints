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


def detect_collisions(objects: list[dict]) -> list[tuple[str, str]]:
    """case_spec.objects の position を使って AABB 重なりを検出。
    重なるペアの id タプルを返す(空なら衝突なし)。"""
    pairs: list[tuple[str, str]] = []
    placed = []
    for o in objects:
        if "id" not in o or "position" not in o:
            continue
        pos = o["position"]
        # 簡略化: bbox 情報が無ければスキップ(case-spec では position のみで bbox 別途必要)
        placed.append((o["id"], pos))
    # 実装メモ: 詳細な AABB 重なり判定には objects[].id から
    # input/objects/<id>.yaml をロードして bbox を引き合わせる必要がある。
    # generator.py 側で組み合わせて呼ぶ想定。
    return pairs
