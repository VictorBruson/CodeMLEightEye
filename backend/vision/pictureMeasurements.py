import base64
import json
import tempfile
from pathlib import Path
from typing import Optional

import cv2
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from .pipeline import process_image
from .export import build_contract, DEFAULT_DBL_MM

router = APIRouter()

def _overlay_b64(img):
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode()


import os

async def _process_upload(upload: UploadFile, side: str):
    suffix = Path(upload.filename or "").suffix or ".jpg"

    # Set delete=False so Windows releases the file handle for cv2
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await upload.read())
        tmp_path = tmp.name

    try:
        return process_image(tmp_path)
    except ValueError as e:
        raise HTTPException(422, detail={"side": side, "message": str(e)})
    finally:
        # Clean up the temp file after processing
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def _measurements(result):
    m = result["measurements"]
    return {"A_mm": round(m["width_mm"], 2), "B_mm": round(m["height_mm"], 2)}


@router.post("/api/measure")
async def measure(
    left: UploadFile = File(...),
    right: UploadFile = File(...),
    dbl_mm: float = Form(DEFAULT_DBL_MM),
    params: str = Form("{}"),               # JSON object as a string
    left_flipped: bool = Form(False),
    right_flipped: bool = Form(False),
):
    """Two photos in. Out: the contract (exactly the frame_input.json format),
    plus the overlays and A/B measurements for the user to review."""
    try:
        params_dict = json.loads(params)
        if not isinstance(params_dict, dict):
            raise ValueError
    except ValueError:
        raise HTTPException(422, detail={"message": "params must be a JSON object."})

    results = {"left": await _process_upload(left, "left"),
               "right": await _process_upload(right, "right")}

    try:
        contract = build_contract(results["left"], results["right"],
                                  dbl_mm=dbl_mm, params=params_dict,
                                  left_flipped=left_flipped, right_flipped=right_flipped)
    except ValueError as e:  # e.g. A/B outside 20-80 mm
        raise HTTPException(422, detail={"message": str(e)})

    return {
        "contract": contract,  # frame_input.json format
        "overlays": {s: _overlay_b64(r["overlay_image"]) for s, r in results.items()},
        "measurements": {s: _measurements(r) for s, r in results.items()},
    }