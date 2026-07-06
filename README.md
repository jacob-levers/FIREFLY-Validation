# FIREFLY-Validation

**A standalone desktop app that grades single-particle-tracking (SPT) accuracy of
[FIREFLY](https://github.com/jacob-levers/FIREFLY) and palmTRACER against ground
truth — side by side.**

It exists to answer one question rigorously: *how accurately does a tracker recover
the truth?* You give it ground truth (imported, or simulated in-app with a known
answer) and the tracking output files from FIREFLY and/or palmTRACER, and it scores
each tool with the accepted community metrics — the same code grading both, so the
comparison is fair.

The scoring engine is the **ISBI-2012 Particle Tracking Challenge** methodology
(Chenouard et al., *Nature Methods* 2014) plus the **SMLM-challenge** detection
scoring (Sage et al., *Nature Methods* 2015) and a Mortensen-2010 CRLB reference
floor. Because the metrics are standard, applied symmetrically, and measured
against independent ground truth, the result is a credible basis for validating
FIREFLY's tracking — not a home-team scorecard.

It shares FIREFLY's dark themed UI and is intentionally light (PySide6 + numpy /
pandas / scipy / matplotlib / tifffile — no torch / trackpy / scikit-image).

---

## Table of contents
- [Install](#install)
- [The 60-second tour](#the-60-second-tour)
- [Step-by-step guide](#step-by-step-guide)
  - [1. Ground Truth](#1-ground-truth)
  - [2. Methods](#2-methods)
  - [3. Results](#3-results)
  - [4. Report](#4-report)
- [What every metric means](#what-every-metric-means)
- [The scoring / colour system](#the-scoring--colour-system)
- [File formats it reads](#file-formats-it-reads)
- [Command line](#command-line)
- [How the scoring works](#how-the-scoring-works)
- [Project layout](#project-layout)
- [Development](#development)
- [FAQ](#faq)

---

## Install

**Pre-built apps** (no Python needed) — from the [Releases page](https://github.com/jacob-levers/FIREFLY-Validation/releases):
- **macOS:** download `FIREFLY-Validation-macOS.dmg`, open it, drag the app to Applications.
  First launch: right-click → **Open** (unsigned build).
- **Windows:** download `FIREFLY-Validation-Windows.exe` and run it. First launch
  extracts to `%LOCALAPPDATA%` and is a little slower.

**From source** (Python ≥ 3.10):
```bash
git clone https://github.com/jacob-levers/FIREFLY-Validation.git
cd FIREFLY-Validation
pip install -e .          # or  pip install -e ".[dev]"  for the test extras
python run_verify.py      # launch the GUI
```

---

## The 60-second tour

1. **Ground Truth → Simulate** → pick a motion type + *D*, click **Generate**.
   You now have a dataset whose true tracks and true *D* are known exactly.
2. *(optional)* **Export movie + GT…** to write a TIFF + ground-truth CSVs, run
   FIREFLY and palmTRACER on that TIFF, and come back.
3. **Methods** → load the FIREFLY and/or palmTRACER output folder(s) → **Score**.
4. **Results** → read the side-by-side scorecard (every value colour-rated), hover
   anything you don't recognise, flip through the figures.
5. **Report** → export the comparison as CSV or a one-page PDF.

---

## Step-by-step guide

### 1. Ground Truth
Everything is scored *against* this, so it's the first thing you set. Two ways:

**Import file** — load ground truth you already have:
- **Plain CSV** with columns `track, frame, x, y` (column-name aliases like
  `particle`/`trajectory`, `t`, `x_nm`/`y_nm` are recognised).
- **ISBI-2012 XML** (`<particle><detection t= x= y=/></particle>`).
- Set **Pixel size (µm)** and **Frame interval (s)** so positional errors can be
  reported in nm and *D* in µm²/s.
- **Frame indexing** (`auto` / `0-based` / `1-based`) — the single most common
  source of silent error. `auto` shifts the minimum frame to 0; set it explicitly
  if your file's convention is known. The resolved choice is honoured exactly, not
  guessed silently.

**Simulate** — generate a known-truth dataset:
- **Motion**: Brownian / Confined / Directed / Mixed (a 4-class mixture).
- **D**, **Frames**, **Emitters**, **Photons**, **Background**, **Blink-off rate**,
  **Seed** (deterministic — same seed ⇒ identical data).
- **Generate** builds the ground truth; **Export movie + GT…** writes
  `sim_stack.tif` + `ground_truth_{locs,tracks}.csv` so you can run the real
  trackers on identical input.

The summary card confirms what loaded: source, track / localisation / frame counts,
pixel size, and **Truth D** (the actual coefficient, e.g. `0.1 µm²/s`, or `—` when
an imported file doesn't carry it).

### 2. Methods
Load the tools' **output folders** (the app reads their exported files — it does not
re-run the trackers):
- **FIREFLY** — point at the run folder (it finds `*_trajectories.csv`,
  `*_diffusion_summary.csv`, `*_run_manifest.json`).
- **palmTRACER** — point at the folder containing `locPALMTracer` / `trcPALMTracer`.

**Common re-fit** (toggle): recompute *D* for **both** tools with one identical MSD
fitter. Use this for an apples-to-apples *tracking-quality* comparison (it removes
differences that come purely from each tool's own *D*-fit), and to get a *D* for
palmTRACER when it didn't export native *D* values.

Press **Score vs ground truth** → jumps to Results.

### 3. Results
A `Metric | FIREFLY | palmTRACER` table. Every value is **colour-rated** by quality
and the better tool is obvious at a glance:
- **Detection** — F1, Jaccard, Precision, Recall, Loc RMSE (nm), Matched spots.
- **Tracking (ISBI-2012)** — α, β, JSC, JSCθ, Track RMSE (nm), Est. tracks.
- **Diffusion recovery** — per motion class: true *D*, recovered *D*, and % bias.
- **Figure** — switch between **Summary**, **D distribution**, **Confusion**, and
  **Track overlay** (each captioned).

**Hover** a metric name (it tints blue) for its plain-English meaning and the rating
bands; **hover** a value for its rating + meaning.

Below the table, a **provenance line** states the exact conditions the scores were
computed under — the resolved pixel size, the detection tolerance and tracking gate
(in nm), and any frame shift applied — so a run is auditable and reproducible. When a
**common re-fit** is on, each tool also shows its **MSD-fit outcomes** (e.g. *"312 fit ·
40 immobile · 5 failed"*), so a blank *D* is never mistaken for a silent solver failure.

### 4. Report
Export the whole comparison:
- **CSV** — the metric table plus the scoring-provenance columns
  (`pixel_size_um`, `match_tol_nm`, `track_gate_nm`) so results stay auditable.
- **PDF** — a one-page-per-panel report of the figures.

---

## What every metric means

### Detection — *did it find the right spots, frame by frame?*
Each detection is matched to a ground-truth spot within a tolerance radius (optimal
Hungarian assignment per frame).

| Metric | Meaning | Good |
|---|---|---|
| **Precision** | of reported spots, fraction that are real (1 − false-positive rate) | →1 |
| **Recall** | of true spots, fraction found (1 − miss rate) | →1 |
| **F1** | harmonic mean of precision & recall | →1 |
| **Jaccard** | TP / (TP + FP + FN) | →1 |
| **Loc RMSE (nm)** | RMS position error of matched spots | low; near the CRLB floor |
| **Matched spots** | count of detections paired to ground truth | (context) |

### Tracking — *did it link spots into the right trajectories?* (Chenouard 2014)
A global optimal assignment pairs estimated tracks to ground-truth tracks.

| Metric | Meaning | Good |
|---|---|---|
| **α (sensitivity)** | how much of the true tracks were recovered (1 = perfect) | →1 |
| **β** | α penalised for spurious (false) tracks; β ≤ α, the gap is the false-track burden | →1 |
| **JSC (points)** | track-point Jaccard: matched / (matched + missed + spurious) | →1 |
| **JSCθ (tracks)** | track-level Jaccard: whole tracks correctly matched | →1 |
| **Track RMSE (nm)** | position error along matched tracks | low |
| **Est. tracks** | trajectories produced (compare to the GT track count) | (context) |

### Diffusion recovery — *are the biophysics right?*
For each motion class, the recovered diffusion coefficient *D* vs the known truth:
**% bias = (recovered − true) / true**. Closer to 0 is better. (Available only when
ground truth carries the true *D* — i.e. the simulator — or via **Common re-fit**.)

---

## The scoring / colour system

Every value is rated against fixed bands; the colour, the rating word, and the
hover-tooltip all come from one source so they always agree:

| Score | 0–1 metrics (higher better) | RMSE (nm, lower better) |
|---|---|---|
| 🟢 **Excellent** | ≥ 0.90 | ≤ 15 |
| 🔵 **Good** | ≥ 0.75 | ≤ 30 |
| 🟡 **Fair** | ≥ 0.50 | ≤ 60 |
| 🔴 **Poor** | < 0.50 | > 60 |

Counts (Matched spots, Est. tracks) are shown neutral — compare them between tools
and to the ground-truth totals rather than rating them.

---

## File formats it reads

**FIREFLY output folder** — written by a FIREFLY run:
- `<stem>_trajectories.csv` — `particle, frame, x, y, mass` (frame 0-based; x/y in **pixels**)
- `<stem>_localisations.csv` — `x, y, frame, mass`
- `<stem>_diffusion_summary.csv` — `particle, D, alpha, motion, …`
- `<stem>_run_manifest.json` — supplies pixel size / frame interval

**palmTRACER output folder** (no stem prefix):
- `trcPALMTracer.txt|csv` — `Track, Plane, CentroidX(px), CentroidY(px), …`
  (**Plane is 1-based** → converted to 0-based on load)
- `locPALMTracer.txt|csv` — header carries `Pixel_Size(um)` / `Frame_Duration(s)`
- `trcPALMTracer-*-D.txt|csv` — optional native per-track *D*

**Ground truth** — plain CSV (`track, frame, x, y`) or ISBI-2012 XML.

All sources are normalised to one schema: integer 0-based `frame`, float `x`/`y` in
**pixels**, integer `particle`.

---

## Command line

Headless scoring + dataset generation (no GUI needed):

```bash
# Grade tool outputs against a ground-truth file; print the table, optionally export
fireflyverify score --gt ground_truth_tracks.csv \
                    --firefly path/to/firefly_run \
                    --palmtracer path/to/palmtracer_folder \
                    --common-refit --csv report.csv --pdf report.pdf

# Generate a known-truth dataset (+ movie) to run the trackers on
fireflyverify simulate --out sim_dataset --motion brownian --D 0.10 \
                       --frames 200 --emitters 60
```
Key `score` flags: `--pixel-size`, `--frame-interval`, `--frame-base {auto,0,1}`,
`--gt-stack` (image stack for an XML GT), `--common-refit`, `--csv`, `--pdf`.
(Equivalent to `python -m fireflyverify.cli …` from a source checkout.)

---

## How the scoring works

1. **Pairing.** Detections are matched to GT per frame, and estimated tracks to GT
   tracks globally, by optimal assignment (`scipy.optimize.linear_sum_assignment`)
   over a distance-gated, dummy-padded cost matrix — the Jaqaman/Chenouard scheme.
2. **Metrics.** Detection (precision/recall/F1/Jaccard/RMSE), tracking ISBI α/β/JSC/
   JSCθ/RMSE, and per-population diffusion recovery are computed from the pairings.
3. **CRLB floor.** The localisation-RMSE panel draws the Mortensen-2010 Cramér-Rao
   bound — the best position precision physically achievable at that photon budget.
4. **Symmetry.** FIREFLY and palmTRACER go through the *identical* code path; nothing
   about the scoring favours either tool.

References: Chenouard et al., *Nat. Methods* 11:281 (2014); Sage et al.,
*Nat. Methods* 12:717 (2015); Mortensen et al., *Nat. Methods* 7:377 (2010).

---

## Project layout
```
fireflyverify/
  scoring/     pure engine — simulator, ISBI metrics, GT loaders, figures, MSD fit
  adapters/    parsers: FIREFLY / palmTRACER / ground-truth → common schema
  ui/          QML front-end (shares FIREFLY's theme) + controllers
  cli.py       headless score / simulate
tests/         scoring, adapters, end-to-end, GUI smoke
fireflyverify.spec        PyInstaller spec (.app / .exe)
.github/workflows/        tests + tag-triggered distributable builds
```
The scoring engine was migrated out of FIREFLY's internal benchmark so it lives in
one independent, auditable place — no dependency on the FIREFLY package.

---

## Development
```bash
pip install -e ".[dev]"
QT_QPA_PLATFORM=offscreen pytest -q     # full suite (GUI tests skip without PySide6)
python run_verify.py                    # GUI
pyinstaller fireflyverify.spec --noconfirm --clean   # build the .app/.exe locally
```
Tag a release to build + publish the DMG + EXE:
```bash
git tag v0.2.0 && git push --tags       # fires .github/workflows/build.yml
```

---

## FAQ

**Does it run FIREFLY/palmTRACER for me?** No — it grades their *exported output*.
This keeps the validator independent of either tool's runtime. Use the simulator's
"Export movie + GT" to run the trackers on identical input, then load their outputs.

**Why does an imported ground truth show "Truth D —"?** A plain track file doesn't
carry the diffusion coefficient that generated it. Detection + tracking are still
scored; for a *D* comparison, simulate the truth or enable **Common re-fit**.

**palmTRACER shows "no reported D".** It didn't export native *D* values — turn on
**Common re-fit** to recompute *D* for both tools with one fitter.

**Is this biased toward FIREFLY?** No: standard published metrics, the same code for
both tools, scored against independent ground truth you control.
