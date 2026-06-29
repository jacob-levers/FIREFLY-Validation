"""Load EXTERNAL ground-truth tracks into the scoring `SimResult` shape.

Supports:
  * plain CSV with track / frame / x / y columns (alias-mapped), and
  * the ISBI-2012 Particle Tracking Challenge XML
    (``<particle><detection t= x= y= z=/>…</particle>``).

Coordinates are normalised to PIXELS and frames to 0-based int. Imported GT has no
known diffusion populations, so `meta["populations"]` is empty (detection +
tracking are scored; recovered-D is shown as a distribution, with no truth-D
overlay — that requires the built-in simulator).
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

from fireflyverify.adapters.common import DEFAULT_DT_S, DEFAULT_PX_UM
from fireflyverify.scoring.simulator import SimResult

_PARTICLE_ALIASES = {"particle", "track", "trackid", "track_id", "trajectory",
                     "traj", "trace", "id"}
_FRAME_ALIASES = {"frame", "t", "time", "plane", "slice"}
_X_ALIASES = {"x", "xpos", "position x", "x_px", "x_pix", "x_nm", "xnano"}
_Y_ALIASES = {"y", "ypos", "position y", "y_px", "y_pix", "y_nm", "ynano"}


def _norm(col: str) -> str:
    c = str(col).strip().strip('"').lower()
    return c.split("[")[0].split("(")[0].strip()


def _is_nm(col: str) -> bool:
    c = str(col).lower()
    return "nm" in c or "nano" in c


def _resolve_frame_offset(frame: np.ndarray, frame_base) -> int:
    """0 → no shift; 1 → −1; "auto" → shift so min becomes 0 (surface it!)."""
    if frame_base in (0, "0"):
        return 0
    if frame_base in (1, "1"):
        return -1
    return -int(frame.min()) if len(frame) else 0          # "auto"


def _meta(pixel_size_um, frame_interval_s):
    px = float(pixel_size_um) if pixel_size_um else DEFAULT_PX_UM
    return {
        "pixel_size_um": px,
        "frame_interval_s": float(frame_interval_s or DEFAULT_DT_S),
        "psf_sigma_px": max(0.5, (0.21 * 660.0 / 1.4) / (px * 1000.0)),
        "photons_per_emitter": 500.0,
        "bg_photons": 1.0,
        "populations": {},                                 # unknown for imported GT
    }


def _finish(particle, frame, x, y, *, pixel_size_um, frame_interval_s,
            stack_path=None):
    gt_tracks = pd.DataFrame({
        "frame": np.asarray(frame, dtype=int),
        "x": np.asarray(x, dtype=float),
        "y": np.asarray(y, dtype=float),
        "particle": np.asarray(particle, dtype=int),
        "population": "?",
    }).sort_values(["particle", "frame"]).reset_index(drop=True)
    gt_locs = gt_tracks[["frame", "x", "y"]].copy()
    gt_locs["photons"] = 1.0
    stack = None
    if stack_path:
        try:
            import tifffile
            stack = tifffile.imread(stack_path)
            if stack.ndim == 2:
                stack = stack[None]
        except Exception:
            stack = None
    return SimResult(stack=stack, gt_locs=gt_locs, gt_tracks=gt_tracks,
                     meta=_meta(pixel_size_um, frame_interval_s))


def _load_csv(path, *, pixel_size_um, frame_interval_s, frame_base, stack_path):
    df = pd.read_csv(path)
    canon = {}
    for col in df.columns:
        n = _norm(col)
        if n in _PARTICLE_ALIASES and "particle" not in canon:
            canon["particle"] = col
        elif n in _FRAME_ALIASES and "frame" not in canon:
            canon["frame"] = col
        elif n in _X_ALIASES and "x" not in canon:
            canon["x"] = col
        elif n in _Y_ALIASES and "y" not in canon:
            canon["y"] = col
    for need in ("particle", "frame", "x", "y"):
        if need not in canon:
            raise ValueError(
                f"Ground-truth CSV missing a '{need}' column; got {list(df.columns)}")
    frame = df[canon["frame"]].to_numpy(float).astype(int)
    frame = frame + _resolve_frame_offset(frame, frame_base)
    x = df[canon["x"]].to_numpy(float)
    y = df[canon["y"]].to_numpy(float)
    if _is_nm(canon["x"]):
        px_nm = (float(pixel_size_um) if pixel_size_um else DEFAULT_PX_UM) * 1000.0
        x = x / px_nm
        y = y / px_nm
    return _finish(df[canon["particle"]].to_numpy(), frame, x, y,
                   pixel_size_um=pixel_size_um, frame_interval_s=frame_interval_s,
                   stack_path=stack_path)


def _load_isbi_xml(path, *, pixel_size_um, frame_interval_s, stack_path):
    root = ET.parse(path).getroot()
    particle, frame, xs, ys = [], [], [], []
    pid = 0
    dropped = 0
    for part in root.iter("particle"):
        dets = list(part.iter("detection"))
        if not dets:
            continue
        any_kept = False
        for det in dets:
            try:
                t = int(round(float(det.get("t"))))
                xv = float(det.get("x"))
                yv = float(det.get("y"))
            except (TypeError, ValueError):
                dropped += 1
                continue
            particle.append(pid); frame.append(t); xs.append(xv); ys.append(yv)
            any_kept = True
        if any_kept:
            pid += 1
    if not particle:
        raise ValueError(f"No <particle><detection .../> rows found in {path}")
    res = _finish(particle, frame, xs, ys,
                  pixel_size_um=pixel_size_um, frame_interval_s=frame_interval_s,
                  stack_path=stack_path)
    if dropped:
        res.meta["dropped_detections"] = dropped
    return res


def load_ground_truth(path, *, pixel_size_um=None, frame_interval_s=DEFAULT_DT_S,
                      frame_base="auto", stack_path=None) -> SimResult:
    """Dispatch on extension/content: ``.xml`` → ISBI-2012; otherwise → CSV."""
    path = os.path.abspath(os.path.expanduser(str(path)))
    ext = os.path.splitext(path)[1].lower()
    if ext == ".xml":
        return _load_isbi_xml(path, pixel_size_um=pixel_size_um,
                              frame_interval_s=frame_interval_s, stack_path=stack_path)
    return _load_csv(path, pixel_size_um=pixel_size_um,
                     frame_interval_s=frame_interval_s, frame_base=frame_base,
                     stack_path=stack_path)
