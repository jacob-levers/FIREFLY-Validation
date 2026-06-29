"""FIREFLY-VERIFICATION — QML / Qt Quick front-end entry point.

A QQuickWidget-hosted QML UI (same pattern + theme as FIREFLY) with controllers
bridging to the pure scoring engine. No native islands / HUD — this app only
loads files, scores them, and renders matplotlib figures.
"""
from __future__ import annotations

import os
import sys

from PySide6 import QtWidgets
from PySide6.QtCore import QUrl
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtQuickControls2 import QQuickStyle

# The Basic style is the customisable one our components restyle. Must be set
# before any Quick item is created → do it at import time.
QQuickStyle.setStyle("Basic")

from fireflyverify import __version__
from fireflyverify.ui.controllers.theme_controller import ThemeController
from fireflyverify.ui.controllers.app_controller import AppController
from fireflyverify.ui.controllers.providers.icon_provider import IconImageProvider

# Resolve the QML tree in dev (next to this file) and in a frozen build.
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    _QML_DIR = os.path.join(sys._MEIPASS, "fireflyverify", "ui", "qml")
else:
    _QML_DIR = os.path.join(os.path.dirname(__file__), "qml")
_ICONS_DIR = os.path.join(_QML_DIR, "assets", "icons")


def build_main_window(app: QtWidgets.QApplication):
    """Construct the QML shell hosted in a QMainWindow. Returns (window, qw);
    controllers are kept alive on the window so QML bindings stay valid."""
    theme = ThemeController()
    appc = AppController()

    win = QtWidgets.QMainWindow()
    win.setWindowTitle("FIREFLY · Verification")

    qw = QQuickWidget()
    qw.engine().addImageProvider("icon", IconImageProvider(_ICONS_DIR))
    ctx = qw.rootContext()
    ctx.setContextProperty("Theme", theme)
    ctx.setContextProperty("App", appc)
    ctx.setContextProperty("appVersion", __version__)
    qw.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
    qw.setSource(QUrl.fromLocalFile(os.path.join(_QML_DIR, "Main.qml")))
    for e in qw.errors():
        print(f"[VERIFY-QML] {e.toString()}", file=sys.stderr)

    win.setCentralWidget(qw)
    win.resize(1180, 820)
    win._ctx = (theme, appc, qw)
    return win, qw


def main() -> int:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    app.setApplicationName("FIREFLY-VERIFICATION")
    app.setOrganizationName("jacoblevers")
    win, qw = build_main_window(app)
    win.show()

    marker_path = os.environ.get("VERIFY_READY_MARKER")
    if marker_path:
        try:
            qw.repaint()
        except Exception:
            pass
        try:
            with open(marker_path, "w") as f:
                f.write("ready\n")
        except Exception:
            pass
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
