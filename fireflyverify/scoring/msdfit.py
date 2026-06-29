"""Vendored MSD fitter (from FIREFLY's ``fa_diffusion``) — pure numpy/scipy.

Used for the OPTIONAL "common re-fit" grading path: recompute per-track D and α
from each tool's tracks with ONE fitter, so tracking quality can be compared
apples-to-apples independent of each tool's own MSD fit. Default grading uses
each tool's reported D instead.

Model (2D): ``MSD(t) = 4·D·t^alpha + offset``, where ``offset`` is the static
localisation-error floor (≈ 4·σ²), modelled jointly so the fitted D is free of
static-error inflation.  `_msd_and_fit_one` is copied verbatim from FIREFLY so the
recovered D/α match FIREFLY's own fit exactly.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import curve_fit

ALPHA_THRESHOLDS_DEFAULT = (0.5, 0.9, 1.1)
MOBILE_D_THRESHOLD_DEFAULT = 0.05

DIFF_COLUMNS = ["particle", "D", "alpha", "motion", "MSD0", "MSE",
                "loc_sigma_nm", "mean_radial_displacement_um",
                "radius_of_gyration_um"]


def msd_linear(t, D, offset):
    return 4 * D * t + offset


def msd_anomalous(t, D, alpha, offset):
    """2D MSD with an anomalous exponent and a localisation-error floor."""
    return 4 * D * t ** alpha + offset


def classify_motion(alpha, thresholds=ALPHA_THRESHOLDS_DEFAULT):
    """Classify a track by its anomalous exponent α (Immobile/Confined/Brownian/Directed)."""
    t_imm, t_conf, t_dir = thresholds
    if alpha < t_imm:
        return "Immobile"
    elif alpha < t_conf:
        return "Confined"
    elif alpha < t_dir:
        return "Brownian"
    else:
        return "Directed"


def _require_positive_finite(name, val):
    if not (np.isfinite(val) and val > 0):
        raise ValueError(f"{name} must be a positive, finite number (got {val!r})")


def _msd_and_fit_one(xy_um, frames, pid, lag_times, max_lagtime, n_fit,
                     alpha_thresholds=ALPHA_THRESHOLDS_DEFAULT):
    """Compute a per-track MSD array AND fit D + alpha in one pass.

    Uses actual frame numbers (not row indices) so memory-linked gaps do not
    inflate the MSD.  Copied verbatim from FIREFLY's fa_diffusion.
    """
    msd_vals = np.full(max_lagtime, np.nan)
    n_pts = len(xy_um)
    gapless = (n_pts >= 2 and int(frames[-1] - frames[0]) == n_pts - 1)
    if gapless:
        x = xy_um[:, 0]; y = xy_um[:, 1]
        for lag_idx, lag in enumerate(range(1, max_lagtime + 1)):
            if lag >= n_pts:
                break
            dx = x[lag:] - x[:-lag]
            dy = y[lag:] - y[:-lag]
            msd_vals[lag_idx] = np.mean(dx * dx + dy * dy)
    else:
        for lag_idx, lag in enumerate(range(1, max_lagtime + 1)):
            if lag >= n_pts:
                break
            frame_diff = frames[lag:] - frames[:-lag]
            valid = frame_diff == lag
            if valid.sum() > 0:
                d = xy_um[lag:][valid] - xy_um[:-lag][valid]
                msd_vals[lag_idx] = np.mean(d[:, 0] ** 2 + d[:, 1] ** 2)

    t = lag_times[:n_fit]
    m = msd_vals[:n_fit]
    ok = np.isfinite(m) & (m > 0)
    D = alpha = np.nan
    msd0 = np.nan
    mse = np.nan
    immobile = False
    n_ok = int(ok.sum())
    t_ok, m_ok = t[ok], m[ok]
    if n_ok >= 4:
        try:
            slope, intercept = np.polyfit(t_ok, m_ok, 1)
            d_seed = max(slope / 4.0, 1e-6)
            off_seed = max(intercept, 0.0)
        except Exception:
            d_seed, off_seed = 0.01, max(0.0, float(m_ok[0]))
        try:
            popt, _ = curve_fit(msd_anomalous, t_ok, m_ok,
                                p0=[d_seed, 1.0, off_seed],
                                bounds=([0, 0, 0], [np.inf, 2.0, np.inf]),
                                maxfev=5000)
            D, alpha, msd0 = float(popt[0]), float(popt[1]), float(popt[2])
            _resid = m_ok - msd_anomalous(t_ok, *popt)
            mse = float(np.mean(_resid ** 2))
            # Identifiability guard: a jitter-dominated track has a flat MSD
            # (dynamic term ≈ 0), so alpha is unconstrained — drop it.
            t_hi = float(t_ok[-1])
            dyn = 4.0 * D * (t_hi ** alpha)
            total = dyn + max(msd0, 0.0)
            dyn_frac = (dyn / total) if total > 0 else 0.0
            if alpha <= 1e-3 or alpha >= 2.0 - 1e-3 or dyn_frac < 0.10:
                alpha = np.nan
                immobile = True
        except Exception:
            pass
    if not np.isfinite(D) and not immobile and n_ok >= 3:
        try:
            _slope = float(np.polyfit(np.log(t_ok), np.log(m_ok), 1)[0])
            if 0.0 <= _slope <= 2.0:
                alpha = _slope
            else:
                alpha = np.nan
        except Exception:
            pass
        try:
            popt, _ = curve_fit(msd_linear, t_ok, m_ok, p0=[0.01, 0],
                                bounds=([0, -np.inf], [np.inf, np.inf]),
                                maxfev=2000)
            D = float(popt[0])
            msd0 = float(popt[1])
            _resid = m_ok - msd_linear(t_ok, *popt)
            mse = float(np.mean(_resid ** 2))
        except Exception:
            pass

    if np.isfinite(alpha):
        motion = classify_motion(alpha, alpha_thresholds)
    elif immobile:
        motion = "Immobile"
    else:
        motion = "Unknown"

    centroid = xy_um.mean(axis=0)
    sq_dists = np.sum((xy_um - centroid) ** 2, axis=1)
    mean_radial = float(np.mean(np.sqrt(sq_dists)))
    rg = float(np.sqrt(np.mean(sq_dists)))

    if np.isfinite(msd0) and msd0 > 0:
        loc_sigma_nm = float(np.sqrt(msd0 / 4.0) * 1000.0)
    else:
        loc_sigma_nm = np.nan

    return pid, msd_vals, dict(particle=pid, D=D, alpha=alpha, motion=motion,
                               MSD0=msd0, MSE=mse, loc_sigma_nm=loc_sigma_nm,
                               mean_radial_displacement_um=mean_radial,
                               radius_of_gyration_um=rg)


def compute_diff_from_tracks(tracks, pixel_size_um, frame_interval_s,
                             max_lagtime=20, n_fit=5,
                             alpha_thresholds=ALPHA_THRESHOLDS_DEFAULT):
    """Per-track D / alpha / motion from a tracks DataFrame (serial).

    `tracks`: DataFrame with columns particle, frame, x, y (x/y in PIXELS).
    Returns a diff DataFrame with the DIFF_COLUMNS schema (D in µm²/s), the same
    shape `diffusion_recovery` consumes.
    """
    _require_positive_finite("pixel_size_um", pixel_size_um)
    _require_positive_finite("frame_interval_s", frame_interval_s)
    if max_lagtime < 1:
        raise ValueError(f"max_lagtime must be >= 1 (got {max_lagtime!r})")
    if n_fit > max_lagtime:
        n_fit = int(max_lagtime)
    if tracks is None or len(tracks) == 0 or "particle" not in tracks.columns:
        return pd.DataFrame(columns=DIFF_COLUMNS)

    lag_times = np.arange(1, max_lagtime + 1) * float(frame_interval_s)
    rows = []
    for pid, g in tracks.groupby("particle"):
        g = g.sort_values("frame")
        xy = g[["x", "y"]].to_numpy(float) * float(pixel_size_um)
        fr = g["frame"].to_numpy()
        _, _, d = _msd_and_fit_one(xy, fr, pid, lag_times, max_lagtime, n_fit,
                                   alpha_thresholds)
        rows.append(d)
    return pd.DataFrame(rows, columns=DIFF_COLUMNS)
