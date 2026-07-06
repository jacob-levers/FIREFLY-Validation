"""VerifyController — bridges the QML UI to the scoring engine.

Owns the ground truth (imported or simulated), the loaded tool outputs (FIREFLY /
palmTRACER), the scoring results, and the rendered figures. All heavy work is
synchronous (benchmark datasets are small); a `busy` flag is exposed for a later
move to a worker thread.
"""
from __future__ import annotations

import os
import traceback

import numpy as np
from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtGui import QImage

from fireflyverify.adapters.firefly_output import load_firefly_output
from fireflyverify.adapters.ground_truth import load_ground_truth
from fireflyverify.adapters.palmtracer_output import load_palmtracer_output
from fireflyverify.constants import DEFAULT_DT_S, DEFAULT_PX_UM
from fireflyverify.scoring import figures as figmod
from fireflyverify.scoring import io as scoring_io
from fireflyverify.scoring.config import DiffusionPopulation, SimConfig
from fireflyverify.scoring.msdfit import (compute_diff_from_tracks,
                                          summarize_fit_status)
from fireflyverify.scoring.report import build_report_table, evaluate
from fireflyverify.scoring.simulator import simulate


def _path(s):
    """Accept a plain path or a file:// URL (QML FileDialog gives URLs)."""
    s = str(s or "")
    if s.startswith("file:"):
        return QUrl(s).toLocalFile()
    return s


def _f(x):
    try:
        v = float(x)
        return v if np.isfinite(v) else None
    except (TypeError, ValueError):
        return None


_FIT_STATUS_LABELS = {"ok": "fit", "immobile": "immobile",
                      "linear_fallback": "linear fallback", "failed": "failed",
                      "too_short": "too short"}


def _fit_status_text(counts: dict) -> str:
    """"312 fit · 40 immobile · 5 failed" from a {status: count} map (common
    re-fit only). Empty → "" so the UI can hide the line."""
    if not counts:
        return ""
    return " · ".join(f"{counts[k]} {_FIT_STATUS_LABELS.get(k, k)}"
                      for k in _FIT_STATUS_LABELS if counts.get(k))


