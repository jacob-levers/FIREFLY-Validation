"""Headless CLI for FIREFLY-VERIFICATION.

  fireflyverify score --gt GT [--firefly DIR] [--palmtracer DIR] [--csv OUT] [--pdf OUT]
  fireflyverify simulate --out DIR [--motion brownian|confined|directed|mixed] ...

`score` grades existing tool outputs against a ground-truth file (CSV / ISBI XML);
`simulate` writes a known-truth dataset (+ movie) so you can run the trackers on
identical input. Pure / Qt-free.
"""
from __future__ import annotations

import argparse
import os
import sys


def _cmd_score(a) -> int:
    from fireflyverify.adapters.firefly_output import load_firefly_output
    from fireflyverify.adapters.ground_truth import load_ground_truth
    from fireflyverify.adapters.palmtracer_output import load_palmtracer_output
    from fireflyverify.scoring import figures as figmod
    from fireflyverify.scoring.msdfit import compute_diff_from_tracks
    from fireflyverify.scoring.report import build_report_table, evaluate

    sim = load_ground_truth(a.gt, pixel_size_um=(a.pixel_size or None),
                            frame_interval_s=a.frame_interval, frame_base=a.frame_base,
                            stack_path=a.gt_stack)
    px, dt = sim.meta["pixel_size_um"], sim.meta["frame_interval_s"]

    tools = {}
    if a.firefly:
        tools["FIREFLY"] = load_firefly_output(a.firefly)
    if a.palmtracer:
        tools["palmTRACER"] = load_palmtracer_output(a.palmtracer)
    if not tools:
        print("error: pass --firefly and/or --palmtracer", file=sys.stderr)
        return 2

    rows = []
    for name in ("FIREFLY", "palmTRACER"):
        t = tools.get(name)
        if t is None:
            continue
        if a.common_refit:
            t.diff = compute_diff_from_tracks(t.tracks, px, dt)
        rows.append(evaluate(t, sim))

    print(build_report_table(rows).to_string(index=False))
    if a.csv:
        build_report_table(rows).to_csv(a.csv, index=False)
        print(f"\nwrote {a.csv}")
    if a.pdf:
        figmod.export_pdf(rows, sim, tools, a.pdf)
        print(f"wrote {a.pdf}")
    return 0


def _cmd_simulate(a) -> int:
    from fireflyverify.scoring import io as sio
    from fireflyverify.scoring.config import (_DEFAULT_POPULATIONS, DiffusionPopulation,
                                              SimConfig)
    from fireflyverify.scoring.simulator import simulate

    if a.motion == "confined":
        pops = (DiffusionPopulation("confined", 1.0, D_um2_s=a.D, confine_radius_um=0.15),)
    elif a.motion == "directed":
        pops = (DiffusionPopulation("directed", 1.0, D_um2_s=a.D, drift_vel_um_s=(0.5, 0.0)),)
    elif a.motion == "mixed":
        pops = _DEFAULT_POPULATIONS
    else:
        pops = (DiffusionPopulation("brownian", 1.0, D_um2_s=a.D),)

    sim = simulate(SimConfig(seed=a.seed, n_frames=a.frames, n_emitters=a.emitters,
                             populations=pops))
    os.makedirs(a.out, exist_ok=True)
    paths = sio.write_gt_csvs(sim, a.out)
    print(f"wrote ground truth: {paths['tracks']}")
    if sim.stack is not None:
        try:
            tif = sio.write_tiff(sim.stack, os.path.join(a.out, "sim_stack.tif"))
            print(f"wrote movie: {tif}")
        except Exception as e:
            print(f"(movie not written: {e})", file=sys.stderr)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="fireflyverify",
                                description="Single-particle-tracking accuracy grader.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("score", help="grade tool outputs against ground truth")
    s.add_argument("--gt", required=True, help="ground-truth CSV or ISBI-2012 XML")
    s.add_argument("--gt-stack", default=None, dest="gt_stack", help="optional image stack for XML")
    s.add_argument("--pixel-size", type=float, default=0.0, dest="pixel_size", help="µm/px (0=default)")
    s.add_argument("--frame-interval", type=float, default=0.02, dest="frame_interval", help="s/frame")
    s.add_argument("--frame-base", default="auto", choices=["auto", "0", "1"], dest="frame_base")
    s.add_argument("--firefly", default=None, help="FIREFLY output folder")
    s.add_argument("--palmtracer", default=None, help="palmTRACER output folder")
    s.add_argument("--common-refit", action="store_true", dest="common_refit",
                   help="recompute D for both tools with one fitter")
    s.add_argument("--csv", default=None, help="write the metric table to this CSV")
    s.add_argument("--pdf", default=None, help="write a PDF report")
    s.set_defaults(fn=_cmd_score)

    g = sub.add_parser("simulate", help="generate a known-truth dataset (+ movie)")
    g.add_argument("--out", required=True, help="output directory")
    g.add_argument("--seed", type=int, default=1)
    g.add_argument("--frames", type=int, default=200)
    g.add_argument("--emitters", type=int, default=60)
    g.add_argument("--D", type=float, default=0.10, help="diffusion coefficient (µm²/s)")
    g.add_argument("--motion", default="brownian",
                   choices=["brownian", "confined", "directed", "mixed"])
    g.set_defaults(fn=_cmd_simulate)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
