"""All tunable numbers live here. Units: mm."""
from dataclasses import dataclass, fields


@dataclass
class FrameParams:
    # --- lens contour cleanup ---
    resample_points: int = 512
    harmonics: int = 40
    min_size_mm: float = 20.0
    max_size_mm: float = 80.0

    # --- frame ---
    clearance: float = 0.2
    wall: float = 3.0
    thickness: float = 4.5
    groove_depth: float = 0.5
    bridge_height: float = 4.0
    bridge_thickness: float = 3.0

    bridge_offset_y: float = 0.0
    simplify_tol: float = 0.02

    @classmethod
    def from_dict(cls, overrides=None):
        """Build params from the contract's `params` object.
        Returns (params, warnings). Unknown keys are ignored with a warning."""
        overrides = overrides or {}
        known = {f.name for f in fields(cls)}
        warnings = [f"unknown param ignored: {k}" for k in overrides if k not in known]
        return cls(**{k: v for k, v in overrides.items() if k in known}), warnings