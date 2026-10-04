import cv2
import numpy as np

try:
    from .calibration import calibrate
    from .segmentation import segment_lens
    from .outline import robust_boxing
    from .export import build_contract, write_contract_json, DEFAULT_DBL_MM
    from .contours import (
        create_contour_overlay,
        find_lens_contours,
        contour_to_mm,
        calculate_measurements,
    )
except ImportError:
    import os
    import sys

    sys.path.insert(0, os.path.dirname(__file__))

    from calibration import calibrate
    from segmentation import segment_lens
    from outline import robust_boxing
    from export import build_contract, write_contract_json, DEFAULT_DBL_MM
    from contours import (
        create_contour_overlay,
        find_lens_contours,
        contour_to_mm,
        calculate_measurements,
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


def export_contract(left_image, right_image, out_path="frame_input.json",
                    dbl_mm=DEFAULT_DBL_MM, params=None,
                    left_flipped=False, right_flipped=False, debug=True):
    results = {}
    for side, path in (("left", left_image), ("right", right_image)):
        if path not in results:
            results[path] = process_image(path)
        result = results[path]
        print(f"{side}: A={result['measurements']['width_mm']:.2f} mm, "
              f"B={result['measurements']['height_mm']:.2f} mm  ({path})")
        if debug:
            # Always look at these: they show what the code actually "saw".
            cv2.imwrite(f"{side}_overlay.jpg", result["overlay_image"])

    data = build_contract(results[left_image], results[right_image], dbl_mm=dbl_mm,
                          params=params, left_flipped=left_flipped,
                          right_flipped=right_flipped)
    write_contract_json(data, out_path)
    print(f"Wrote {out_path}")
    return data


if __name__ == "__main__":
    import argparse
    import json

    from pathlib import Path

    ap = argparse.ArgumentParser(
        description="Measure lenses and write the build_frame() input JSON."
    )

    default_image = Path(__file__).parent / "test_image.jpg"
    default_image2 = Path(__file__).parent / "test_image2.jpg"

    ap.add_argument(
        "left",
        nargs="?",
        default=str(default_image),
        help="photo of the lens for the wearer's LEFT eye"
    )
    ap.add_argument("right", nargs="?", default=str(default_image2),
                    help="photo of the lens for the RIGHT eye (default: same photo as left)")
    ap.add_argument("-o", "--out", default="frame_input.json")
    ap.add_argument("--dbl", type=float, default=DEFAULT_DBL_MM, help="bridge width in mm (8-30)")
    ap.add_argument("--params", default="{}",
                    help='frame settings overrides as JSON, e.g. \'{"clearance": 0.2, "wall": 3.0}\'')
    ap.add_argument("--left-flipped", action="store_true", help="left lens was photographed back side up")
    ap.add_argument("--right-flipped", action="store_true", help="right lens was photographed back side up")
    args = ap.parse_args()

    right = args.right or args.left
    if right == args.left:
        print("Note: the same photo is used for both lenses.")
    export_contract(args.left, right, args.out, dbl_mm=args.dbl,
                    params=json.loads(args.params),
                    left_flipped=args.left_flipped, right_flipped=args.right_flipped)
