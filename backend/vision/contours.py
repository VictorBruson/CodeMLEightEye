import cv2
import numpy as np

def find_lens_contours(mask):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    if not contours:
        raise ValueError("No lens contour found.")

    contour = max(contours, key=cv2.contourArea)

    return contour


def contour_to_mm(contour, pixels_per_mm):
    points = contour.reshape(-1, 2)
    points_mm = points / pixels_per_mm
    return points_mm


def calculate_measurements(contour, pixels_per_mm):
    x, y, width, height = cv2.boundingRect(contour)
    perimeter_px = cv2.arcLength(contour, True)

    area_px = cv2.contourArea(contour)

    measurements = {
        "width_mm": width / pixels_per_mm,
        "height_mm": height / pixels_per_mm,
        "perimeter_mm": perimeter_px / pixels_per_mm,
        "area_mm2": area_px / (pixels_per_mm ** 2)
    }

    return measurements


def create_contour_overlay(image, contour):
    overlay = image.copy()
    cv2.drawContours(overlay, [contour], -1, (0, 255, 0), thickness=2)
    return overlay
