"""Where this run writes its results.

Single source of truth so parallel workers (behavex) can each write to their
own subdir instead of clobbering the shared one. Read from the env every call
so a hook can repoint it mid-process. Default keeps single-process runs at the
historical `allure-results/`.
"""
import os
from pathlib import Path


def results_dir() -> Path:
    return Path(os.getenv("BDDFRAME_RESULTS_DIR", "allure-results"))
