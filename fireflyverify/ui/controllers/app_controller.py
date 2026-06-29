"""AppController — top-level tab navigation for the QML shell."""
from __future__ import annotations

from PySide6.QtCore import QObject, Property, Signal, Slot

TABS = ["Ground Truth", "Methods", "Results", "Report"]


class AppController(QObject):
    tabChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tab = 0

    @Property(int, notify=tabChanged)
    def currentTab(self):
        return self._tab

    @Property("QStringList", constant=True)
    def tabs(self):
        return list(TABS)

    @Slot(int)
    def setTab(self, tab: int):
        if 0 <= tab < len(TABS) and tab != self._tab:
            self._tab = tab
            self.tabChanged.emit()
