import math

import cv2
import numpy as np

CARD_WIDTH_MM = 85.6
CARD_HEIGHT_MM = 53.98
CARD_RATIO = CARD_WIDTH_MM / CARD_HEIGHT_MM 

PIXELS_PER_MM = 8

SCENE_MARGIN_MM = 250


def order_points(points):
    points = np.array(points, dtype="float32")

    sums = points.sum(axis=1)
    diff = np.diff(points, axis=1).flatten()

    top_left = points[np.argmin(sums)]
    bottom_right = points[np.argmax(sums)]
    top_right = points[np.argmin(diff)]
    bottom_left = points[np.argmax(diff)]

    return np.array([top_left, top_right, bottom_right, bottom_left], dtype="float32")


def _quad_from_contour(contour):
    hull = cv2.convexHull(contour)
    perimeter = cv2.arcLength(hull, True)
    for eps in np.linspace(0.01, 0.08, 15):
        approx = cv2.approxPolyDP(hull, eps * perimeter, True)
        if len(approx) == 4:
            return order_points(approx.reshape(4, 2))
    return order_points(cv2.boxPoints(cv2.minAreaRect(hull)))


def _refine_corners(contour, quad):
    pts = contour.reshape(-1, 2).astype(np.float32)
    lines = []
    for i in range(4):
        a, b = quad[i], quad[(i + 1) % 4]
        d = b - a
        length = float(np.linalg.norm(d))
        u = d / length
        n = np.array([-u[1], u[0]], dtype="float32")
        t = (pts - a) @ u
        dist = np.abs((pts - a) @ n)
        sel = (t > 0.2 * length) & (t < 0.8 * length) & (dist < 0.05 * length)
        if sel.sum() < 10:
            return quad
        vx, vy, x0, y0 = cv2.fitLine(pts[sel], cv2.DIST_L2, 0, 0.01, 0.01).flatten()
        lines.append((np.array([x0, y0]), np.array([vx, vy])))

    refined = []
    for i in range(4):
        p1, d1 = lines[i - 1]
        p2, d2 = lines[i]
        A = np.array([d1, -d2]).T
        if abs(np.linalg.det(A)) < 1e-6:
            return quad
        t = np.linalg.solve(A, p2 - p1)
        refined.append(p1 + t[0] * d1)
    return np.array(refined, dtype="float32")


def _best_card_quad(contours, image_area):
    best, best_score = None, 0.0
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 0.005 * image_area:
            continue

        quad = _quad_from_contour(contour)
        quad_area = cv2.contourArea(quad)
        if quad_area <= 0 or area / quad_area < 0.85:
            continue 

        w = (np.linalg.norm(quad[1] - quad[0]) + np.linalg.norm(quad[2] - quad[3])) / 2
        h = (np.linalg.norm(quad[3] - quad[0]) + np.linalg.norm(quad[2] - quad[1])) / 2
        ratio = max(w, h) / max(min(w, h), 1e-6)
        if abs(ratio - CARD_RATIO) / CARD_RATIO > 0.15:
            continue

        if area > best_score:
            best, best_score = (contour, quad), area
    if best is None:
        return None
    contour, quad = best
    return _refine_corners(contour, quad)


def get_card_corners(image):
    image_area = image.shape[0] * image.shape[1]
    k = np.ones((7, 7), np.uint8)

    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    sat = cv2.GaussianBlur(hsv[:, :, 1], (7, 7), 0)
    _, mask = cv2.threshold(sat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask[hsv[:, :, 2] < 50] = 0  # near-black pixels have meaningless saturation
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    corners = _best_card_quad(contours, image_area)
    if corners is not None:
        return corners

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, k, iterations=2)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return _best_card_quad(contours, image_area)


def rectify_scene(image, corners, pixels_per_mm=PIXELS_PER_MM):
    tl, tr, br, bl = corners
    card_w = CARD_WIDTH_MM * pixels_per_mm
    card_h = CARD_HEIGHT_MM * pixels_per_mm

    # If the card was photographed in portrait, keep it portrait.
    if np.linalg.norm(tr - tl) < np.linalg.norm(bl - tl):
        card_w, card_h = card_h, card_w

    destination = np.array(
        [[0, 0], [card_w, 0], [card_w, card_h], [0, card_h]], dtype="float32"
    )

    H = cv2.getPerspectiveTransform(corners, destination)

    h, w = image.shape[:2]
    photo_corners = np.array(
        [[0, 0], [w, 0], [w, h], [0, h]], dtype="float32"
    ).reshape(-1, 1, 2)
    landed = cv2.perspectiveTransform(photo_corners, H).reshape(-1, 2)

    margin = SCENE_MARGIN_MM * pixels_per_mm
    x_min = max(landed[:, 0].min(), -margin)
    y_min = max(landed[:, 1].min(), -margin)
    x_max = min(landed[:, 0].max(), card_w + margin)
    y_max = min(landed[:, 1].max(), card_h + margin)

    shift = np.array([[1, 0, -x_min], [0, 1, -y_min], [0, 0, 1]], dtype="float64")
    out_size = (int(math.ceil(x_max - x_min)), int(math.ceil(y_max - y_min)))

    warped = cv2.warpPerspective(image, shift @ H, out_size)

    card_quad = (destination - np.array([x_min, y_min], dtype="float32")).astype(
        "float32"
    )
    return warped, card_quad


def calibrate(image):
    corners = get_card_corners(image)

    if corners is None:
        raise ValueError("Could not find the reference card in the image.")

    warped, card_quad = rectify_scene(image, corners, PIXELS_PER_MM)

    return warped, PIXELS_PER_MM, corners, card_quad
