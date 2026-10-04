import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union

from .lens import GeometryError

# Stacked cutter layers overlap by this much (mm) so they fuse into one solid
# instead of touching along a shared face.
EPS = 1e-3


def _clean(poly, tol):
    poly = poly.simplify(tol)
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly


def _extrude(geom, height, z0=0.0):
    """Extrude a Polygon or MultiPolygon from z0 up by `height` (one mesh per part)."""
    if geom.is_empty:
        raise GeometryError("bad_shape", "The lens outline looks invalid. Retake the photo.")
    parts = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    meshes = [trimesh.creation.extrude_polygon(part, height) for part in parts]
    for m in meshes:
        m.apply_translation([0, 0, z0])
    return meshes


def check_retention(p):
    """Check the lens-retention numbers. Returns a list of warnings.
    Raises GeometryError("bad_params") when the numbers cannot make a working pocket."""
    must_be_positive = {
        "thickness": p.thickness, "groove_depth": p.groove_depth,
        "lens_edge_thickness": p.lens_edge_thickness, "ledge_thickness": p.ledge_thickness,
        "ledge_width": p.ledge_width, "lip_height": p.lip_height,
    }
    for name, value in must_be_positive.items():
        if value <= 0:
            raise GeometryError("bad_params", f"Frame setting '{name}' must be greater than zero.")
    if int(round(p.lip_steps)) < 1:
        raise GeometryError("bad_params", "Frame setting 'lip_steps' must be at least 1.")

    stack = p.ledge_thickness + p.lens_edge_thickness + p.lip_height
    if stack > p.thickness:
        raise GeometryError(
            "bad_params",
            f"The frame is too thin for the lens pocket: thickness must be at least {stack:g} mm.")

    # the open top of the lip must leave at least 1 mm of wall around the lens
    top_offset = p.clearance - p.groove_depth + p.lip_height
    if top_offset > p.clearance + p.wall - 1.0:
        raise GeometryError("bad_params", "The frame wall is too thin for the entry lip.")

    warnings = []
    overlap = p.groove_depth - p.clearance
    if overlap <= 0:
        warnings.append("The lens will not be held: groove_depth must be larger than clearance.")
    elif overlap > 0.6:
        warnings.append("The lens may be hard to snap in: the lip overlaps it by more than 0.6 mm.")
    return warnings


def retention_layers(p):
    """Hole profile of one lens, bottom to top: a list of (offset_mm, z_bottom, z_top).

    `offset` is how far the hole is grown from the lens outline (negative = smaller
    than the lens). From the bed (z = 0) up:
      ledge   smaller than the lens, so the lens rests on it
      pocket  lens + clearance, as tall as the lens edge
      lip     starts `groove_depth` inside the pocket wall (the lens clicks past it),
              then widens in `lip_steps` stairs at 45 degrees so the lens can enter
      top     straight, wide open
    Every stair widens going up, so only the underside of the lip faces down.
    """
    c = p.clearance
    z_ledge = p.ledge_thickness
    z_pocket = z_ledge + p.lens_edge_thickness
    steps = max(1, int(round(p.lip_steps)))
    step_h = p.lip_height / steps
    narrow = c - p.groove_depth

    layers = [(-p.ledge_width, -1.0, z_ledge),   # starts below the bed so the cut is clean
              (c, z_ledge, z_pocket)]
    for i in range(steps):
        layers.append((narrow + i * step_h, z_pocket + i * step_h, z_pocket + (i + 1) * step_h))
    layers.append((narrow + p.lip_height, z_pocket + p.lip_height, p.thickness + 1.0))
    return layers


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

    # 3. cut the lens openings layer by layer (ledge, pocket, entry lip), then the
    #    tenon pin holes straight through the full depth (with margin)
    pieces = []
    for offset, z_bottom, z_top in retention_layers(p):
        shape = unary_union([_clean(poly.buffer(offset, join_style="round"), p.simplify_tol)
                             for poly in placed.values()])
        pieces += _extrude(shape, (z_top - z_bottom) + EPS, z0=z_bottom)
    pins = unary_union([t["hole"] for t in tenons.values()])
    pieces += _extrude(pins, p.thickness + 2.0, z0=-1.0)
    cutter = trimesh.boolean.union(pieces, engine="manifold")
    frame = trimesh.boolean.difference([solid, cutter], engine="manifold")
    frame.merge_vertices()
    return frame