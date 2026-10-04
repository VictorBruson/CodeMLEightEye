"""All tunable numbers live here. Units: mm."""
from dataclasses import dataclass, fields


@dataclass
class FrameParams:
    # --- lens contour cleanup ---
    resample_points: int = 512   # points after uniform resampling
    harmonics: int = 40          # FFT harmonics kept when smoothing
    min_size_mm: float = 20.0    # A and B must be within [min, max]
    max_size_mm: float = 80.0

    # --- frame (used by later modules) ---
    clearance: float = 0.2
    wall: float = 3.0
    thickness: float = 4.5
    groove_depth: float = 0.5      # how far the entry lip reaches in past the pocket wall;
                                   # snap overlap on the lens = groove_depth - clearance

    # --- lens retention: the hole is a stack of layers, built up from the bed (z = 0) ---
    #   ledge (the lens rests on it) -> pocket (holds the lens edge)
    #   -> 45-degree entry lip (the lens clicks past it) -> open top
    lens_edge_thickness: float = 2.0  # thickness of the lens edge = height of the pocket
    ledge_thickness: float = 0.8      # height of the ledge on the bed side
    ledge_width: float = 0.8          # how far the ledge reaches in under the lens edge
    lip_height: float = 1.0           # height of the 45-degree entry lip
    lip_steps: int = 4                # stair steps used to approximate that 45-degree slope

    bridge_height: float = 4.0
    bridge_thickness: float = 3.0
    bridge_offset_y: float = 0.0   # bridge center above (+) / below (-) the boxing line

    # temple tenons: one tab per rim on the outer (temple) side
    tenon_width: float = 8.0       # how far the tab sticks out of the rim (x)
    tenon_height: float = 7.0      # tab height (y)
    tenon_thickness: float = 3.0   # tab depth (z), flush with the back face
    tenon_hole_d: float = 1.6      # pin hole diameter, axis along z
    tenon_hole_inset: float = 3.0  # pin hole center, measured back from the tab tip
    tenon_overlap: float = 1.5     # how far the tab reaches into the rim (joins the two)
    tenon_corner_r: float = 1.5    # rounded corners
    tenon_drop: float = 0.33       # position: fraction of the lens height, down from the top
    simplify_tol: float = 0.02     # polygon simplification after offsets

    @classmethod
    def from_dict(cls, overrides=None):
        """Build params from the contract's `params` object.
        Returns (params, warnings). Unknown keys are ignored with a warning."""
        if overrides is None:
            overrides = {}
        if not isinstance(overrides, dict):
            return cls(), ["params ignored: expected an object"]
        known = {f.name for f in fields(cls)}
        warnings, clean = [], {}
        for k, v in overrides.items():
            if k not in known:
                warnings.append(f"unknown param ignored: {k}")
            elif isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or abs(v) == float("inf"):
                warnings.append(f"param ignored (not a number): {k}")
            else:
                clean[k] = v
        return cls(**clean), warnings