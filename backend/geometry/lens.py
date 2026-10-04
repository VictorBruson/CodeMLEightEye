from dataclasses import dataclass

import numpy as np
from shapely import make_valid
from shapely.geometry import Polygon, MultiPolygon, GeometryCollection
from shapely.geometry.polygon import orient

from .params import FrameParams


class GeometryError(ValueError):
    def __init__(self, code, message, lens=None):
        super().__init__(message)
        self.code, self.message, self.lens = code, message, lens

    def to_dict(self):
        err = {"code": self.code, "message": self.message}
        if self.lens:
            err["lens"] = self.lens
        return {"error": err}


@dataclass
class Lens:
    poly: Polygon
    eye: str
    A: float
    B: float
    perimeter: float
    flipped: bool = False


def from_image_coords(pts):
    """Image axes (y down) -> frame axes (y up)."""
    out = np.array(pts, dtype=float)
    out[:, 1] *= -1
    return out


def _dedupe(pts, tol=1e-6):
    """Drop a repeated closing point and consecutive duplicates."""
    keep = [0]
    for i in range(1, len(pts)):
        if np.hypot(*(pts[i] - pts[keep[-1]])) > tol:
            keep.append(i)
    pts = pts[keep]
    if len(pts) > 1 and np.hypot(*(pts[0] - pts[-1])) <= tol:
        pts = pts[:-1]
    return pts


def _largest_polygon(geom):
    if isinstance(geom, Polygon):
        return geom
    parts = [g for g in getattr(geom, "geoms", []) if isinstance(g, (Polygon, MultiPolygon))]
    polys = []
    for p in parts:
        polys.extend(p.geoms if isinstance(p, MultiPolygon) else [p])
    return max(polys, key=lambda p: p.area) if polys else None


def _resample(ring, n):
    """Uniform arc-length resampling of a closed ring (no repeated end point)."""
    closed = np.vstack([ring, ring[:1]])
    seg = np.hypot(*np.diff(closed, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, s[-1], n, endpoint=False)
    return np.column_stack([np.interp(t, s, closed[:, 0]), np.interp(t, s, closed[:, 1])])


def _smooth(ring, harmonics):
    """FFT low-pass of a closed contour (x + iy). Removes pixel staircase."""
    z = ring[:, 0] + 1j * ring[:, 1]
    f = np.fft.fft(z)
    n = len(z)
    k = np.fft.fftfreq(n, d=1.0 / n)
    f[np.abs(k) > harmonics] = 0
    out = np.fft.ifft(f)
    return np.column_stack([out.real, out.imag])


def lens_from_points(points, eye, flipped=False, params=None, name=None):
    p = params or FrameParams()

    # --- parse ---
    try:
        pts = np.asarray(points, dtype=float)
    except (TypeError, ValueError):
        raise GeometryError("bad_shape", "The lens outline could not be read. Retake the photo.", name)
    if pts.ndim != 2 or pts.shape[1] != 2 or not np.isfinite(pts).all():
        raise GeometryError("bad_shape", "The lens outline could not be read. Retake the photo.", name)
    pts = _dedupe(pts)
    if len(pts) < 8:
        raise GeometryError("too_few_points", "The lens outline could not be read. Retake the photo.", name)

    # --- orient: image axes -> front view, y up ---
    pts = from_image_coords(pts)
    if flipped:
        pts[:, 0] *= -1

    # --- repair ---
    poly = _largest_polygon(make_valid(Polygon(pts)))
    if poly is None or poly.area < 1e-6:
        raise GeometryError("bad_shape", "The lens outline looks invalid. Retake the photo.", name)
    poly = orient(poly, sign=1.0)             # CCW
    ring = np.asarray(poly.exterior.coords)[:-1]

    # --- smooth ---
    ring = _smooth(_resample(ring, p.resample_points), p.harmonics)
    poly = _largest_polygon(make_valid(Polygon(ring)))
    if poly is None:
        raise GeometryError("bad_shape", "The lens outline looks invalid. Retake the photo.", name)
    poly = orient(poly, sign=1.0)

    # --- recenter on boxing center, measure ---
    minx, miny, maxx, maxy = poly.bounds
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    ring = np.asarray(poly.exterior.coords)[:-1] - [cx, cy]
    poly = Polygon(ring)
    A, B = maxx - minx, maxy - miny

    if not (p.min_size_mm <= A <= p.max_size_mm and p.min_size_mm <= B <= p.max_size_mm):
        raise GeometryError(
            "size_out_of_range",
            "This lens looks too small or too large. Check the reference object.", name)

    return Lens(poly=poly, eye=eye, A=A, B=B, perimeter=poly.length, flipped=bool(flipped))


def lens_from_dict(d, params=None, name=None):
    """Takes one contract lens object: {eye, points_mm, flipped?}."""
    if not isinstance(d, dict) or "points_mm" not in d:
        raise GeometryError("missing_lens", "Both lenses are needed to build a frame.", name)
    if d.get("eye") not in ("L", "R"):
        raise GeometryError("bad_eye", "Choose one left and one right lens.", name)
    return lens_from_points(d["points_mm"], d["eye"], bool(d.get("flipped", False)), params, name)