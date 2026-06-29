"""Vendored MSD fitter recovers a known D / α on clean Brownian tracks."""
import numpy as np
import pandas as pd

from fireflyverify.scoring.msdfit import compute_diff_from_tracks, classify_motion


def test_recovers_known_brownian_D():
    rng = np.random.default_rng(0)
    D_true, dt, px = 0.10, 0.02, 0.106
    step = np.sqrt(2 * D_true * dt)            # per-axis µm std
    rows = []
    for pid in range(40):
        xy = np.cumsum(rng.normal(0, step, size=(80, 2)), axis=0)   # µm
        xy_px = xy / px + 50.0
        for f in range(80):
            rows.append((pid, f, xy_px[f, 0], xy_px[f, 1]))
    tr = pd.DataFrame(rows, columns=["particle", "frame", "x", "y"])
    diff = compute_diff_from_tracks(tr, px, dt, max_lagtime=20, n_fit=8)
    assert abs(diff["D"].median() - D_true) / D_true < 0.15
    assert abs(diff["alpha"].dropna().median() - 1.0) < 0.2


def test_classify_motion_thresholds():
    assert classify_motion(0.3) == "Immobile"
    assert classify_motion(0.7) == "Confined"
    assert classify_motion(1.0) == "Brownian"
    assert classify_motion(1.5) == "Directed"


def test_empty_tracks_returns_empty():
    diff = compute_diff_from_tracks(pd.DataFrame(columns=["particle", "frame", "x", "y"]),
                                    0.106, 0.02)
    assert len(diff) == 0
