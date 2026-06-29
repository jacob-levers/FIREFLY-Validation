"""End-to-end: simulate known truth → craft fake FIREFLY + palmTRACER outputs →
load via the adapters → score with the engine. Proves the adapters normalise to
the scoring schema (0-based frames, pixels) and that scoring is near-perfect on
un-jittered inputs (incl. the palmTRACER Plane→frame−1 round-trip)."""
import json
import os

import numpy as np
import pandas as pd

from fireflyverify.scoring.config import SimConfig, DiffusionPopulation
from fireflyverify.scoring.simulator import simulate
from fireflyverify.scoring.report import evaluate
from fireflyverify.scoring.msdfit import compute_diff_from_tracks
from fireflyverify.adapters.firefly_output import load_firefly_output
from fireflyverify.adapters.palmtracer_output import load_palmtracer_output

D_TRUE = 0.10


def _sim():
    # Long, mostly-ON Brownian tracks so D recovery is well-determined.
    cfg = SimConfig(seed=3, n_frames=60, height=64, width=64, n_emitters=25,
                    k_on=0.95, k_off=0.01, bleach_prob=0.0, photon_cv=0.0,
                    populations=(DiffusionPopulation("brownian", 1.0, D_um2_s=D_TRUE),))
    return simulate(cfg)


def _write_firefly(d, gt_tracks, px, dt):
    os.makedirs(d, exist_ok=True)
    stem = "sim"
    trj = gt_tracks[["particle", "frame", "x", "y"]].copy()
    trj["mass"] = 1000.0
    trj.to_csv(os.path.join(d, f"{stem}_trajectories.csv"), index=False)
    locs = gt_tracks[["x", "y", "frame"]].copy()
    locs["mass"] = 1000.0
    locs.to_csv(os.path.join(d, f"{stem}_localisations.csv"), index=False)
    diff = pd.DataFrame({"particle": sorted(gt_tracks["particle"].unique())})
    diff["D"] = D_TRUE
    diff["alpha"] = 1.0
    diff["motion"] = "Brownian"
    diff.to_csv(os.path.join(d, f"{stem}_diffusion_summary.csv"), index=False)
    with open(os.path.join(d, f"{stem}_run_manifest.json"), "w") as fh:
        json.dump({"parameters": {"pixel_size_um": px, "frame_interval_s": dt}}, fh)


def _write_palmtracer(d, gt_tracks, px, dt):
    """Write loc/trc with Plane = frame + 1 (1-based) so the adapter's −1 is tested."""
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "locPALMTracer.csv"), "w") as f:
        f.write("Pixel_Size(um),Frame_Duration(s)\n")
        f.write(f"{px},{dt}\n")
        f.write("id,Plane,Index,Channel,Integrated_Intensity,CentroidX(px),CentroidY(px)\n")
        for i, r in enumerate(gt_tracks.itertuples()):
            f.write(f"{i},{int(r.frame)+1},0,0,1000,{r.x},{r.y}\n")
    with open(os.path.join(d, "trcPALMTracer.csv"), "w") as f:
        f.write("Pixel_Size(um),Frame_Duration(s)\n")
        f.write(f"{px},{dt}\n")
        f.write("Track,Plane,CentroidX(px),CentroidY(px),CentroidZ(um),"
                "Integrated_Intensity,id,Pair_Distance(px)\n")
        for i, r in enumerate(gt_tracks.itertuples()):
            f.write(f"{int(r.particle)},{int(r.frame)+1},{r.x},{r.y},0,1000,{i},0\n")
    # native per-track D (palmTRACER's own) — constant D_true
    with open(os.path.join(d, "trcPALMTracer-AllROI-D.csv"), "w") as f:
        f.write("# Diffusion Coef in um2/s\n")
        f.write("ROI Trace D(um2/s) MSD(0) MSE\n")
        for pid in sorted(gt_tracks["particle"].unique()):
            f.write(f"1 {int(pid)} {D_TRUE} 0.0 0.0\n")


def test_firefly_adapter_and_scoring(tmp_path):
    sim = _sim()
    px, dt = sim.meta["pixel_size_um"], sim.meta["frame_interval_s"]
    d = str(tmp_path / "firefly_run")
    _write_firefly(d, sim.gt_tracks, px, dt)

    ff = load_firefly_output(d)
    assert ff.name == "FIREFLY"
    assert int(ff.tracks["frame"].min()) == 0
    assert ff.tracks["particle"].dtype.kind == "i"
    assert ff.meta["pixel_size_um"] == px and ff.meta["frame_interval_s"] == dt

    ev = evaluate(ff, sim)
    assert ev["f1"] > 0.95
    assert ev["jsc"] > 0.9
    assert ev["isbi_alpha"] > 0.9
    # reported D matches truth
    pop = ev["_detail"]["diffusion"]["per_population"]["brownian"]
    assert abs(pop["D_bias_pct"]) < 5.0


def test_palmtracer_adapter_plane_roundtrip_and_scoring(tmp_path):
    sim = _sim()
    px, dt = sim.meta["pixel_size_um"], sim.meta["frame_interval_s"]
    d = str(tmp_path / "palmtracer_run")
    _write_palmtracer(d, sim.gt_tracks, px, dt)

    pt = load_palmtracer_output(d)
    assert pt.name == "palmTRACER"
    # Plane was frame+1; the adapter must subtract 1 → 0-based, matching GT.
    assert int(pt.tracks["frame"].min()) == int(sim.gt_tracks["frame"].min()) == 0
    assert int(pt.tracks["frame"].max()) == int(sim.gt_tracks["frame"].max())
    assert pt.meta["pixel_size_um"] == px
    assert len(pt.diff) > 0 and abs(pt.diff["D"].median() - D_TRUE) < 1e-6

    ev = evaluate(pt, sim)
    assert ev["f1"] > 0.95
    assert ev["jsc"] > 0.9
    assert ev["isbi_alpha"] > 0.9


def test_common_refit_recovers_known_D(tmp_path):
    sim = _sim()
    px, dt = sim.meta["pixel_size_um"], sim.meta["frame_interval_s"]
    d = str(tmp_path / "ff")
    _write_firefly(d, sim.gt_tracks, px, dt)
    ff = load_firefly_output(d)
    # keep tracks long enough for a stable fit
    lens = ff.tracks.groupby("particle")["frame"].transform("size")
    long_tracks = ff.tracks[lens >= 20]
    diff = compute_diff_from_tracks(long_tracks, px, dt, max_lagtime=20, n_fit=8)
    med = diff["D"].dropna().median()
    assert abs(med - D_TRUE) / D_TRUE < 0.25
