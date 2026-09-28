#!/usr/bin/env python3
"""Backward-compatibility wrapper around the new pipeline.

The original ``scripts/update_papers.py`` is preserved as a thin wrapper that
forwards arguments to ``python -m miccai_index build``. This keeps existing
automation and contributor muscle memory working.

If you are a new contributor, prefer the new entry point:

    python -m miccai_index build --scope miccai-all-years --mode broad --tracks all
"""

from __future__ import annotations

import os
import subprocess
import sys


def main() -> int:
    args = sys.argv[1:]
    # Forward everything after the script name. The new CLI accepts the same
    # --scope / --mode / --tracks flags, plus a richer set of options.
    cmd = [sys.executable, "-m", "miccai_index", "build", *args]
    env = os.environ.copy()
    # The new package lives under src/. Set PYTHONPATH if not already set.
    src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
    src_path = os.path.abspath(src_path)
    if "PYTHONPATH" not in env:
        env["PYTHONPATH"] = src_path
    else:
        env["PYTHONPATH"] = src_path + os.pathsep + env["PYTHONPATH"]
    print("[compat] Delegating to: " + " ".join(cmd))
    return subprocess.call(cmd, env=env)


if __name__ == "__main__":
    raise SystemExit(main())