class VerifyController(QObject):
    groundTruthChanged = Signal()
    methodsChanged = Signal()
    resultsChanged = Signal()
    figureChanged = Signal()
    busyChanged = Signal()
    error = Signal(str, str)              # title, message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._gt = None                   # SimResult
        self._gt_source = ""
        self._tools = {}                  # name -> ToolResult
        self._rows = []                   # evaluate dicts
        self._figures = {}                # kind -> QImage
        self._fig_token = 0
        self._busy = False
        self._fit_status = {}             # name -> {status: count} from common re-fit
        self._imp_px = 0.0                 # import calibration (0 → default/auto)
        self._imp_dt = DEFAULT_DT_S
        self._imp_base = "auto"            # frame indexing: auto | 0 | 1

    # ── busy ──────────────────────────────────────────────────────────────
    def _set_busy(self, on):
        if on != self._busy:
            self._busy = on
            self.busyChanged.emit()

    @Property(bool, notify=busyChanged)
    def busy(self):
        return self._busy

    def _fail(self, title, exc):
        self.error.emit(title, str(exc))

    # ── ground truth ──────────────────────────────────────────────────────
    @Slot(str)
    @Slot(str, float, float, str)
    def importGroundTruthCsv(self, path, pixel_size_um=0.0,
                             frame_interval_s=DEFAULT_DT_S, frame_base="auto"):
        try:
            self._gt = load_ground_truth(
                _path(path), pixel_size_um=(pixel_size_um or None),
                frame_interval_s=(frame_interval_s or DEFAULT_DT_S),
                frame_base=frame_base)
            self._gt_source = "CSV: " + os.path.basename(_path(path))
            self._after_gt()
        except Exception as e:
            self._fail("Couldn't import ground-truth CSV", e)

    @Slot(str)
    @Slot(str, str, float, float)
    def importGroundTruthXml(self, path, stack_path="", pixel_size_um=0.0,
                             frame_interval_s=DEFAULT_DT_S):
        try:
            self._gt = load_ground_truth(
                _path(path), pixel_size_um=(pixel_size_um or None),
                frame_interval_s=(frame_interval_s or DEFAULT_DT_S),
                stack_path=(_path(stack_path) or None))
            self._gt_source = "ISBI XML: " + os.path.basename(_path(path))
            self._after_gt()
        except Exception as e:
            self._fail("Couldn't import ISBI XML", e)

    @Slot("QVariantMap")
    def simulate(self, cfg):
        try:
            self._gt = simulate(self._sim_config(dict(cfg)))
            self._gt_source = "Simulated"
            self._after_gt()
        except Exception as e:
            traceback.print_exc()
            self._fail("Simulation failed", e)

    def _sim_config(self, m):
        pops = []
        for p in (m.get("populations") or []):
            p = dict(p)
            drift = p.get("drift_vel_um_s")
            pops.append(DiffusionPopulation(
                name=str(p.get("name", "brownian")),
                fraction=float(p.get("fraction", 1.0)),
                D_um2_s=float(p.get("D_um2_s", 0.0)),
                alpha=float(p.get("alpha", 1.0)),
                confine_radius_um=(float(p["confine_radius_um"])
                                   if p.get("confine_radius_um") else None),
                drift_vel_um_s=(tuple(drift) if drift else None)))
        if not pops:
            pops = [DiffusionPopulation("brownian", 1.0, D_um2_s=0.1)]
        keys = ("seed", "n_frames", "height", "width", "pixel_size_um",
                "frame_interval_s", "n_emitters", "photons_per_emitter",
                "bg_photons", "k_on", "k_off", "bleach_prob", "photon_cv")
        kw = {k: m[k] for k in keys if k in m and m[k] is not None}
        # coerce ints/floats sensibly
        for k in ("seed", "n_frames", "height", "width", "n_emitters"):
            if k in kw:
                kw[k] = int(kw[k])
        for k in ("pixel_size_um", "frame_interval_s", "photons_per_emitter",
                  "bg_photons", "k_on", "k_off", "bleach_prob", "photon_cv"):
            if k in kw:
                kw[k] = float(kw[k])
        return SimConfig(populations=tuple(pops), **kw)

    @Slot(str)
    def exportSimMovieAndGt(self, out_dir):
        try:
            d = _path(out_dir)
            if self._gt is None:
                raise RuntimeError("Generate or import a ground truth first.")
            os.makedirs(d, exist_ok=True)
            scoring_io.write_gt_csvs(self._gt, d)
            if getattr(self._gt, "stack", None) is not None:
                scoring_io.write_tiff(self._gt.stack, os.path.join(d, "sim_stack.tif"))
        except Exception as e:
            self._fail("Export failed", e)

    def _after_gt(self):
        self._rows = []
        self._figures = {}
        self.groundTruthChanged.emit()
        self.resultsChanged.emit()

    @Property("QVariantMap", notify=groundTruthChanged)
    def gtSummary(self):
        if self._gt is None:
            return {"loaded": False}
        gt = self._gt
        # Show the actual known diffusion coefficient(s) when the dataset carries
        # them (the simulator does; imported CSV/XML usually don't).
        pops = gt.meta.get("populations") or {}
        Ds = []
        for p in pops.values():
            try:
                Ds.append(float(p.get("D_um2_s")))
            except (TypeError, ValueError):
                pass
        if not Ds:
            truth_d, truth_d_unit = "", ""
        elif len(Ds) == 1:
            truth_d, truth_d_unit = f"{Ds[0]:g}", "µm²/s"
        else:
            lo, hi = min(Ds), max(Ds)
            rng = f"{lo:g}" if lo == hi else f"{lo:g}–{hi:g}"
            truth_d, truth_d_unit = f"{rng} µm²/s · {len(Ds)} classes", ""
        meta = gt.meta
        return {
            "loaded": True, "source": self._gt_source,
            "n_tracks": int(gt.gt_tracks["particle"].nunique()) if len(gt.gt_tracks) else 0,
            "n_locs": int(len(gt.gt_locs)),
            "n_frames": int(meta.get("n_frames", (gt.gt_locs["frame"].max() + 1) if len(gt.gt_locs) else 0)),
            "pixel_size_um": float(meta.get("pixel_size_um", 0.0)),
            "frame_interval_s": float(meta.get("frame_interval_s", 0.0)),
            "has_truth_D": bool(pops),
            "truth_d": truth_d, "truth_d_unit": truth_d_unit,
            # scoring provenance — the conditions this GT was resolved under, so a
            # silent frame shift / defaulted-or-inferred pixel size is visible.
            "frame_offset": int(meta.get("frame_offset", 0)),
            "pixel_size_source": str(meta.get("pixel_size_source", "given")),
            "pixel_size_inferred": bool(meta.get("pixel_size_inferred", False)),
            "photon_budget_assumed": bool(meta.get("photon_budget_assumed", False)),
        }

    # ── native pickers (keep the QML free of file dialogs) ────────────────
    @Slot(float)
    def setImportPixelSize(self, v):
        self._imp_px = float(v or 0.0)

    @Slot(float)
    def setImportFrameInterval(self, v):
        self._imp_dt = float(v or DEFAULT_DT_S)

    @Slot(str)
    def setImportFrameBase(self, v):
        self._imp_base = str(v or "auto")

    @Slot()
    def chooseGroundTruth(self):
        from PySide6 import QtWidgets
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            None, "Open ground truth", os.path.expanduser("~"),
            "Ground truth (*.csv *.xml);;All files (*)")
        if not path:
            return
        if path.lower().endswith(".xml"):
            self.importGroundTruthXml(path, "", self._imp_px, self._imp_dt)
        else:
            self.importGroundTruthCsv(path, self._imp_px, self._imp_dt, self._imp_base)

    @Slot()
    def chooseFireflyFolder(self):
        from PySide6 import QtWidgets
        d = QtWidgets.QFileDialog.getExistingDirectory(
            None, "Open FIREFLY output folder", os.path.expanduser("~"))
        if d:
            self.loadFirefly(d)

    @Slot()
    def choosePalmtracerFolder(self):
        from PySide6 import QtWidgets
        d = QtWidgets.QFileDialog.getExistingDirectory(
            None, "Open palmTRACER output folder", os.path.expanduser("~"))
        if d:
            self.loadPalmtracer(d)

    @Slot()
    def chooseExportSimDir(self):
        from PySide6 import QtWidgets
        d = QtWidgets.QFileDialog.getExistingDirectory(
            None, "Export simulated movie + ground truth to…", os.path.expanduser("~"))
        if d:
            self.exportSimMovieAndGt(d)

    @Slot(str)
    def chooseReportPath(self, kind):
        from PySide6 import QtWidgets
        if kind == "pdf":
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                None, "Export PDF report", os.path.expanduser("~/comparison.pdf"),
                "PDF (*.pdf)")
            if path:
                self.exportReportPdf(path)
        else:
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                None, "Export CSV report", os.path.expanduser("~/comparison.csv"),
                "CSV (*.csv)")
            if path:
                self.exportReportCsv(path)

    # ── methods (tool outputs) ────────────────────────────────────────────
    @Slot(str)
    def loadFirefly(self, path):
        try:
            self._tools["FIREFLY"] = load_firefly_output(_path(path))
            self.methodsChanged.emit()
        except Exception as e:
            self._fail("Couldn't load FIREFLY output", e)

    @Slot(str)
    def loadPalmtracer(self, folder):
        try:
            self._tools["palmTRACER"] = load_palmtracer_output(_path(folder))
            self.methodsChanged.emit()
        except Exception as e:
            self._fail("Couldn't load palmTRACER output", e)

    def _tool_summary(self, name):
        t = self._tools.get(name)
        if t is None:
            return {"loaded": False, "name": name}
        return {"loaded": True, "name": name,
                "n_tracks": int(t.tracks["particle"].nunique()) if len(t.tracks) else 0,
                "n_locs": int(len(t.locs)),
                "has_D": bool(len(t.diff) and "D" in t.diff.columns)}

    @Property("QVariantMap", notify=methodsChanged)
    def methodsSummary(self):
        return {"FIREFLY": self._tool_summary("FIREFLY"),
                "palmTRACER": self._tool_summary("palmTRACER")}

    # ── scoring ───────────────────────────────────────────────────────────
    @Slot()
    @Slot(bool)
    def score(self, common_refit=False):
        if self._gt is None:
            self._fail("Nothing to score", "Load or simulate a ground truth first.")
            return
        if not self._tools:
            self._fail("Nothing to score", "Load at least one method output first.")
            return
        self._set_busy(True)
        try:
            px = self._gt.meta.get("pixel_size_um", DEFAULT_PX_UM)
            dt = self._gt.meta.get("frame_interval_s", DEFAULT_DT_S)
            rows = []
            fit_status = {}
            for name in ("FIREFLY", "palmTRACER"):
                t = self._tools.get(name)
                if t is None:
                    continue
                if common_refit:
                    t.diff = compute_diff_from_tracks(t.tracks, px, dt)
                    fit_status[name] = summarize_fit_status(t.diff)
                rows.append(evaluate(t, self._gt))
            self._rows = rows
            self._fit_status = fit_status
            self._figures = {}
            self.resultsChanged.emit()
            self.renderFigure("summary", 900, 640)
        except Exception as e:
            traceback.print_exc()
            self._fail("Scoring failed", e)
        finally:
            self._set_busy(False)

    @Property("QVariantList", notify=resultsChanged)
    def scorecards(self):
        cards = []
        for r in self._rows:
            pops = r["_detail"]["diffusion"]["per_population"]
            diff_rows = [{"pop": k, "D_true": _f(v.get("D_true")),
                          "D_est": _f(v.get("D_est_median")),
                          "bias_pct": _f(v.get("D_bias_pct")),
                          "alpha": _f(v.get("alpha_est_median")), "n": int(v.get("n", 0))}
                         for k, v in pops.items()]
            cards.append({
                "tool": r["tool"],
                "f1": _f(r["f1"]), "jaccard": _f(r["jaccard"]),
                "precision": _f(r["precision"]), "recall": _f(r["recall"]),
                "rmse_nm": _f(r["rmse_nm"]), "n_matched": int(r["n_matched"]),
                "alpha": _f(r["isbi_alpha"]), "beta": _f(r["isbi_beta"]),
                "jsc": _f(r["jsc"]), "jsc_theta": _f(r["jsc_theta"]),
                "track_rmse_nm": _f(r["isbi_rmse_nm"]), "n_tracks": int(r["n_tracks"]),
                "diffusion": diff_rows,
                "fit_status": _fit_status_text(self._fit_status.get(r["tool"], {})),
            })
        return cards

    @Property(bool, notify=resultsChanged)
    def hasResults(self):
        return bool(self._rows)

    @Property("QVariantMap", notify=resultsChanged)
    def scoreProvenance(self):
        """The conditions the scores were computed under (matching tolerance /
        tracking gate, resolved pixel size, frame offset), so the numbers are
        auditable in the UI — mirrors what the CSV/PDF report carries."""
        if not self._rows:
            return {"has": False}
        p = self._rows[0].get("_provenance", {})
        return {
            "has": True,
            "pixel_size_um": float(p.get("pixel_size_um", 0.0)),
            "match_tol_nm": float(p.get("match_tol_nm", 0.0)),
            "track_gate_nm": float(p.get("track_gate_nm", 0.0)),
            "frame_offset": int(p.get("frame_offset", 0)),
            "pixel_size_inferred": bool(p.get("pixel_size_inferred", False)),
            "pixel_size_source": str(p.get("pixel_size_source", "given")),
            "photon_budget_assumed": bool(p.get("photon_budget_assumed", False)),
        }

    # ── figures ───────────────────────────────────────────────────────────
    @Property(int, notify=figureChanged)
    def figureToken(self):
        return self._fig_token

    @Slot(str, int, int)
    def renderFigure(self, kind, w, h):
        if not self._rows or self._gt is None:
            return
        try:
            png = figmod.render(kind, self._rows, self._gt, self._tools,
                                int(w) or 800, int(h) or 600)
            img = QImage.fromData(png, "PNG")
            self._figures[kind] = img
            self._fig_token += 1
            self.figureChanged.emit()
        except Exception as e:
            traceback.print_exc()
            self._fail("Figure render failed", e)

    def figure_image(self, kind):
        return self._figures.get(kind)

    # ── report export ─────────────────────────────────────────────────────
    @Slot(str)
    def exportReportCsv(self, path):
        try:
            build_report_table(self._rows).to_csv(_path(path), index=False)
        except Exception as e:
            self._fail("CSV export failed", e)

    @Slot(str)
    def exportReportPdf(self, path):
        try:
            if not self._rows or self._gt is None:
                raise RuntimeError("Score the methods before exporting.")
            figmod.export_pdf(self._rows, self._gt, self._tools, _path(path))
        except Exception as e:
            traceback.print_exc()
            self._fail("PDF export failed", e)
