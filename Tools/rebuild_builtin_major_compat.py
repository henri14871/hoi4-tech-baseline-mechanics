#!/usr/bin/env python3
"""
One-command rebuild for TBM's generated compatibility bundles and core cleanup.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parent


def run_step(args: list[str]) -> None:
    completed = subprocess.run([sys.executable, *args], cwd=TOOLS_DIR.parent)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> None:
    run_step(["Tools/tbm_compat_tool.py", "rebuild"])
    print("Rebuilt TBM compatibility bundles and cleaned legacy baked runtime files.")


if __name__ == "__main__":
    main()
