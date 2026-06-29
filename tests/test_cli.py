"""CLI: `simulate` writes a known-truth dataset; `score` grades outputs + exports."""
import json
import os

import pandas as pd

from fireflyverify.cli import main
from fireflyverify.scoring.config import DiffusionPopulation, SimConfig
from fireflyverify.scoring.simulator import simulate


def _fake_firefly(d, gt_tracks, px=0.106, dt=0.02):
    os.makedirs(d, exist_ok=True)
    t = gt_tracks[["particle", "frame", "x", "y"]].copy(); t["mass"] = 1000.0
    t.to_csv(os.path.join(d, "s_trajectories.csv"), index=False)
    loc = gt_tracks[["x", "y", "frame"]].copy(); loc["mass"] = 1000.0
    loc.to_csv(os.path.join(d, "s_localisations.csv"), index=False)
    json.dump({"parameters": {"pixel_size_um": px, "frame_interval_s": dt}},
              open(os.path.join(d, "s_run_manifest.json"), "w"))


def test_simulate_writes_ground_truth(tmp_path):
    out = str(tmp_path / "sim")
    rc = main(["simulate", "--out", out, "--frames", "40", "--emitters", "12",
               "--motion", "brownian"])
    assert rc == 0
    assert os.path.isfile(os.path.join(out, "ground_truth_tracks.csv"))
    df = pd.read_csv(os.path.join(out, "ground_truth_tracks.csv"))
    assert {"particle", "frame", "x", "y"} <= set(df.columns)


def test_score_writes_csv_and_pdf(tmp_path):
    sim = simulate(SimConfig(seed=2, n_frames=50, height=64, width=64, n_emitters=20,
                             k_on=0.95, k_off=0.01, bleach_prob=0.0, photon_cv=0.0,
                             populations=(DiffusionPopulation("brownian", 1.0, D_um2_s=0.1),)))
    gt_csv = str(tmp_path / "gt.csv")
    sim.gt_tracks.rename(columns={"particle": "track"}).to_csv(gt_csv, index=False)
    ffdir = str(tmp_path / "ff")
    _fake_firefly(ffdir, sim.gt_tracks)
    out_csv = str(tmp_path / "report.csv")
    out_pdf = str(tmp_path / "report.pdf")

    rc = main(["score", "--gt", gt_csv, "--frame-base", "0", "--firefly", ffdir,
               "--csv", out_csv, "--pdf", out_pdf])
    assert rc == 0
    assert os.path.isfile(out_csv) and os.path.isfile(out_pdf)
    tbl = pd.read_csv(out_csv)
    assert "FIREFLY" in tbl["tool"].tolist()
    assert float(tbl.loc[tbl["tool"] == "FIREFLY", "f1"].iloc[0]) > 0.95
