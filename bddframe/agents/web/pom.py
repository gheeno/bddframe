"""
POM YAML fallback — maps human names to explicit selectors.

Resolution order (per lookup):
  1. Local  pom.yaml  (features/<subfolder>/pom.yaml)
  2. Global pom.yaml  (features/pom.yaml)

Within each file, keys are looked up in this order:
  a. Active page block  (pages: whose `match.url_contains` fits the live URL,
     or the page pinned via `set_active_page`)
  b. shared: block      (page-agnostic elements)
  c. Top-level flat keys (legacy format — still fully supported)

FLAT FORMAT (legacy, unchanged):
  burger menu:
    id: react-burger-menu-btn

PAGE-SCOPED FORMAT (new, optional — solves same-key-different-page):
  pages:
    home:
      match: { url_contains: "example.com/$" }   # regex, matched on page.url
      search: { css: "input.home-search" }
    search results:
      match: { url_contains: "/search" }
      search: { css: "input.results-filter" }
  shared:
    cookie accept: { id: onetrust-accept-btn-handler }

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

# Set by hooks.before_feature so locator knows which folder is active.
_feature_dir: str | None = None

# Optional page pin (9.3): overrides URL matching when set (e.g. SPAs where the
# URL never changes). Set by the "User is on the '<name>' page" step / @page tag.
_active_page: str | None = None

_RESERVED = ("pages", "shared")


def set_context(feature_dir: str | None):
    global _feature_dir
    _feature_dir = feature_dir


def set_active_page(name: str | None):
    global _active_page
    _active_page = name


def locate(page, text: str):
    """Return a Playwright Locator from POM YAML, or None."""
    url = ""
    try:
        url = page.url or ""
    except Exception:
        pass
    entry = _lookup(text, url)
    if entry is None:
        return None
    return _build_locator(page, entry, text)


# ---------------------------------------------------------------------------

def _normalize(s: str) -> str:
    return re.sub(r'\s+', ' ', s.strip().lower())


def _lookup(text: str, url: str = "") -> dict | str | None:
    key = _normalize(text)
    for mapping in _load_pom_chain():
        entry = _lookup_in_mapping(mapping, key, url)
        if entry is not None:
            return entry
    return None


def _lookup_in_mapping(mapping: dict, key: str, url: str):
    if not isinstance(mapping, dict):
        return None

    # a. active page block (pinned name first, then URL match)
    pages = mapping.get("pages")
    if isinstance(pages, dict):
        block = _active_page_block(pages, url)
        if block:
            hit = _match_key(block, key, skip=("match",))
            if hit is not None:
                return hit

    # b. shared block
    shared = mapping.get("shared")
    if isinstance(shared, dict):
        hit = _match_key(shared, key)
        if hit is not None:
            return hit

    # c. legacy flat keys
    flat = {k: v for k, v in mapping.items() if k not in _RESERVED}
    return _match_key(flat, key)


def _active_page_block(pages: dict, url: str) -> dict | None:
    # Pinned page wins, regardless of URL.
    if _active_page is not None:
        pin = _normalize(_active_page)
        for name, block in pages.items():
            if _normalize(str(name)) == pin and isinstance(block, dict):
                return block
    # Otherwise first block whose match.url_contains is found in the URL.
    for name, block in pages.items():
        if not isinstance(block, dict):
            continue
        pattern = (block.get("match") or {}).get("url_contains")
        if pattern and re.search(pattern, url, re.IGNORECASE):
            return block
    return None


def _match_key(mapping: dict, key: str, skip: tuple = ()):
    for raw_key, entry in mapping.items():
        if raw_key in skip:
            continue
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
