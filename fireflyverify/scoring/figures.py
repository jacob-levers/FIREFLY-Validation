"""Dark-themed comparison figures (pyplot-free, matplotlib OO Agg).

Each renderer takes the evaluate `rows`, the ground-truth `SimResult`, and a
`tools` dict {name: ToolResult}, and returns PNG bytes. Colours match the app's
dark theme so the figures sit cohesively inside the QML UI.
"""
from __future__ import annotations

import io as _io

import numpy as np

from fireflyverify.scoring.metrics import crlb_sigma_nm

_BG = "#0e1218"
_PANEL = "#151a22"
_TXT = "#e6edf3"
_MUTED = "#8b949e"
_GRID = "#1d232c"
_TOOL_COLOURS = {"FIREFLY": "#58a6ff", "palmTRACER": "#f6a623"}
_SERIES = ["#58a6ff", "#f6a623", "#4fe0a0", "#27c0e8"]


def _new_fig(w_px, h_px):
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    dpi = 100.0
    fig = Figure(figsize=(max(w_px, 320) / dpi, max(h_px, 240) / dpi), dpi=dpi)
    FigureCanvasAgg(fig)
    fig.patch.set_facecolor(_BG)
    return fig


def _style(ax, title=""):
    ax.set_facecolor(_PANEL)
    for s in ax.spines.values():
        s.set_color(_GRID)
    ax.tick_params(colors=_MUTED, labelsize=8)
    ax.grid(True, color=_GRID, lw=0.6, alpha=0.6)
    ax.set_axisbelow(True)
    if title:
        ax.set_title(title, color=_TXT, fontsize=10)
    return ax


def _colour(tool, i):
    return _TOOL_COLOURS.get(tool, _SERIES[i % len(_SERIES)])


def _to_png(fig):
    buf = _io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor())
    return buf.getvalue()


def _grouped_bars(ax, tools, series: dict, ylim=None):
    n = len(series)
    x = np.arange(len(tools))
    w = 0.8 / max(n, 1)
    for i, (label, vals) in enumerate(series.items()):
        ax.bar(x + i * w - 0.4 + w / 2, vals, w, label=label,
               color=_SERIES[i % len(_SERIES)])
    ax.set_xticks(x)
    ax.set_xticklabels(tools, color=_TXT, fontsize=9)
    if ylim:
        ax.set_ylim(*ylim)
    leg = ax.legend(fontsize=8, frameon=False, labelcolor=_TXT)
    if leg:
        pass


def render_summary(rows, sim, tools, w, h):
    tool_names = [r["tool"] for r in rows]
    fig = _new_fig(w, h)
    axes = fig.subplots(2, 2)
    _style(axes[0, 0], "Detection  F1 / Jaccard")
    _grouped_bars(axes[0, 0], tool_names,
                  {"F1": [r["f1"] for r in rows], "Jaccard": [r["jaccard"] for r in rows]},
                  ylim=(0, 1.05))
    _style(axes[0, 1], "Tracking  α / β / JSC")
    _grouped_bars(axes[0, 1], tool_names,
                  {"α": [r["isbi_alpha"] for r in rows], "β": [r["isbi_beta"] for r in rows],
                   "JSC": [r["jsc"] for r in rows]}, ylim=(0, 1.05))
    # localisation RMSE vs CRLB floor
    ax = _style(axes[1, 0], "Localisation RMSE (nm)")
    ax.bar(tool_names, [r["rmse_nm"] for r in rows],
           color=[_colour(t, i) for i, t in enumerate(tool_names)])
    meta = sim.meta
    crlb = crlb_sigma_nm(meta.get("photons_per_emitter", 0), meta.get("bg_photons", 0),
                         meta.get("psf_sigma_px", 1.0), meta.get("pixel_size_um", 0.1))
    if np.isfinite(crlb):
        ax.axhline(crlb, color="#f85149", ls="--", lw=1.2, label=f"CRLB ≈ {crlb:.0f} nm")
        ax.legend(fontsize=8, frameon=False, labelcolor=_TXT)
    # precision–recall
    ax = _style(axes[1, 1], "Detection precision–recall")
    for i, r in enumerate(rows):
        ax.scatter(r["recall"], r["precision"], s=60, color=_colour(r["tool"], i),
                   label=r["tool"])
    ax.set_xlim(0, 1.05); ax.set_ylim(0, 1.05)
    ax.set_xlabel("recall", color=_MUTED, fontsize=8)
    ax.set_ylabel("precision", color=_MUTED, fontsize=8)
    ax.legend(fontsize=8, frameon=False, labelcolor=_TXT)
    return _to_png(fig)


