# EightEye

**Turn recycled lenses into custom 3D-printed glasses.**

EightEye is a mobile web app that takes a photo of a recycled eyeglass lens, measures its shape to the millimetre, and generates a 3D-printable frame that fits it, even when the left and right lenses have different shapes. It is our answer to the **OptiFrame** challenge from Santé Numérique Sans Frontières (SN-SF), built for the CodeML hackathon.

- Devpost: https://devpost.com/software/eighteye-s5tnwm
- Demo video: https://www.youtube.com/watch?v=NqhWV81mBPg

## Why

In medical deserts and humanitarian settings, opticians are rare or out of reach, yet usable corrective lenses exist: donations, end-of-line stock, lenses taken from used glasses. The expensive part of a pair of glasses is the frame and the fitting. A recycled lens also has its own shape, and one prescription can pair two different shapes, one per eye, so a standard frame does not fit.

Opticians measure a lens outline with a costly tracer. We replace that machine with a phone, and the frame with a few dollars of 3D-printer filament.

## What it does

1. **Capture.** Photograph each lens, left and right, on a plain surface next to a standard bank card. The card (85.6 x 53.98 mm) gives the app a known size.
2. **Measure.** The app straightens the photo into a top-down view, finds the lens outline, and shows its width (A), height (B) and perimeter in millimetres, with an overlay so you can check what it "saw".
3. **Generate.** It builds a 3D frame whose rims follow each lens's exact shape, joined by a bridge (18 mm by default) and with temple tenons that have pin holes.
4. **Preview and export.** You get a rotatable 3D preview, a downloadable **STL** for printing, and a **1:1 SVG** contour sheet to print and lay the real lens on.
5. **Check.** Every frame is validated (watertight mesh, single connected body, printable without excessive supports) and the app warns you if something is off.

No account and no API key are needed.

## How it works

Three layers, built in parallel and joined by a shared JSON contract.

### Vision (OpenCV, NumPy)

- Detects the bank card from colour and edge cues, checks its aspect ratio against a real card, and refines the corners by line fitting.
- Applies a perspective transform to a top-down view at a fixed pixels-per-millimetre scale.
- Segments the lens from **edge gradients rather than brightness**, since a transparent lens shows in its edges, not its surface. It tries several gradient thresholds, closes and fills the rim, filters by area, aspect ratio and solidity, then refines the rim with 720 rays and a dynamic-programming edge search.
- A Fourier-smoothed contour gives a robust A and B using the ISO 8624 "boxing" convention.

### Geometry (Shapely, trimesh, manifold3d)

- **Lens cleanup.** The outline is repaired, resampled to evenly spaced points, smoothed with an FFT low-pass, and recentred on its boxing centre. The smoothing is tested to move A and B by less than 0.1 mm, including on sharp-cornered shapes.
- **Layout.** Each lens is placed by its eye (the right-eye lens on the viewer's left, nasal side toward the centre), with the two lens boxes the chosen bridge width apart.
- **Frame.** Each rim is the lens grown by a clearance plus a wall. The bridge and the temple tenons are added, everything is extruded, and the lens openings are cut with manifold boolean operations. The openings have a ledge, a pocket and a stepped 45-degree entry lip so each lens clicks in and stays put, and the frame prints flat on its back face without supports.
- **Validation.** Each mesh is checked for watertightness, a single connected body, and overhang, with plain-language warnings.

### API (FastAPI)

- One endpoint measures two photos and returns the contour contract and overlays.
- A second turns the contract into a base64 STL, a 1:1 SVG and a validation report.
- Bad input returns a clear, non-technical message in one consistent error format.

### Frontend (React, TypeScript, Vite, three.js)

A mobile-first flow with in-app camera capture and a file-picker fallback, result overlays, an interactive STL viewer (React Three Fiber) and download buttons.

## Data and AI

The current segmentation is **classical computer vision** (gradients, contours, ray search, Fourier smoothing). We do not yet use a trained segmentation model or an external dataset, so there are no model or dataset licences to cite. Training or fine-tuning a segmentation model on a purpose-built dataset (real, synthetic and augmented photos) for harder cases is our main next step.

## Built with

Python, FastAPI, uvicorn, pydantic, NumPy, OpenCV, Pillow, Shapely, trimesh, manifold3d, mapbox-earcut, networkx, pytest, React, TypeScript, Vite, three.js, React Three Fiber, drei, the browser camera API (`getUserMedia`), and Cloudflare Tunnel (`cloudflared`) for testing over HTTPS.

## Team

[An-Khiem Le](https://github.com/akybreaky), [Pamela Daniel](https://github.com/bypameladaniel), [Victor Bruson](https://github.com/VictorBruson), [Quinton Shannon](https://github.com/qrs-programmer)
