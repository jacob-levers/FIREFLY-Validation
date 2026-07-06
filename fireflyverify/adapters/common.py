"""Shared types + helpers for the file adapters.

`ToolResult` is duck-compatible with `scoring.report.evaluate` (it reads
`.name`, `.locs`, `.tracks`, `.diff`). All coordinates are normalised to the
scoring schema: integer 0-based `frame`, float `x`/`y` in PIXELS, integer
`particle`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

# Re-exported from the package-level constants module so there is one source of
# truth for the acquisition fallbacks (existing `from ...common import
# DEFAULT_PX_UM` call sites keep working).
from fireflyverify.constants import DEFAULT_DT_S, DEFAULT_PX_UM  # noqa: F401


@dataclass
class ToolResult:
    name: str
    locs: pd.DataFrame                 # frame, x, y (, mass)
    tracks: pd.DataFrame               # particle, frame, x, y (, mass)
    diff: pd.DataFrame                 # particle, D, alpha, motion, ... (may be empty)
    meta: dict                         # pixel_size_um, frame_interval_s
    extra: dict = field(default_factory=dict)


def coerce_tracks(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce to particle(int), frame(int, 0-based), x/y(float px); sorted."""
    df = df.copy()
    df["frame"] = df["frame"].astype(float).round().astype(int)
    df["particle"] = df["particle"].astype(float).round().astype(int)
    df["x"] = df["x"].astype(float)
    df["y"] = df["y"].astype(float)
    return df.sort_values(["particle", "frame"]).reset_index(drop=True)


def coerce_locs(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce to frame(int, 0-based), x/y(float px); sorted by frame."""
    df = df.copy()
    df["frame"] = df["frame"].astype(float).round().astype(int)
    df["x"] = df["x"].astype(float)
    df["y"] = df["y"].astype(float)
    return df.sort_values(["frame"]).reset_index(drop=True)


def tracks_to_locs(tracks: pd.DataFrame) -> pd.DataFrame:
    """Fall back to track points when a tool exports no separate localisations
    file. Detection F1 then excludes unlinked spots — surface that caveat in UI."""
    cols = [c for c in ("frame", "x", "y", "mass") if c in tracks.columns]
    return tracks[cols].copy()
