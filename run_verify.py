#!/usr/bin/env python3
"""Launch the FIREFLY-VERIFICATION GUI."""
import multiprocessing

from fireflyverify.ui.app_qml import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
