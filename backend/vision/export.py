import json
import re

import numpy as np

from .outline import fourier_smooth, DEFAULT_HARMONICS

MIN_POINTS = 8
AB_RANGE_MM = (20.0, 80.0)       # allowed width / height of each lens
DBL_RANGE_MM = (8.0, 30.0)       # allowed bridge width
DEFAULT_DBL_MM = 18
PARAM_KEYS = ("clearance", "wall", "thickness", "groove_depth",
              "bridge_height", "bridge_thickness")


def _resample_closed(points, n):
    p = np.asarray(points, dtype=float)
    closed = np.vstack([p, p[:1]])
    seg = np.hypot(*np.diff(closed, axis=0).T)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    t = np.linspace(0.0, s[-1], n, endpoint=False)
    return np.column_stack([np.interp(t, s, closed[:, 0]),
                            np.interp(t, s, closed[:, 1])])


def lens_points_mm(contour_mm, n_points=200, harmonics=DEFAULT_HARMONICS):
    smooth = fourier_smooth(contour_mm, harmonics)
    pts = _resample_closed(smooth, n_points)
    return pts - pts.min(axis=0)


def validate_contract(data):
    errors = []

    for side, eye in (("left", "L"), ("right", "R")):
        lens = data.get(side)
        if not isinstance(lens, dict):
            errors.append(f"'{side}' is missing or not an object")
            continue
        if lens.get("eye") not in ("L", "R"):
            errors.append(f"{side}.eye must be 'L' or 'R', got {lens.get('eye')!r}")
        pts = lens.get("points_mm")
        try:
            arr = np.asarray(pts, dtype=float)
            ok_shape = arr.ndim == 2 and arr.shape[1] == 2
        except (TypeError, ValueError):
            ok_shape = False
        if not ok_shape:
            errors.append(f"{side}.points_mm must be an array of [x, y]")
        else:
            if len(arr) < MIN_POINTS:
                errors.append(f"{side}.points_mm has {len(arr)} points, need at least {MIN_POINTS}")
            if not np.isfinite(arr).all():
                errors.append(f"{side}.points_mm contains NaN or infinity")
            else:
                a, b = float(np.ptp(arr[:, 0])), float(np.ptp(arr[:, 1]))
                for label, v in (("A (width)", a), ("B (height)", b)):
                    if not AB_RANGE_MM[0] <= v <= AB_RANGE_MM[1]:
                        errors.append(f"{side} {label} = {v:.1f} mm, must be {AB_RANGE_MM[0]:g} to {AB_RANGE_MM[1]:g} mm")
        if "flipped" in lens and not isinstance(lens["flipped"], bool):
            errors.append(f"{side}.flipped must be true or false")

    eyes = [(data.get(s) or {}).get("eye") for s in ("left", "right")]
    if eyes[0] == eyes[1] and eyes[0] is not None:
        errors.append("left.eye and right.eye must be different")

    dbl = data.get("dbl_mm", DEFAULT_DBL_MM)
    if isinstance(dbl, bool) or not isinstance(dbl, (int, float)) or not DBL_RANGE_MM[0] <= dbl <= DBL_RANGE_MM[1]:
        errors.append(f"dbl_mm must be a number from {DBL_RANGE_MM[0]:g} to {DBL_RANGE_MM[1]:g}, got {dbl!r}")

    params = data.get("params", {})
    if not isinstance(params, dict):
        errors.append("params must be an object")

    if errors:
        raise ValueError("Input does not follow contract.md:\n  - " + "\n  - ".join(errors))


def build_contract(left_result, right_result, dbl_mm=DEFAULT_DBL_MM, params=None,
                   left_flipped=False, right_flipped=False, n_points=200):
    params = dict(params or {})
    unknown = [k for k in params if k not in PARAM_KEYS]
    if unknown:
        print(f"Warning: params {unknown} are not known keys and will be ignored by "
              f"the geometry module (known: {', '.join(PARAM_KEYS)})")

    def entry(result, eye, flipped):
        pts = lens_points_mm(result["lens_contour_mm"], n_points)
        return {"eye": eye,
                "points_mm": [[round(float(x), 2), round(float(y), 2)] for x, y in pts],
                "flipped": bool(flipped)}

    data = {"left": entry(left_result, "L", left_flipped),
            "right": entry(right_result, "R", right_flipped),
            "dbl_mm": dbl_mm,
            "params": params}
    validate_contract(data)
    return data


def write_contract_json(data, path):
    validate_contract(data)
    text = json.dumps(data, indent=2)
    text = re.sub(r"\[\s+(-?[\d.]+),\s+(-?[\d.]+)\s+\]", r"[\1, \2]", text)
    with open(path, "w") as f:
        f.write(text + "\n")
