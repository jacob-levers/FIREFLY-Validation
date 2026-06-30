# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for FIREFLY-Validation (PySide6 QML front-end).

Outputs:
  macOS:   dist/FIREFLY-Validation.app   (wrapped in a DMG by CI)
  Windows: dist/FIREFLY-Validation.exe   (onefile)

Lean by design — this app only needs PySide6 + numpy/pandas/scipy/matplotlib/
tifffile (no torch / trackpy / scikit-image / numba), so the bundle is small.
"""
import os
import re
import sys

from PyInstaller.utils.hooks import (collect_data_files, collect_submodules,
                                     copy_metadata)


def _no_tests(pkg):
    """collect_submodules(pkg) minus the bundled `*.tests.*` trees."""
    return collect_submodules(pkg, filter=lambda n: "tests" not in n.split("."))


# ── hidden imports ────────────────────────────────────────────────────────────
hidden = []
hidden += _no_tests("numpy")
hidden += _no_tests("pandas")
hidden += _no_tests("scipy")
hidden += _no_tests("matplotlib")

# scipy >=1.16 moved array_api_compat under scipy._external, and
# collect_submodules("scipy") does NOT recurse into it — so
# scipy._external.array_api_compat.numpy.fft (pulled in transitively by
# scipy.special <- scipy.linalg <- our `from scipy.special import erf`) is absent
# from the bundle and the frozen app dies on first import with
# ModuleNotFoundError. Collect the vendored subtrees explicitly.
for _vendored in (
    # scipy >=1.16 layout (array_api_compat under scipy._external)
    "scipy._external.array_api_compat",
    "scipy._external.array_api_extra",
    "scipy._external._array_api_compat_vendor",
    "scipy._external.packaging_version",
    # alternate layout used by some scipy versions (under scipy._lib)
    "scipy._lib.array_api_compat",
    "scipy._lib.array_api_extra",
):
    try:
        hidden += collect_submodules(_vendored)
    except Exception:
        pass
hidden += collect_submodules("PySide6")
hidden += collect_submodules("shiboken6")
hidden += collect_submodules("fireflyverify")
hidden += [
    # Qt Quick stack (loaded lazily via app_qml → static analysis misses them).
    # QtSvg backs the Lucide icon image-provider; Controls2 is restyled to Basic.
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets",
    "PySide6.QtQuickControls2", "PySide6.QtSvg",
    "PySide6.QtWidgets", "PySide6.QtGui", "PySide6.QtCore",
    # matplotlib renders figures to PNG (Agg) + the PDF report.
    "matplotlib.backends.backend_agg",
    "matplotlib.backends.backend_pdf",
    "tifffile",
    "pandas._libs.tslibs.np_datetime",
    "pandas._libs.tslibs.nattype",
    "pandas._libs.tslibs.timedeltas",
    "pandas._libs.tslibs.timestamps",
    "encodings.utf_8", "encodings.ascii", "encodings.latin_1",
]

# ── datas ──────────────────────────────────────────────────────────────────────
datas = []
datas += collect_data_files("matplotlib")
for _pkg in ("numpy", "pandas", "scipy", "matplotlib", "tifffile",
             "PySide6", "shiboken6"):
    try:
        datas += copy_metadata(_pkg)
    except Exception:
        pass

# Bundle the QML tree (Main.qml + components/ + tabs/ + assets/icons) so the
# frozen app loads it from sys._MEIPASS — app_qml.py resolves it there.
_qml_dir = os.path.join(SPECPATH, "fireflyverify", "ui", "qml")
if os.path.isdir(_qml_dir):
    datas += [(_qml_dir, os.path.join("fireflyverify", "ui", "qml"))]

# app icon (used at runtime for the window/dock; the .icns/.ico drive the bundle)
_icon_png = os.path.join(SPECPATH, "assets", "icon.png")
if os.path.isfile(_icon_png):
    datas += [(_icon_png, "assets")]

# version (kept in sync with fireflyverify/__init__.py, stamped by CI from the tag)
_version = "0.1.0"
try:
    _t = open(os.path.join(SPECPATH, "fireflyverify", "__init__.py"),
              encoding="utf-8").read()
    _m = re.search(r'__version__\s*=\s*"([^"]+)"', _t)
    if _m:
        _version = _m.group(1)
except Exception:
    pass

# ── analysis ───────────────────────────────────────────────────────────────────
a = Analysis(
    ["run_verify.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["torch", "trackpy", "skimage", "scikit_image", "sklearn",
              "numba", "llvmlite", "napari", "vispy", "IPython", "notebook",
              "jupyter", "tkinter", "_tkinter", "streamlit", "tornado"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

_ICON_WIN = (os.path.join(SPECPATH, "assets", "icon.ico")
             if os.path.isfile(os.path.join(SPECPATH, "assets", "icon.ico")) else None)
_ICON_MAC = (os.path.join(SPECPATH, "assets", "icon.icns")
             if os.path.isfile(os.path.join(SPECPATH, "assets", "icon.icns")) else None)

if sys.platform == "win32":
    exe = EXE(
        pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
        name="FIREFLY-Validation",
        debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
        runtime_tmpdir="%LOCALAPPDATA%\\FIREFLY-Validation\\bundle",
        console=False, disable_windowed_traceback=False, argv_emulation=False,
        target_arch=None, codesign_identity=None, entitlements_file=None,
        icon=_ICON_WIN,
    )
else:
    exe = EXE(
        pyz, a.scripts, [], exclude_binaries=True,
        name="FIREFLY-Validation",
        debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
        console=False, argv_emulation=False,
        codesign_identity=None, entitlements_file=None,
    )
    coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=False,
                   upx_exclude=[], name="FIREFLY-Validation")
    if sys.platform == "darwin":
        app = BUNDLE(
            coll,
            name="FIREFLY-Validation.app",
            icon=_ICON_MAC,
            bundle_identifier="com.jacoblevers.fireflyvalidation",
            info_plist={
                "CFBundleName": "FIREFLY-Validation",
                "CFBundleDisplayName": "FIREFLY · Verification",
                "CFBundleVersion": _version,
                "CFBundleShortVersionString": _version,
                "NSHighResolutionCapable": True,
                "LSMinimumSystemVersion": "11.0",
            },
        )
