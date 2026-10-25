# -*- coding: utf-8 -*-
"""Runs the pipeline regression tests. (The previous version re-implemented the formulas
inline and always printed PASSED; it tested nothing about the real data or code.)"""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", str(here / "tests"), "-q"]))
