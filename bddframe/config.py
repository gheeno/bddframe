"""Workspace config — bddframe.yaml lives in the user's test directory, not here.

A workspace is any directory the user owns holding their features/, pageobjects/,
.env and bddframe.yaml. The engine reads this to know where things live; CI passes
--workspace, the agent passes it too. Missing file → defaults (current layout).
"""
from pathlib import Path
import yaml

DEFAULTS = {
    "features_dir": "features",
    # Engine resolves POMs at <feature_dir>/pageobjects/, so keep them under features/.
    "pageobjects_dir": "features/pageobjects",
    "env_file": ".env",
    "reports_dir": "reports",
    "browser": "chromium",
    "headless": False,
}


def load(workspace: str = ".") -> dict:
    """Merge bddframe.yaml (if present) over the defaults."""
    cfg = dict(DEFAULTS)
    f = Path(workspace) / "bddframe.yaml"
    if f.exists():
        cfg.update(yaml.safe_load(f.read_text()) or {})
    return cfg
