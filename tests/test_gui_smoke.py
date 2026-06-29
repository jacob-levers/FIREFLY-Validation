"""GUI smoke: the QML shell loads without errors and renders.

Skipped where PySide6 is unavailable (e.g. headless CI without Qt)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


def test_shell_loads_without_qml_errors():
    from fireflyverify.ui.app_qml import build_main_window
    win, qw = build_main_window(_app)
    win.resize(1180, 820)
    win.show()
    for _ in range(20):
        _app.processEvents()
    errs = [e.toString() for e in qw.errors()]
    assert not errs, "QML load errors:\n" + "\n".join(errs)
    assert qw.rootObject() is not None


def test_tab_navigation():
    from fireflyverify.ui.app_qml import build_main_window
    win, qw = build_main_window(_app)
    win.show()
    for _ in range(10):
        _app.processEvents()
    appc = qw.rootContext().contextProperty("App")
    assert list(appc.tabs) == ["Ground Truth", "Methods", "Results", "Report"]
    appc.setTab(2)
    assert appc.currentTab == 2
