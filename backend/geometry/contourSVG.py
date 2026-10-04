import numpy as np

PAGE_W, PAGE_H = 210.0, 297.0
MARGIN = 10.0
SCALE_BAR_MM = 50.0
STROKE_MM = 0.25
TEXT_MM = 4.0


def photo_view_ring(lens):
    """Lens outline as seen in the photo: (N, 2) array, mm, x right, y down.

    lens.poly is y-up and centered on the boxing center. Image axes flip y back;
    if the photo was taken back side up, lens.py also mirrored x, so undo that.
    """
    xy = np.asarray(lens.poly.exterior.coords, dtype=float)[:-1]
    x = -xy[:, 0] if getattr(lens, "flipped", False) else xy[:, 0]
    return np.column_stack([x, -xy[:, 1]])


def _f(v):
    """Format a number for SVG: 3 decimals (0.001 mm), no trailing zeros."""
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _path_d(ring):
    pts = " L".join(f"{_f(x)},{_f(y)}" for x, y in ring)
    return f"M{pts} Z"


def _eye_name(eye):
    return {"L": "Left", "R": "Right"}.get(eye, eye)


def contour_sheet_svg(lenses):
    """Build the printable sheet for one or two Lens objects. Returns SVG text.

    Lenses are stacked top to bottom, right eye first (the order they sit in
    the frame, viewer's left to right). Each carries data-eye, data-A, data-B.
    """
    lenses = sorted(lenses, key=lambda l: 0 if l.eye == "R" else 1)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_f(PAGE_W)}mm" '
        f'height="{_f(PAGE_H)}mm" viewBox="0 0 {_f(PAGE_W)} {_f(PAGE_H)}">',
        f'<rect width="{_f(PAGE_W)}" height="{_f(PAGE_H)}" fill="#fff"/>',
        f'<g font-family="sans-serif" font-size="{_f(TEXT_MM)}" fill="#000">',
        f'<text id="title" x="{_f(MARGIN)}" y="{_f(MARGIN + 3)}">'
        f'EightEye - lens contour, scale 1:1. Print at 100% (actual size), '
        f'then lay the lens on the line.</text>',
        '</g>',
    ]

    cx = PAGE_W / 2
    top = MARGIN + 12
    for lens in lenses:
        ring = photo_view_ring(lens)
        label = f"{_eye_name(lens.eye)} lens ({lens.eye}) - A {lens.A:.2f} x B {lens.B:.2f} mm"
        cy = top + 8 + lens.B / 2
        out.append(f'<g id="lens-{lens.eye}" data-eye="{lens.eye}" '
                   f'data-A="{lens.A:.3f}" data-B="{lens.B:.3f}">')
        out.append(f'<text x="{_f(cx - lens.A / 2)}" y="{_f(top + 3)}" '
                   f'font-family="sans-serif" font-size="{_f(TEXT_MM)}">{label}</text>')
        out.append(f'<g transform="translate({_f(cx)},{_f(cy)})">')
        # boxing rectangle (what A and B measure) and centre cross, hairline grey
        hw, hh = lens.A / 2, lens.B / 2
        out.append(f'<rect x="{_f(-hw)}" y="{_f(-hh)}" width="{_f(lens.A)}" height="{_f(lens.B)}" '
                   f'fill="none" stroke="#999" stroke-width="0.1" stroke-dasharray="1 1"/>')
        out.append(f'<path d="M-3,0 L3,0 M0,-3 L0,3" fill="none" stroke="#999" stroke-width="0.1"/>')
        out.append(f'<path class="contour" d="{_path_d(ring)}" fill="none" stroke="#000" '
                   f'stroke-width="{_f(STROKE_MM)}" stroke-linejoin="round"/>')
        out.append('</g></g>')
        top += 8 + lens.B + 8

    # scale bar: exactly SCALE_BAR_MM long, with end ticks
    bx0 = MARGIN
    by = PAGE_H - MARGIN - 8
    bx1 = bx0 + SCALE_BAR_MM
    out.append('<g id="scale-bar">')
    out.append(f'<path d="M{_f(bx0)},{_f(by)} L{_f(bx1)},{_f(by)} '
               f'M{_f(bx0)},{_f(by - 2)} L{_f(bx0)},{_f(by + 2)} '
               f'M{_f(bx1)},{_f(by - 2)} L{_f(bx1)},{_f(by + 2)}" '
               f'fill="none" stroke="#000" stroke-width="{_f(STROKE_MM)}"/>')
    out.append(f'<text x="{_f(bx1 + 4)}" y="{_f(by + 1.4)}" font-family="sans-serif" '
               f'font-size="{_f(TEXT_MM)}">{_f(SCALE_BAR_MM)} mm - measure this bar; '
               f'if it is not {_f(SCALE_BAR_MM)} mm, reprint at 100%</text>')
    out.append('</g>')
    out.append('</svg>')
    return "\n".join(out)