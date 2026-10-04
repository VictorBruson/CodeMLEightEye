import base64
import logging

import numpy as np

from .bridge import make_bridge, make_tenons, place_lenses
from .contourSVG import contour_sheet_svg
from .frame import build_solid
from .lens import GeometryError, lens_from_dict
from .params import FrameParams

log = logging.getLogger("optiframe")

DBL_MIN, DBL_MAX = 8.0, 30.0


def _validate(mesh, params):
    n_bodies = len(mesh.split(only_watertight=False))
    # overhang: downward faces steeper than 45 deg, ignoring the flat face on the bed (z = 0)
    n = mesh.face_normals
    on_bed = mesh.triangles[:, :, 2].max(axis=1) < 1e-6
    steep = (n[:, 2] < -np.sin(np.radians(45))) & ~on_bed
    overhang = float(mesh.area_faces[steep].sum() / mesh.area)
    return {
        "watertight": bool(mesh.is_watertight and mesh.is_winding_consistent and mesh.is_volume),
        "single_body": n_bodies == 1,
        "overhang_fraction": round(overhang, 4),
    }


def build_frame(lens_a, lens_b, dbl, params=None):
    """lens_a / lens_b: Lens objects (any order). Returns (trimesh.Trimesh, report dict)."""
    params = params or FrameParams()
    if not (DBL_MIN <= dbl <= DBL_MAX):
        raise GeometryError("bad_dbl", f"Bridge width must be between {DBL_MIN:g} and {DBL_MAX:g} mm.")
    placed = place_lenses(lens_a, lens_b, dbl)
    bridge = make_bridge(placed, params)
    tenons = make_tenons(placed, params)
    mesh = build_solid(placed, bridge, tenons, params)

    by_eye = {lens_a.eye: lens_a, lens_b.eye: lens_b}
    report = {
        "dbl_mm": dbl,
        "bbox_mm": [round(float(v), 2) for v in mesh.extents],
        "validation": _validate(mesh, params),
        "warnings": [],
    }
    v = report["validation"]
    if v["overhang_fraction"] > 0.05:
        report["warnings"].append("Parts of the frame may need supports when printed.")
    if not v["single_body"]:
        report["warnings"].append("The frame is not one connected piece.")
    return mesh, report, by_eye


def build_from_contract(data):
    """Dict in contract.md format -> (stl_bytes, response dict in contract_output.md format).
    Raises GeometryError on bad input."""
    params, warnings = FrameParams.from_dict(data.get("params"))
    left = lens_from_dict(data.get("left"), params, name="left")
    right = lens_from_dict(data.get("right"), params, name="right")
    try:
        dbl = float(data.get("dbl_mm", 18))
    except (TypeError, ValueError):
        raise GeometryError("bad_dbl", "Bridge width must be a number between 8 and 30 mm.")

    mesh, report, _ = build_frame(left, right, dbl, params)
    report["warnings"] = warnings + report["warnings"]
    stl = mesh.export(file_type="stl")

    # The 1:1 trace is a secondary output: if it fails, still return the frame.
    try:
        contour_svg = contour_sheet_svg([left, right])
    except Exception:
        log.exception("contour svg failed")
        contour_svg = None
        report["warnings"].append("The contour sheet could not be generated.")

    response = {
        "version": 1,
        "stl_b64": base64.b64encode(stl).decode("ascii"),
        "contour_svg": contour_svg,
        "left": {"eye": left.eye, "A": round(left.A, 2), "B": round(left.B, 2),
                 "perimeter": round(left.perimeter, 2)},
        "right": {"eye": right.eye, "A": round(right.A, 2), "B": round(right.B, 2),
                  "perimeter": round(right.perimeter, 2)},
        **report,
    }
    return stl, response