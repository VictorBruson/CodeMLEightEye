from shapely import affinity
from shapely.geometry import Polygon, box

from .lens import GeometryError


def place_lenses(lens_a, lens_b, dbl):
    """Returns {"R": polygon, "L": polygon}, translated into frame position."""
    by_eye = {lens_a.eye: lens_a, lens_b.eye: lens_b}
    if set(by_eye) != {"L", "R"}:
        raise GeometryError("bad_eye", "Choose one left and one right lens.")
    right, left = by_eye["R"], by_eye["L"]
    return {
        "R": affinity.translate(right.poly, xoff=-(dbl / 2 + right.A / 2)),
        "L": affinity.translate(left.poly, xoff=+(dbl / 2 + left.A / 2)),
    }


def _nasal_x(poly, eye, y_lo, y_hi):
    """x of the lens edge on the nose side, inside the horizontal band [y_lo, y_hi]."""
    minx, _, maxx, _ = poly.bounds
    band = poly.intersection(box(minx - 1, y_lo, maxx + 1, y_hi))
    if band.is_empty:                      # band misses the lens: fall back to the box edge
        return maxx if eye == "R" else minx
    bx0, _, bx1, _ = band.bounds
    return bx1 if eye == "R" else bx0      # right-eye lens: nose side is +x


def make_bridge(placed, params):
    """Rectangle from one lens edge to the other, at bridge height.
    It starts exactly at the lens edges, so it overlaps the whole rim ring there
    and the union is one body. The lens holes are cut out afterwards."""
    y_mid = params.bridge_offset_y
    y_lo, y_hi = y_mid - params.bridge_height / 2, y_mid + params.bridge_height / 2
    x0 = _nasal_x(placed["R"], "R", y_lo, y_hi)
    x1 = _nasal_x(placed["L"], "L", y_lo, y_hi)
    return box(x0, y_lo, x1, y_hi)