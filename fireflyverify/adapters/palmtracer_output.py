"""Load raw palmTRACER output into a `ToolResult`.

palmTRACER files have NO stem prefix:
  locPALMTracer.txt|csv  — 3 header lines; metadata line 2 carries Pixel_Size(um),
                           Frame_Duration(s); cols id,Plane,Index,Channel,
                           Integrated_Intensity,CentroidX(px),CentroidY(px),...
  trcPALMTracer.txt|csv  — 3 header lines; cols Track,Plane,CentroidX(px),
                           CentroidY(px),CentroidZ(um),Integrated_Intensity,id,...
  trcPALMTracer-*-D.*    — optional native per-track D (Trace, D(um2/s), MSD(0), MSE)

`Plane` is 1-based → subtract 1 for the 0-based scoring frame. Parsing is vendored
from FIREFLY's fa_palmtracer (kept identical so the import matches FIREFLY's).
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from fireflyverify.adapters.common import (DEFAULT_DT_S, DEFAULT_PX_UM, ToolResult,
                                           coerce_locs, coerce_tracks)


def is_palmtracer_folder(folder) -> bool:
    try:
        names = {n.lower() for n in os.listdir(folder)}
    except OSError:
        return False
    has_loc = "locpalmtracer.txt" in names or "locpalmtracer.csv" in names
    has_trc = "trcpalmtracer.txt" in names or "trcpalmtracer.csv" in names
    return has_loc and has_trc


def _read_table(path, header_lines):
    """Read a palmTRACER table (tab- or comma-separated), skipping header rows."""
    with open(path, "r") as fh:
        for _ in range(header_lines):
            fh.readline()
        first = fh.readline()
    sep = "\t" if "\t" in first and first.count("\t") >= first.count(",") else ","
    kw = dict(sep=sep, header=None, comment="#", skiprows=header_lines)
    try:
        return pd.read_csv(path, engine="c", float_precision="round_trip", **kw)
    except (pd.errors.ParserError, ValueError):
        return pd.read_csv(path, engine="python", **kw)


def _parse_native_d(path):
    """Parse a trcPALMTracer-*-D file → diff DataFrame (palmTRACER's own D).
    Columns: ROI Trace D(um2/s) MSD(0) MSE [LogD ...]. alpha/motion stay NaN."""
    rows = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            s = line.strip()
            if not s or s.startswith("#") or s[:3].upper() == "ROI":
                continue
            parts = s.split()
            if len(parts) < 5:
                continue
            try:
                trace = int(round(float(parts[1])))
                D = float(parts[2]); msd0 = float(parts[3]); mse = float(parts[4])
            except ValueError:
                continue
            rows.append((trace, D, msd0, mse))
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=["particle", "D", "MSD0", "MSE"])
    df["alpha"] = np.nan
    df["motion"] = "Unclassified"
    return df


def _pick(folder, *names):
    for n in names:
        p = os.path.join(folder, n)
        if os.path.isfile(p):
            return p
    return None


def load_palmtracer_output(folder) -> ToolResult:
    """Parse a raw palmTRACER output folder → ToolResult."""
    folder = os.path.abspath(os.path.expanduser(str(folder)))
    loc_path = _pick(folder, "locPALMTracer.txt", "locPALMTracer.csv")
    trc_path = _pick(folder, "trcPALMTracer.txt", "trcPALMTracer.csv")
    if not (loc_path and trc_path):
        raise FileNotFoundError(
            f"palmTRACER files (locPALMTracer / trcPALMTracer) not found in {folder}.")
    d_path = _pick(folder, "trcPALMTracer-AllROI-D.txt", "trcPALMTracer-AllROI-D.csv",
                   "trcPALMTracer-1-D.txt", "trcPALMTracer-1-D.csv")

    # metadata header (line 2 holds the values)
    px, dt = DEFAULT_PX_UM, DEFAULT_DT_S
    try:
        with open(loc_path, "r") as fh:
            names = fh.readline().rstrip("\n").replace(",", "\t").split("\t")
            vals = fh.readline().rstrip("\n").replace(",", "\t").split("\t")
        meta = {k.strip(): v.strip() for k, v in zip(names, vals)}
        px = float(meta.get("Pixel_Size(um)", px))
        dt = float(meta.get("Frame_Duration(s)", dt))
    except Exception:
        pass

    loc_df = _read_table(loc_path, header_lines=3)
    loc_df.columns = ["id", "Plane", "Index", "Channel", "Integrated_Intensity",
                      "CentroidX_px", "CentroidY_px", "SigmaX_px", "SigmaY_px",
                      "Angle_rad", "MSE_Gauss", "CentroidZ_um", "MSE_Z_um",
                      "Pair_Distance_px"][:loc_df.shape[1]]
    locs = coerce_locs(pd.DataFrame({
        "x": loc_df["CentroidX_px"].astype(float).values,
        "y": loc_df["CentroidY_px"].astype(float).values,
        "frame": loc_df["Plane"].astype(int).values - 1,        # 1-based → 0-based
        "mass": loc_df["Integrated_Intensity"].astype(float).values,
    }))

    trc_df = _read_table(trc_path, header_lines=3)
    trc_df.columns = ["Track", "Plane", "CentroidX_px", "CentroidY_px",
                      "CentroidZ_um", "Integrated_Intensity", "id",
                      "Pair_Distance_px"][:trc_df.shape[1]]
    tracks = coerce_tracks(pd.DataFrame({
        "particle": trc_df["Track"].astype(int).values,
        "frame": trc_df["Plane"].astype(int).values - 1,        # 1-based → 0-based
        "x": trc_df["CentroidX_px"].astype(float).values,
        "y": trc_df["CentroidY_px"].astype(float).values,
        "mass": trc_df["Integrated_Intensity"].astype(float).values,
    }))

    diff = pd.DataFrame(columns=["particle", "D", "alpha", "motion"])
    if d_path:
        nd = _parse_native_d(d_path)
        if nd is not None and len(nd):
            diff = nd

    return ToolResult(
        name="palmTRACER", locs=locs, tracks=tracks, diff=diff,
        meta={"pixel_size_um": px, "frame_interval_s": dt},
        extra={"native_d": d_path})
