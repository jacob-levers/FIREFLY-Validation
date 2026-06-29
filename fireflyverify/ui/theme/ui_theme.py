"""Theme palettes for the FIREFLY-VERIFICATION QML UI (Dark / AMOLED / Light).

Copied from FIREFLY's `ui_theme` so the two apps share one look, trimmed to just
the palettes + startup-theme pick (the legacy Widgets QSS lived here too but isn't
needed by the QML front-end).
"""
from __future__ import annotations

from PySide6 import QtCore

_THEMES = {
    "Dark": {
        "BG":          "#090b0f",
        "PANEL":       "#0e1218",
        "PANEL_ALT":   "#151a22",
        "WELL":        "#05070a",
        "BORDER":      "#1d232c",
        "BORDER_HI":   "#2b333d",
        "TXT":         "#e6edf3",
        "TXT_MUTED":   "#8b949e",
        "ACC":         "#58a6ff",
        "ACC_HOVER":   "#79c0ff",
        "ACC_PRESSED": "#388bfd",
        "ACC_FG":      "#0d1117",
        "DANGER":      "#f85149",
        "SUCCESS":     "#56d364",
        "WARN":        "#f78166",
    },
    "AMOLED": {
        "BG":          "#000000",
        "PANEL":       "#0a0a0a",
        "PANEL_ALT":   "#141414",
        "WELL":        "#000000",
        "BORDER":      "#30363d",
        "BORDER_HI":   "#484f58",
        "TXT":         "#e6edf3",
        "TXT_MUTED":   "#8b949e",
        "ACC":         "#58a6ff",
        "ACC_HOVER":   "#79c0ff",
        "ACC_PRESSED": "#388bfd",
        "ACC_FG":      "#000000",
        "DANGER":      "#f85149",
        "SUCCESS":     "#56d364",
        "WARN":        "#f78166",
    },
    "Light": {
        "BG":          "#ffffff",
        "PANEL":       "#f6f8fa",
        "PANEL_ALT":   "#eaeef2",
        "WELL":        "#eef1f5",
        "BORDER":      "#d0d7de",
        "BORDER_HI":   "#afb8c1",
        "TXT":         "#24292f",
        "TXT_MUTED":   "#57606a",
        "ACC":         "#0969da",
        "ACC_HOVER":   "#218bff",
        "ACC_PRESSED": "#0550ae",
        "ACC_FG":      "#ffffff",
        "DANGER":      "#cf222e",
        "SUCCESS":     "#1f883d",
        "WARN":        "#9a6700",
    },
}

_SETTINGS_ORG = "jacoblevers"
_SETTINGS_APP = "FIREFLY-VERIFICATION"


def _pick_startup_theme() -> str:
    """Read the chosen app theme from this app's QSettings, defaulting to Dark."""
    try:
        s = QtCore.QSettings(_SETTINGS_ORG, _SETTINGS_APP)
        name = str(s.value("ui/app_theme", "Dark") or "Dark")
        if name in _THEMES:
            return name
    except Exception:
        pass
    return "Dark"
