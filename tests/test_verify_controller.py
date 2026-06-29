"""VerifyController: simulate GT, load a (fake) FIREFLY output, score, render."""
import json
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import pandas as pd
import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])

from fireflyverify.ui.controllers.verify_controller import VerifyController


def _write_firefly(d, gt_tracks, px, dt, D_true=0.1):
    os.makedirs(d, exist_ok=True)
    trj = gt_tracks[["particle", "frame", "x", "y"]].copy()
    trj["mass"] = 1000.0
    trj.to_csv(os.path.join(d, "sim_trajectories.csv"), index=False)
    loc = gt_tracks[["x", "y", "frame"]].copy(); loc["mass"] = 1000.0
    loc.to_csv(os.path.join(d, "sim_localisations.csv"), index=False)
    diff = pd.DataFrame({"particle": sorted(gt_tracks["particle"].unique())})
    diff["D"] = D_true; diff["alpha"] = 1.0; diff["motion"] = "Brownian"
    diff.to_csv(os.path.join(d, "sim_diffusion_summary.csv"), index=False)
    json.dump({"parameters": {"pixel_size_um": px, "frame_interval_s": dt}},
              open(os.path.join(d, "sim_run_manifest.json"), "w"))


def test_full_flow(tmp_path):
    c = VerifyController()
    errors = []
    c.error.connect(lambda t, m: errors.append((t, m)))

    c.simulate({"seed": 4, "n_frames": 50, "height": 64, "width": 64,
                "n_emitters": 20, "k_on": 0.95, "k_off": 0.01, "bleach_prob": 0.0,
                "photon_cv": 0.0,
                "populations": [{"name": "brownian", "fraction": 1.0, "D_um2_s": 0.1}]})
    assert not errors, errors
    gt = c.gtSummary
    assert gt["loaded"] and gt["n_tracks"] > 0 and gt["has_truth_D"]

    px, dt = gt["pixel_size_um"], gt["frame_interval_s"]
    d = str(tmp_path / "ff")
    _write_firefly(d, c._gt.gt_tracks, px, dt)
    c.loadFirefly(d)
    assert c.methodsSummary["FIREFLY"]["loaded"]
    assert not errors, errors

    c.score(False)
    assert c.hasResults
    cards = c.scorecards
    assert len(cards) == 1 and cards[0]["tool"] == "FIREFLY"
    assert cards[0]["f1"] > 0.9 and cards[0]["jsc"] > 0.85
    # reported diffusion present, recovered D ≈ truth
    assert any(row["bias_pct"] is not None and abs(row["bias_pct"]) < 5
               for row in cards[0]["diffusion"])

    # figure rendered + retrievable via the provider getter
    c.renderFigure("summary", 800, 600)
    img = c.figure_image("summary")
    assert img is not None and not img.isNull()
    assert not errors, errors
