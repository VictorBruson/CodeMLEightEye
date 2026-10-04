import cv2
import numpy as np

MIN_LENS_AREA_MM2 = 400
MAX_LENS_AREA_MM2 = 3500
GRADIENT_THRESHOLDS = (6.0, 4.5, 3.5, 3.0, 2.5)
RIM_CLOSE_MM = 1.5
MIN_EDGE_EXTENT_MM = 15.0
MIN_SOLIDITY = 0.9
REF_PPM = 8.0
LOCAL_FRAC = 0.4
LOCAL_IN_MM = 0.5
LOCAL_OUT_MM = 1.5
REFINE_RIM = True
REFINE_IN_MM = 6.0
REFINE_OUT_MM = 1.5
N_RAYS = 720
REFINE_STEP_PX = 0.5
OUTWARD_BONUS = 2.0
JUMP_PENALTY = 2.5
MAX_JUMP = 3
SMOOTH_MM = 0.6
EDGE_BIAS_MM = 0.0
R0_CLIP_WINDOW_MM = 20.0
R0_CLIP_TOL_MM = 0.5

REFINE_PASSES = 2
MAX_GROWTH = 1.15
MAX_TOTAL_OUT_MM = 2.5

FINAL_MEDIAN_MM = 6.0
FINAL_SMOOTH_MM = 1.5


def _circ_median(x, w):
    w = int(w) | 1
    half = w // 2
    ext = np.concatenate([x[-half:], x, x[:half]])
    win = np.lib.stride_tricks.sliding_window_view(ext, w)
    return np.median(win, axis=1)


def _clip_bumps(r, window_mm, tol_mm, pixels_per_mm):
    arc_px = float(np.mean(r)) * 2 * np.pi / len(r)
    w = max(5, int(round(window_mm * pixels_per_mm / arc_px)))
    return np.minimum(r, _circ_median(r, w) + tol_mm * pixels_per_mm)


def _circ_gauss(x, sigma):
    k = int(max(3, round(sigma * 4))) | 1
    t = np.arange(k) - k // 2
    g = np.exp(-t ** 2 / (2.0 * sigma ** 2))
    g /= g.sum()
    ext = np.concatenate([x[-k:], x, x[:k]])
    return np.convolve(ext, g, mode="same")[k:-k]


def _smooth_radial(r, pixels_per_mm):
    """Wide circular median (kills narrow bumps/notches) then a light gaussian."""
    arc_mm = float(np.mean(r)) * 2 * np.pi / len(r) / pixels_per_mm
    r = _circ_median(r, max(5, int(round(FINAL_MEDIAN_MM / arc_mm))))
    return _circ_gauss(r, FINAL_SMOOTH_MM / arc_mm)


def _lens_candidates(gradient, ignore, pixels_per_mm, threshold):
    h_img, w_img = gradient.shape
    edges = (gradient > threshold).astype(np.uint8) * 255
    edges[ignore > 0] = 0

    n, labels, stats, _ = cv2.connectedComponentsWithStats(edges, connectivity=8)
    min_ext = MIN_EDGE_EXTENT_MM * pixels_per_mm
    keep = np.zeros(n, bool)
    keep[1:] = np.maximum(stats[1:, cv2.CC_STAT_WIDTH], stats[1:, cv2.CC_STAT_HEIGHT]) >= min_ext
    edges = (keep[labels].astype(np.uint8)) * 255

    k = int(round(RIM_CLOSE_MM * pixels_per_mm)) | 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    padded = cv2.copyMakeBorder(closed, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    flood = padded.copy()
    ff_mask = np.zeros((flood.shape[0] + 2, flood.shape[1] + 2), np.uint8)
    cv2.floodFill(flood, ff_mask, (0, 0), 255)
    inside = cv2.bitwise_not(flood)[1:-1, 1:-1]
    filled = cv2.bitwise_or(closed, inside)

    ko = int(round(1.2 * pixels_per_mm)) | 1
    opened = cv2.morphologyEx(
        filled, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ko, ko))
    )

    contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = []
    for contour in contours:
        area_mm2 = cv2.contourArea(contour) / pixels_per_mm ** 2
        if not (MIN_LENS_AREA_MM2 <= area_mm2 <= MAX_LENS_AREA_MM2):
            continue
        x, y, w, h = cv2.boundingRect(contour)
        if x <= 1 or y <= 1 or x + w >= w_img - 1 or y + h >= h_img - 1:
            continue
        if not (0.3 < w / float(h) < 3.0):
            continue
        hull_area = cv2.contourArea(cv2.convexHull(contour))
        if hull_area <= 0 or cv2.contourArea(contour) / hull_area < MIN_SOLIDITY:
            continue
        out.append(contour)
    return out


