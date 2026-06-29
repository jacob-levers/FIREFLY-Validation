# FIREFLY-VERIFICATION

A standalone desktop app that grades **single-particle-tracking accuracy** of
[FIREFLY](https://github.com/jacob-levers/FIREFLY) and **palmTRACER** *output
files* against ground truth — the basis for validating FIREFLY's tracking
methodology and comparing it head-to-head with palmTRACER.

It uses the **ISBI-2012 Particle Tracking Challenge** metrics (Chenouard et al.,
*Nat. Methods* 2014): detection (precision / recall / F1 / Jaccard / RMSE),
tracking (α, β, JSC, track-JSC, RMSE) and diffusion recovery (recovered *D* and α
vs truth, motion confusion matrix). The same scoring code grades both tools, so
the comparison is symmetric.

Ground truth can be **imported** (plain CSV `track,frame,x,y` or ISBI-2012 XML) or
**simulated** in-app (known *D* / motion / density / noise, with an optional movie
so you can run both trackers on identical input).

## Layout
- `fireflyverify/scoring/` — the pure scoring engine (simulator + ISBI metrics +
  ground-truth loaders), migrated from FIREFLY's internal benchmark.
- `fireflyverify/adapters/` — parsers that read FIREFLY / palmTRACER / GT files
  into a common schema.
- `fireflyverify/ui/` — the QML front-end (shares FIREFLY's dark theme).

## Run
```bash
pip install -e .          # or: pip install -e ".[dev]"
python run_verify.py      # GUI
pytest -q                 # tests
```
