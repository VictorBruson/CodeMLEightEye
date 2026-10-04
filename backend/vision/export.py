import json

import numpy as np

from outline import fourier_smooth, DEFAULT_HARMONICS


def _resample_closed(points, n):
    p = np.asarray(points, dtype=float)
    closed = np.vstack([p, p[:1]])
    seg = np.hypot(*np.diff(closed, axis=0).T)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    t = np.linspace(0.0, s[-1], n, endpoint=False)
    return np.column_stack([np.interp(t, s, closed[:, 0]),
                            np.interp(t, s, closed[:, 1])])


def _shoelace_area(p):
    x, y = p[:, 0], p[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def lens_outline_mm(contour_mm, n_points=200, harmonics=DEFAULT_HARMONICS):
    smooth = fourier_smooth(contour_mm, harmonics)            # image coords (y down)
    pts = _resample_closed(smooth, n_points)
    pts[:, 1] *= -1                                           # y down -> y up
    if _shoelace_area(pts) < 0:                               # make it counter-clockwise
        pts = pts[::-1]
    centre = (pts.min(axis=0) + pts.max(axis=0)) / 2.0
    return pts - centre


def export_lens_json(result, path, n_points=200):
    pts = lens_outline_mm(result["lens_contour_mm"], n_points)
    perimeter = float(np.hypot(*np.diff(np.vstack([pts, pts[:1]]), axis=0).T).sum())
    data = {
        "units": "mm",
        "coordinate_system": {
            "origin": "centre of the outline bounding box",
            "x_axis": "right",
            "y_axis": "up",
            "winding": "counter-clockwise",
            "closed": "implicit; the first point is not repeated at the end",
        },
        "point_count": int(len(pts)),
        "measurements": {
            "width_mm": round(float(np.ptp(pts[:, 0])), 3),
            "height_mm": round(float(np.ptp(pts[:, 1])), 3),
            "perimeter_mm": round(perimeter, 3),
            "area_mm2": round(abs(_shoelace_area(pts)), 3),
        },
        "points_mm": [[round(float(x), 3), round(float(y), 3)] for x, y in pts],
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return data
