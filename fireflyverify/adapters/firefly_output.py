"""Load FIREFLY tracking output into a `ToolResult`.

FIREFLY writes (per input stem):
  <stem>_trajectories.csv      particle, frame, x, y, mass   (frame 0-based; x/y px)
  <stem>_localisations.csv     x, y, frame, mass
  <stem>_diffusion_summary.csv particle, D, alpha, motion, MSD0, ...
  <stem>_run_manifest.json     parameters.{pixel_size_um, frame_interval_s}
"""
from __future__ import annotations

import glob
import json
import os

import pandas as pd

from fireflyverify.adapters.common import (DEFAULT_DT_S, DEFAULT_PX_UM, ToolResult,
                                           coerce_locs, coerce_tracks, tracks_to_locs)


def _find(dirs, suffix):
    """First file ending in `suffix` across the candidate dirs (then recursive)."""
    for d in dirs:
        hits = sorted(glob.glob(os.path.join(d, "*" + suffix)))
        if hits:
            return hits[0]
    for d in dirs:
        hits = sorted(glob.glob(os.path.join(d, "**", "*" + suffix), recursive=True))
        if hits:
            return hits[0]
    return None


def _meta_from_manifest(path):
    px, dt = DEFAULT_PX_UM, DEFAULT_DT_S
    if not path or not os.path.isfile(path):
        return px, dt
    try:
        with open(path, "r", encoding="utf-8") as fh:
            man = json.load(fh)
    except Exception:
        return px, dt
    params = man.get("parameters") or {}
    ws = man.get("widget_state") or {}
    px = (params.get("pixel_size_um") or ws.get("analysis/pixel_size") or px)
    dt = (params.get("frame_interval_s") or ws.get("analysis/frame_interval") or dt)
    try:
        px = float(px)
    except (TypeError, ValueError):
        px = DEFAULT_PX_UM
    try:
        dt = float(dt)
    except (TypeError, ValueError):
        dt = DEFAULT_DT_S
    return px, dt


def load_firefly_output(path) -> ToolResult:
    """Parse a FIREFLY run directory (or any of its output files) → ToolResult."""
    path = os.path.abspath(os.path.expanduser(str(path)))
    if os.path.isfile(path):
        base = os.path.dirname(path)
    else:
        base = path
    # FIREFLY may write into the run dir and/or a firefly_extras/ subdir.
    dirs = [base, os.path.join(base, "firefly_extras")]

    trj_path = _find(dirs, "_trajectories.csv")
    if not trj_path:
        raise FileNotFoundError(
            f"No *_trajectories.csv found under {base} — not a FIREFLY output folder.")
    run_dir = os.path.dirname(trj_path)
    dirs = [run_dir, base, os.path.dirname(run_dir)]

    tracks = coerce_tracks(pd.read_csv(trj_path))

    loc_path = _find(dirs, "_localisations.csv")
    if loc_path:
        locs = coerce_locs(pd.read_csv(loc_path))
    else:
        locs = coerce_locs(tracks_to_locs(tracks))

    diff_path = _find(dirs, "_diffusion_summary.csv")
    if diff_path:
        diff = pd.read_csv(diff_path)
        if "particle" in diff.columns:
            diff["particle"] = diff["particle"].astype(float).round().astype(int)
    else:
        diff = pd.DataFrame(columns=["particle", "D", "alpha", "motion"])

    man_path = _find(dirs, "_run_manifest.json")
    px, dt = _meta_from_manifest(man_path)

    return ToolResult(
        name="FIREFLY", locs=locs, tracks=tracks, diff=diff,
        meta={"pixel_size_um": px, "frame_interval_s": dt},
        extra={"trajectories": trj_path, "manifest": man_path})
