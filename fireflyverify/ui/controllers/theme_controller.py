"""ThemeController — the single source of design tokens for the QML UI.

Adapted from FIREFLY's ThemeController so this app shares the same palette + scale
tokens. Exposed to QML as `Theme`; `palette` re-emits on `setTheme`/`setAccent` so
every binding re-evaluates (live theme/accent switching). Prefs live in this app's
own QSettings store (`jacoblevers / FIREFLY-VERIFICATION`).
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Property, QSettings, Signal, Slot

from fireflyverify.ui.theme.ui_theme import _THEMES, _pick_startup_theme

_ORG, _APP = "jacoblevers", "FIREFLY-VERIFICATION"


def _store() -> QSettings:
    return QSettings(_ORG, _APP)


def _font_mult(label):
    import re
    m = re.search(r"(\d+)\s*px", str(label or ""))
    if m:
        return max(0.7, min(1.6, int(m.group(1)) / 12.0))
    lo = str(label or "").lower()
    return 11 / 12 if "small" in lo else 14 / 12 if "large" in lo else 1.0


def _density_mult(label):
    lo = str(label or "").lower()
    if "comfortable" in lo:
        return 1.18
    if "spacious" in lo:
        return 1.32
    return 1.0


class ThemeController(QObject):
    changed = Signal()
    scaleChanged = Signal()
    accentChanged = Signal()
    reducedMotionChanged = Signal()

    _SCALE = {
        "sp1": 2, "sp2": 4, "sp3": 6, "sp4": 8, "sp5": 10, "sp6": 12,
        "sp8": 16, "sp10": 20, "sp12": 24, "sp16": 32, "sp20": 40, "sp24": 48,
        "radiusXs": 3, "radiusSm": 4, "radiusMd": 5, "radiusLg": 6,
        "radiusXl": 8, "radius2xl": 10, "radiusPill": 999,
        "borderWidth": 1, "borderAccent": 3, "borderFocus": 2,
        "textXs": 11, "textSm": 12, "textMd": 13, "textLg": 14,
        "textXl": 18, "text2xl": 28,
        "displaySm": 22, "displayMd": 34, "displayLg": 54, "displayXl": 88,
        "weightRegular": 400, "weightMedium": 500, "weightSemibold": 600,
        "weightBold": 700, "weightHeavy": 800,
        "eyebrowTracking": 0.18, "sidebarWidth": 380,
    }

    _ACCENTS = [
        {"name": "Luminous blue",  "v": "#58a6ff", "h": "#79c0ff", "p": "#388bfd"},
        {"name": "Firefly amber",  "v": "#f6a623", "h": "#ffc65c", "p": "#d98e10"},
        {"name": "Motion green",   "v": "#4fe0a0", "h": "#7ef0bd", "p": "#33c084"},
        {"name": "Detection cyan", "v": "#27c0e8", "h": "#5fd4f0", "p": "#15a3c8"},
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._name = _pick_startup_theme()
        s = _store()
        try:
            self._reduced_motion = s.value("ui/reduce_motion", False, type=bool)
        except Exception:
            self._reduced_motion = False
        self._accent = "Luminous blue"
        try:
            a = s.value("ui/accent", "Luminous blue")
            if any(x["name"] == a for x in self._ACCENTS):
                self._accent = a
        except Exception:
            pass
        self._fmult = 1.0
        self._dmult = 1.0
        try:
            self._fmult = _font_mult(s.value("ui/font_size", "Medium — 12px"))
            self._dmult = _density_mult(s.value("ui/density", "Compact"))
        except Exception:
            pass
        self._cb_status = False

    def _accent_def(self):
        for a in self._ACCENTS:
            if a["name"] == self._accent:
                return a
        return self._ACCENTS[0]

    @Property("QVariantMap", notify=changed)
    def palette(self):
        pal = dict(_THEMES.get(self._name, _THEMES["Dark"]))
        a = self._accent_def()
        pal["ACC"], pal["ACC_HOVER"], pal["ACC_PRESSED"] = a["v"], a["h"], a["p"]
        pal["STATUS_OK"]  = "#009e73" if self._cb_status else pal["SUCCESS"]
        pal["STATUS_BAD"] = "#d55e00" if self._cb_status else pal["DANGER"]
        return pal

    @Slot(bool)
    def setStatusColourblind(self, on):
        if bool(on) != self._cb_status:
            self._cb_status = bool(on)
            self.changed.emit()

    @Property("QVariantList", constant=True)
    def accents(self):
        return [dict(a) for a in self._ACCENTS]

    @Property(str, notify=accentChanged)
    def accentName(self):
        return self._accent

    @Slot(str)
    def setAccent(self, name: str):
        if any(a["name"] == name for a in self._ACCENTS) and name != self._accent:
            self._accent = name
            try:
                s = _store(); s.setValue("ui/accent", name); s.sync()
            except Exception:
                pass
            self.accentChanged.emit()
            self.changed.emit()

    @Property(str, notify=changed)
    def name(self):
        return self._name

    @Property("QVariantMap", notify=scaleChanged)
    def scale(self):
        sc = dict(self._SCALE)
        if self._fmult != 1.0 or self._dmult != 1.0:
            for k, v in list(sc.items()):
                if not isinstance(v, (int, float)) or isinstance(v, bool):
                    continue
                if k.startswith("text") or k.startswith("display"):
                    sc[k] = max(1, round(v * self._fmult))
                elif k.startswith("sp"):
                    sc[k] = max(1, round(v * self._dmult))
        return sc

    @Slot(str)
    def setFontSize(self, label):
        m = _font_mult(label)
        if abs(m - self._fmult) > 1e-6:
            self._fmult = m
            self.scaleChanged.emit()

    @Slot(str)
    def setDensity(self, label):
        m = _density_mult(label)
        if abs(m - self._dmult) > 1e-6:
            self._dmult = m
            self.scaleChanged.emit()

    @Property("QStringList", constant=True)
    def themes(self):
        return list(_THEMES.keys())

    @Property(bool, notify=reducedMotionChanged)
    def reducedMotion(self):
        return self._reduced_motion

    @reducedMotion.setter
    def reducedMotion(self, v: bool):
        if bool(v) != self._reduced_motion:
            self._reduced_motion = bool(v)
            try:
                s = _store(); s.setValue("ui/reduce_motion", self._reduced_motion); s.sync()
            except Exception:
                pass
            self.reducedMotionChanged.emit()

    @Slot(str)
    def setTheme(self, name: str):
        if name in _THEMES and name != self._name:
            self._name = name
            try:
                s = _store(); s.setValue("ui/app_theme", name); s.sync()
            except Exception:
                pass
            self.changed.emit()
