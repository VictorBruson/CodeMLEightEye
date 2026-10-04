from shapely import affinity
from shapely.geometry import LineString, Point, box
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
    if band.is_empty:
        return maxx if eye == "R" else minx
    bx0, _, bx1, _ = band.bounds
    return bx1 if eye == "R" else bx0


def make_bridge(placed, params):
    """Rectangle from one lens edge to the other, at bridge height.
    It starts exactly at the lens edges, so it overlaps the whole rim ring there
    and the union is one body. The lens holes are cut out afterwards."""
    y_mid = params.bridge_offset_y
    y_lo, y_hi = y_mid - params.bridge_height / 2, y_mid + params.bridge_height / 2
    x0 = _nasal_x(placed["R"], "R", y_lo, y_hi)
    x1 = _nasal_x(placed["L"], "L", y_lo, y_hi)
    return box(x0, y_lo, x1, y_hi)

def make_tenons(placed, params):
    """One tab per rim, on the temple side.
    Returns {"R": {"poly": ..., "hole": ...}, "L": {...}} (2D, frame axes).
 
    The tab starts `tenon_overlap` inside the rim so it fuses with it, sticks out
    `tenon_width` past the outer edge, and has a pin hole (axis along z) near its tip."""
    p = params
    tenons = {}
    for eye, lens in placed.items():
        outer = lens.buffer(p.clearance + p.wall, join_style="round")
        _, miny, _, maxy = lens.bounds
        y_t = maxy - p.tenon_drop * (maxy - miny)
 
        ox0, _, ox1, _ = outer.bounds
        hit = outer.intersection(LineString([(ox0 - 1, y_t), (ox1 + 1, y_t)]))
        if hit.is_empty:
            raise GeometryError("bad_shape", "The lens outline looks invalid. Retake the photo.")
        hx0, _, hx1, _ = hit.bounds
 
        side = -1 if eye == "R" else 1
        # outer rim edge at the tab height
        x_edge = hx0 if eye == "R" else hx1
        x_in = x_edge - side * p.tenon_overlap
        x_tip = x_edge + side * p.tenon_width
 
        tab = box(min(x_in, x_tip), y_t - p.tenon_height / 2,
                  max(x_in, x_tip), y_t + p.tenon_height / 2)
        # round the corners
        tab = tab.buffer(-p.tenon_corner_r).buffer(p.tenon_corner_r)
        hole = Point(x_tip - side * p.tenon_hole_inset, y_t).buffer(p.tenon_hole_d / 2, 16)
        tenons[eye] = {"poly": tab, "hole": hole}
    return tenons