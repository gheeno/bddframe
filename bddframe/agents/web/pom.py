"""
POM YAML fallback — maps human names to explicit selectors.

Resolution order (per lookup):
  1. Local  pom.yaml  (features/<subfolder>/pom.yaml)
  2. Global pom.yaml  (features/pom.yaml)

YAML structure:
  hero banner:
    css: ".hero-banner"

  product table:
    xpath: "//table[@data-testid='products']"

  profile avatar:
    id: "user-avatar"          # shorthand for [id="user-avatar"]

  search input:
    testid: "search-box"       # data-testid attribute

Selector types: css | xpath | id | testid | text | role
"""
from __future__ import annotations

import re
from pathlib import Path
from functools import lru_cache

try:
    import yaml
except ImportError:
    yaml = None  # ponytail: only fail at lookup time, not import time

# Set by hooks.before_scenario so locator knows which folder is active.
_feature_dir: str | None = None


def set_context(feature_dir: str | None):
    global _feature_dir
    _feature_dir = feature_dir


def locate(page, text: str):
    """Return a Playwright Locator from POM YAML, or None."""
    entry = _lookup(text)
    if entry is None:
        return None
    return _build_locator(page, entry, text)


# ---------------------------------------------------------------------------

def _normalize(s: str) -> str:
    return re.sub(r'\s+', ' ', s.strip().lower())


def _lookup(text: str) -> dict | None:
    key = _normalize(text)
    for mapping in _load_pom_chain():
        for raw_key, entry in mapping.items():
            if _normalize(str(raw_key)) == key:
                return entry
    return None


def _load_pom_chain() -> list[dict]:
    """Return [local_pom, global_pom] — local first so it wins on duplicates."""
    chain = []
    if _feature_dir:
        local = _load_yaml(Path(_feature_dir) / "pom.yaml")
        if local:
            chain.append(local)
    global_ = _load_yaml(_global_pom_path())
    if global_:
        chain.append(global_)
    return chain


def _global_pom_path() -> Path:
    """Walk up from feature_dir (or cwd) to find features/pom.yaml."""
    start = Path(_feature_dir) if _feature_dir else Path.cwd()
    for directory in [start, *start.parents]:
        candidate = directory / "features" / "pom.yaml"
        if candidate.exists():
            return candidate
        candidate = directory / "pom.yaml"
        if candidate.exists():
            return candidate
    return Path("features/pom.yaml")  # fallback path, may not exist


@lru_cache(maxsize=32)
def _load_yaml(path: Path) -> dict | None:
    if yaml is None:
        raise ImportError("POM YAML requires PyYAML: pip install pyyaml")
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text()) or {}


def _build_locator(page, entry: dict, original_text: str):
    if isinstance(entry, str):
        # shorthand: just a CSS string
        return _first_or_none(page.locator(entry))

    selector_type = next(iter(entry)).lower()
    value = entry[selector_type]

    if selector_type == "css":
        return _first_or_none(page.locator(value))
    if selector_type == "xpath":
        return _first_or_none(page.locator(f"xpath={value}"))
    if selector_type == "id":
        return _first_or_none(page.locator(f"[id='{value}']"))
    if selector_type == "testid":
        return _first_or_none(page.get_by_test_id(value))
    if selector_type == "text":
        return _first_or_none(page.get_by_text(value, exact=False))
    if selector_type == "role":
        return _first_or_none(page.get_by_role(value))

    raise ValueError(f"Unknown POM selector type '{selector_type}' for '{original_text}'")


def _first_or_none(loc):
    try:
        return loc.first if loc.count() > 0 else None
    except Exception:
        return None
