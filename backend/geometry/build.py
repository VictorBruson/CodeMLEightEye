import base64
import logging
import numpy as np

from .bridge import make_bridge, make_tenons, place_lenses
from .contourSVG import contour_sheet_svg
from .frame import build_solid, check_retention
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


def build_frame(lens_a, lens_b, dbl, params_by_eye):
    """lens_a / lens_b: Lens objects (any order).
    params_by_eye: dict mapping eye ('L', 'R') to FrameParams.
    Returns (trimesh.Trimesh, report dict, by_eye dict).
    """
    by_eye = {lens_a.eye: lens_a, lens_b.eye: lens_b}
    if not (DBL_MIN <= dbl <= DBL_MAX):
        raise GeometryError("bad_dbl", f"Bridge width must be between {DBL_MIN:g} and {DBL_MAX:g} mm.")

    retention_warnings = []
    for eye, p in params_by_eye.items():
        retention_warnings.extend(check_retention(p))

    placed = place_lenses(lens_a, lens_b, dbl)
    # Bridge uses the left lens params for height/thickness defaults
    primary_params = params_by_eye.get("L", list(params_by_eye.values())[0])
    bridge = make_bridge(placed, primary_params)
    tenons = make_tenons(placed, primary_params)
    mesh = build_solid(placed, bridge, tenons, params_by_eye)

    report = {
        "dbl_mm": dbl,
        "bbox_mm": [round(float(v), 2) for v in mesh.extents],
        "validation": _validate(mesh, primary_params),
        "warnings": list(set(retention_warnings)),
    }
    v = report["validation"]
    if v["overhang_fraction"] > 0.05:
        report["warnings"].append("Parts of the frame may need supports when printed.")
    if not v["single_body"]:
        report["warnings"].append("The frame is not one connected piece.")
    return mesh, report, by_eye


def build_from_contract(data):
    """Dict in contract.md format -> (stl_bytes, response dict in contract_output.md format).
    Raises GeometryError on bad input.
    """
    if not isinstance(data, dict):
        raise GeometryError("bad_contract", "Contract payload must be a JSON object.")

    # 1. Parse global default params
    global_raw = data.get("params")
    global_dict = global_raw if isinstance(global_raw, dict) else {}
    global_params, global_warnings = FrameParams.from_dict(global_dict)

    # 2. Extract per-lens dicts and merge: global params <- per-lens overrides
    left_raw = data.get("left") if isinstance(data.get("left"), dict) else {}
    right_raw = data.get("right") if isinstance(data.get("right"), dict) else {}

    left_params_raw = left_raw.get("params")
    right_params_raw = right_raw.get("params")

    left_dict = {**global_dict, **(left_params_raw if isinstance(left_params_raw, dict) else {})}
    right_dict = {**global_dict, **(right_params_raw if isinstance(right_params_raw, dict) else {})}

    # Ensure shared 'wall' parameter synchronization across both sides
    if "wall" in global_dict:
        left_dict["wall"] = global_dict["wall"]
        right_dict["wall"] = global_dict["wall"]

    left_params, left_warnings = FrameParams.from_dict(left_dict)
    right_params, right_warnings = FrameParams.from_dict(right_dict)

    # Combine parameter warnings
    all_param_warnings = list(set(global_warnings + left_warnings + right_warnings))

    # 3. Instantiate Lens objects with their respective params
    left = lens_from_dict(left_raw, left_params, name="left")
    right = lens_from_dict(right_raw, right_params, name="right")

    try:
        dbl = float(data.get("dbl_mm", 18))
    except (TypeError, ValueError):
        raise GeometryError("bad_dbl", "Bridge width must be a number between 8 and 30 mm.")

    # 4. Generate 3D mesh passing per-eye params map
    params_by_eye = {"L": left_params, "R": right_params}
    mesh, report, _ = build_frame(left, right, dbl, params_by_eye)
    report["warnings"] = list(set(all_param_warnings + report["warnings"]))
    stl = mesh.export(file_type="stl")

    # 5. Generate 1:1 contour SVG trace
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
        "left": {
            "eye": left.eye,
            "A": round(left.A, 2),
            "B": round(left.B, 2),
            "perimeter": round(left.perimeter, 2),
        },
        "right": {
            "eye": right.eye,
            "A": round(right.A, 2),
            "B": round(right.B, 2),
            "perimeter": round(right.perimeter, 2),
        },
        **report,
    }
    return stl, response