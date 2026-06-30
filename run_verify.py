#!/usr/bin/env python3
"""Launch the FIREFLY-VERIFICATION GUI.

Wraps import + main in a guard that logs any startup/import crash to the file
named by $VERIFY_LOG (used by the packaging smoke test) — frozen *windowed*
builds have no console, so an uncaught exception would otherwise vanish silently.
"""
import multiprocessing
import os
import sys
import traceback


def _log_fatal(exc_text: str) -> None:
    path = os.environ.get("VERIFY_LOG")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("[VERIFY-FATAL] startup crashed:\n" + exc_text + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        from fireflyverify.ui.app_qml import main
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException:
        _log_fatal(traceback.format_exc())
        raise