def render_d_dist(rows, sim, tools, w, h):
    """Per-tool recovered-D histograms with truth lines (when known)."""
    fig = _new_fig(w, h)
    ax = _style(fig.subplots(), "Recovered diffusion coefficient")
    truth = {k.lower(): v.get("D_um2_s") for k, v in sim.meta.get("populations", {}).items()}
    any_data = False
    for i, r in enumerate(rows):
        diff = tools.get(r["tool"]).diff if tools.get(r["tool"]) is not None else None
        if diff is None or "D" not in getattr(diff, "columns", []):
            continue
        d = np.asarray(diff["D"], float)
        d = d[np.isfinite(d) & (d > 0)]
        if not len(d):
            continue
        any_data = True
        ax.hist(d, bins=24, alpha=0.55, color=_colour(r["tool"], i), label=r["tool"])
    for j, (name, D) in enumerate(truth.items()):
        if D and D > 0:
            ax.axvline(D, color="#56d364", ls="--", lw=1.1,
                       label=f"{name} truth D={D:g}")
    ax.set_xlabel("D (µm²/s)", color=_MUTED, fontsize=8)
    ax.set_ylabel("tracks", color=_MUTED, fontsize=8)
    if any_data or truth:
        ax.legend(fontsize=8, frameon=False, labelcolor=_TXT)
    else:
        ax.text(0.5, 0.5, "no reported D — enable common re-fit",
                ha="center", va="center", color=_MUTED, transform=ax.transAxes)
    return _to_png(fig)


def render_confusion(rows, sim, tools, w, h):
    """Motion-class confusion heatmap per tool (true → estimated)."""
    classes = ["Immobile", "Confined", "Brownian", "Directed"]
    fig = _new_fig(w, h)
    axes = fig.subplots(1, max(1, len(rows)))
    if len(rows) == 1:
        axes = [axes]
    for ax, r in zip(np.atleast_1d(axes), rows):
        _style(ax, f"{r['tool']} motion classes")
        conf = r["_detail"]["diffusion"]["confusion"]
        M = np.zeros((len(classes), len(classes)))
        for ti, tcl in enumerate(classes):
            for ei, ecl in enumerate(classes):
                M[ti, ei] = conf.get(tcl, {}).get(ecl, 0)
        im = ax.imshow(M, cmap="cividis", aspect="auto")
        ax.set_xticks(range(len(classes))); ax.set_yticks(range(len(classes)))
        ax.set_xticklabels(classes, rotation=45, ha="right", color=_MUTED, fontsize=7)
        ax.set_yticklabels(classes, color=_MUTED, fontsize=7)
        ax.set_xlabel("estimated", color=_MUTED, fontsize=8)
        ax.set_ylabel("true", color=_MUTED, fontsize=8)
        for ti in range(len(classes)):
            for ei in range(len(classes)):
                if M[ti, ei]:
                    ax.text(ei, ti, int(M[ti, ei]), ha="center", va="center",
                            color="#000000" if M[ti, ei] > M.max() * 0.5 else _TXT,
                            fontsize=8)
    return _to_png(fig)


def render_overlay(rows, sim, tools, w, h):
    """GT tracks vs the first tool's tracks (matched/missed/spurious by pairing)."""
    fig = _new_fig(w, h)
    ax = _style(fig.subplots(), "Trajectory overlay (GT vs estimate)")
    gt = sim.gt_tracks
    for _, g in gt.groupby("particle"):
        ax.plot(g["x"], g["y"], color=_MUTED, lw=0.8, alpha=0.7)
    if rows:
        r = rows[0]
        tr = tools.get(r["tool"])
        if tr is not None:
            paired_est = {e for _, e in r["_detail"]["tracking"].get("pairs", [])}
            for pid, g in tr.tracks.groupby("particle"):
                col = _colour(r["tool"], 0) if pid in paired_est else "#f85149"
                ax.plot(g["x"], g["y"], color=col, lw=1.0, alpha=0.9)
            ax.plot([], [], color=_MUTED, label="ground truth")
            ax.plot([], [], color=_colour(r["tool"], 0), label=f"{r['tool']} matched")
            ax.plot([], [], color="#f85149", label="spurious")
            ax.legend(fontsize=8, frameon=False, labelcolor=_TXT)
    ax.set_xlabel("x (px)", color=_MUTED, fontsize=8)
    ax.set_ylabel("y (px)", color=_MUTED, fontsize=8)
    ax.set_aspect("equal", adjustable="datalim")
    ax.invert_yaxis()
    return _to_png(fig)


_RENDERERS = {
    "summary": render_summary,
    "d_dist": render_d_dist,
    "confusion": render_confusion,
    "overlay": render_overlay,
}


def render(kind, rows, sim, tools, w, h) -> bytes:
    fn = _RENDERERS.get(kind, render_summary)
    return fn(rows, sim, tools, w, h)
