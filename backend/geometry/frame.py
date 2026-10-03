import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union


def _clean(poly, tol):
    poly = poly.simplify(tol)
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly


def _extrude(geom, height, z0=0.0):
    """Extrude a Polygon or MultiPolygon from z0 up by `height` (one mesh per part)."""
    parts = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    meshes = [trimesh.creation.extrude_polygon(part, height) for part in parts]
    for m in meshes:
        m.apply_translation([0, 0, z0])
    return meshes


def build_solid(placed, bridge, tenons, params):
    p = params
    # 1. rims: each lens grown by clearance + wall (filled lens for now)
    outers = [_clean(poly.buffer(p.clearance + p.wall, join_style="round"), p.simplify_tol)
              for poly in placed.values()]
    rims = unary_union(outers)

    # 2. extrude rims at full thickness, bridge at its own (thinner) thickness
    parts = _extrude(rims, p.thickness) + _extrude(bridge, p.bridge_thickness)
    for t in tenons.values():
        parts += _extrude(t["poly"], p.tenon_thickness)
    solid = trimesh.boolean.union(parts, engine="manifold")

    # 3. cut the holes: lens + clearance and the tenon pin holes, through the full depth (with margin)
    holes = unary_union(
        [_clean(poly.buffer(p.clearance, join_style="round"), p.simplify_tol) for poly in placed.values()]
        + [t["hole"] for t in tenons.values()])
    cutter = trimesh.boolean.union(_extrude(holes, p.thickness + 2.0, z0=-1.0), engine="manifold")
    frame = trimesh.boolean.difference([solid, cutter], engine="manifold")
    frame.merge_vertices()
    return frame