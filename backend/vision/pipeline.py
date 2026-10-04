import cv2
import numpy as np

from calibration import calibrate
from segmentation import segment_lens
from outline import robust_boxing
from export import export_lens_json
from contours import (
    create_contour_overlay,
    find_lens_contours,
    contour_to_mm,
    calculate_measurements,
    create_contour_overlay
)

def process_image(image_path):
    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(f"Could not read image from path: {image_path}")

    warped, pixels_per_mm, corners, card_quad = calibrate(image)

    lens_mask = segment_lens(warped, pixels_per_mm, card_quad)

    lens_contour = find_lens_contours(lens_mask)

    lens_contour_mm = contour_to_mm(lens_contour, pixels_per_mm)

    measurements = calculate_measurements(lens_contour, pixels_per_mm)

    measurements["width_raw_mm"] = measurements["width_mm"]
    measurements["height_raw_mm"] = measurements["height_mm"]
    measurements["width_mm"], measurements["height_mm"] = robust_boxing(lens_contour_mm)

    overlay_image = create_contour_overlay(warped, lens_contour)

    return {
        "warped_image": warped,
        "measurements": measurements,
        "lens_mask": lens_mask,
        "lens_contour": lens_contour,
        "lens_contour_mm": lens_contour_mm,
        "overlay_image": overlay_image
    }

def measure_multi(image_paths):
    shots = [process_image(p)["measurements"] for p in image_paths]
    A = np.array([m["width_mm"] for m in shots])
    B = np.array([m["height_mm"] for m in shots])
    return {
        "A_mm": float(np.median(A)),
        "B_mm": float(np.median(B)),
        "A_spread_mm": float(A.max() - A.min()),
        "B_spread_mm": float(B.max() - B.min()),
        "shots": shots,
    }


if __name__ == "__main__":
    result = process_image("test_image.jpg")

    print("\nMeasurements:\n")
    for name, value in result["measurements"].items():
        print(f"{name}: {value:.2f} mm")

    cv2.imwrite("debug_warped.jpg", result["warped_image"])
    cv2.imwrite("debug_overlay.jpg", result["overlay_image"])
    cv2.imwrite("debug_mask.png", result["lens_mask"])

    export_lens_json(result, "lens_outline.json")