def _refine_rim_polar(gray, coarse_mask, pixels_per_mm):
    ys, xs = np.nonzero(coarse_mask)
    cx, cy = xs.mean(), ys.mean()
    cnts, _ = cv2.findContours(coarse_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cnts, key=cv2.contourArea).reshape(-1, 2).astype(np.float64)
    ca = np.arctan2(c[:, 1] - cy, c[:, 0] - cx)
    cr = np.hypot(c[:, 0] - cx, c[:, 1] - cy)
    order = np.argsort(ca)

    angles = np.linspace(-np.pi, np.pi, N_RAYS, endpoint=False)
    r0 = np.interp(angles, ca[order], cr[order], period=2 * np.pi)
    if R0_CLIP_WINDOW_MM:
        r0 = _clip_bumps(r0, R0_CLIP_WINDOW_MM, R0_CLIP_TOL_MM, pixels_per_mm)

    offs = np.arange(-REFINE_IN_MM * pixels_per_mm,
                     REFINE_OUT_MM * pixels_per_mm + REFINE_STEP_PX, REFINE_STEP_PX)
    R = r0[:, None] + offs[None, :]
    mx = (cx + R * np.cos(angles)[:, None]).astype(np.float32)
    my = (cy + R * np.sin(angles)[:, None]).astype(np.float32)

    blur = cv2.GaussianBlur(gray.astype(np.float32), (0, 0), 1.0 * pixels_per_mm / REF_PPM)
    prof = cv2.remap(blur, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

    d = np.gradient(prof, REFINE_STEP_PX, axis=1) * (pixels_per_mm / REF_PPM)  # per reference pixel
    noise = 1.4826 * np.median(np.abs(d - np.median(d)))
    strength = np.clip(np.abs(d) - 4.0 * noise, 0, 30)  # only clearly sharp edges
    score = strength + OUTWARD_BONUS * (offs / pixels_per_mm)[None, :] * (strength > 0)

    S = np.vstack([score, score, score])
    n, M = S.shape
    best = np.empty((n, M))
    back = np.zeros((n, M), np.int16)
    best[0] = S[0]
    jumps = np.arange(-MAX_JUMP, MAX_JUMP + 1)
    for i in range(1, n):
        pad = np.pad(best[i - 1], (MAX_JUMP, MAX_JUMP), constant_values=-1e9)
        cands = np.stack([pad[MAX_JUMP + dj: MAX_JUMP + dj + M] - JUMP_PENALTY * abs(dj)
                          for dj in jumps])
        k = cands.argmax(axis=0)
        best[i] = S[i] + cands[k, np.arange(M)]
        back[i] = jumps[k]
    path = np.empty(n, np.int64)
    path[-1] = int(best[-1].argmax())
    for i in range(n - 1, 0, -1):
        path[i - 1] = np.clip(path[i] + back[i, path[i]], 0, M - 1)
    j = path[N_RAYS: 2 * N_RAYS]

    s_abs = np.abs(d)
    w_in = int(round(LOCAL_IN_MM * pixels_per_mm / REFINE_STEP_PX))
    w_out = int(round(LOCAL_OUT_MM * pixels_per_mm / REFINE_STEP_PX))
    floor = 6.0 * noise
    r = np.empty(N_RAYS)
    for a in range(N_RAYS):
        lo = max(int(j[a]) - w_in, 1)
        hi = min(int(j[a]) + w_out, M - 2)
        seg = s_abs[a, lo:hi + 1]
        thr = max(LOCAL_FRAC * seg.max(), floor)
        peaks = np.nonzero((seg >= thr)
                           & (seg >= s_abs[a, lo - 1:hi])
                           & (seg >= s_abs[a, lo + 1:hi + 2]))[0]
        k = lo + int(peaks[-1]) if peaks.size else int(j[a])
        k = min(max(k, 1), M - 2)
        y0, y1, y2 = s_abs[a, k - 1], s_abs[a, k], s_abs[a, k + 1]
        den = y0 - 2 * y1 + y2
        delta = float(np.clip(0.5 * (y0 - y2) / den, -1, 1)) if den != 0 else 0.0
        r[a] = r0[a] + offs[k] + delta * REFINE_STEP_PX

    ext = np.concatenate([r[-2:], r, r[:2]])
    r = np.median(np.stack([ext[k:k + N_RAYS] for k in range(5)]), axis=0)

    r = _smooth_radial(r, pixels_per_mm)

    pts = np.column_stack([cx + r * np.cos(angles), cy + r * np.sin(angles)])
    refined = np.zeros_like(coarse_mask)
    cv2.fillPoly(refined, [np.round(pts).astype(np.int32)], 255)

    ratio = (refined > 0).sum() / max((coarse_mask > 0).sum(), 1)
    if not (0.6 < ratio <= MAX_GROWTH):
        return coarse_mask
    return refined


def _refine_rim_multipass(gray, mask, pixels_per_mm):
    r = int(round(MAX_TOTAL_OUT_MM * pixels_per_mm))
    limit = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
    for _ in range(REFINE_PASSES):
        mask = cv2.bitwise_and(_refine_rim_polar(gray, mask, pixels_per_mm), limit)
    return mask


def segment_lens(image, pixels_per_mm, card_quad=None):

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (0, 0), 1.5 * pixels_per_mm / REF_PPM)

    gx = cv2.Sobel(blurred, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(blurred, cv2.CV_32F, 0, 1, ksize=3)

    gradient = cv2.magnitude(gx, gy) / 8.0 * (pixels_per_mm / REF_PPM)

    ignore = np.zeros_like(gray)
    if card_quad is not None:
        cv2.fillConvexPoly(ignore, card_quad.astype(np.int32), 255)
        band = int(round(1.5 * pixels_per_mm))
        ignore = cv2.dilate(ignore, np.ones((2 * band + 1, 2 * band + 1), np.uint8))

    valid = (gray > 0).astype(np.uint8) * 255
    valid = cv2.morphologyEx(valid, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    valid = cv2.erode(valid, np.ones((31, 31), np.uint8))
    ignore[valid == 0] = 255

    candidates = []
    for threshold in GRADIENT_THRESHOLDS:
        candidates = _lens_candidates(gradient, ignore, pixels_per_mm, threshold)
        if candidates:
            break

    if not candidates:
        raise ValueError("Could not find a lens candidate.")

    lens_contour = max(candidates, key=cv2.contourArea)

    lens_mask = np.zeros_like(gray)
    cv2.drawContours(lens_mask, [lens_contour], -1, 255, thickness=cv2.FILLED)

    if REFINE_RIM:
        lens_mask = _refine_rim_multipass(gray, lens_mask, pixels_per_mm)

    sigma = SMOOTH_MM * pixels_per_mm
    smooth = cv2.GaussianBlur(lens_mask, (0, 0), sigma)
    lens_mask = (smooth > 127).astype(np.uint8) * 255

    if EDGE_BIAS_MM > 0:
        r = int(round(EDGE_BIAS_MM * pixels_per_mm))
        lens_mask = cv2.erode(
            lens_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
        )
    return lens_mask