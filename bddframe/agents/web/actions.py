import os
import time
from playwright.sync_api import Page
from bddframe.log import logger
from .locator import find


def set_page(name: str):
    """Pin the active POM page (9.3) — used when the URL can't identify the page."""
    from . import pom
    pom.set_active_page(name)


def navigate(page: Page, url: str):
    page.goto(url, wait_until="domcontentloaded")


def click(page: Page, locator_text: str):
    loc = find(page, locator_text)
    if loc is None:
        raise AssertionError(f"Could not find element to click: '{locator_text}'")
    loc.click()


def fill(page: Page, locator_text: str, value: str):
    loc = find(page, locator_text)
    if loc is None:
        raise AssertionError(f"Could not find element to fill: '{locator_text}'")
    loc.fill(value)


def clear(page: Page, locator_text: str):
    loc = find(page, locator_text)
    if loc is None:
        raise AssertionError(f"Could not find element to clear: '{locator_text}'")
    loc.clear()


def select_option(page: Page, locator_text: str, value: str):
    loc = find(page, locator_text)
    if loc is None:
        raise AssertionError(f"Could not find dropdown: '{locator_text}'")
    loc.select_option(label=value)


def check(page: Page, locator_text: str):
    loc = find(page, locator_text)
    if loc is None:
        raise AssertionError(f"Could not find checkbox: '{locator_text}'")
    loc.check()


def uncheck(page: Page, locator_text: str):
    loc = find(page, locator_text)
    if loc is None:
        raise AssertionError(f"Could not find checkbox: '{locator_text}'")
    loc.uncheck()


def assert_visible(page: Page, text: str):
    loc = page.get_by_text(text, exact=False)
    # Scan for the first VISIBLE match — the first DOM match is often an
    # sr-only (screen-reader, visually hidden) duplicate. ponytail: cap at 30,
    # raise the cap if a page hides the real match past the 30th occurrence.
    for i in range(min(loc.count(), 30)):
        if loc.nth(i).is_visible():
            return
    raise AssertionError(f"Expected to see '{text}' on page — not found.\nURL: {page.url}")


def assert_hidden(page: Page, text: str):
    loc = page.get_by_text(text, exact=False)
    if loc.count() == 0 or not loc.first.is_visible():
        return
    raise AssertionError(f"Expected '{text}' to NOT be visible — but it is.\nURL: {page.url}")


def assert_url(page: Page, fragment: str):
    if fragment.lower() not in page.url.lower():
        raise AssertionError(f"Expected URL to contain '{fragment}'\nActual URL: {page.url}")


def assert_title(page: Page, fragment: str):
    title = page.title()
    if fragment.lower() not in title.lower():
        raise AssertionError(f"Expected page title to contain '{fragment}'\nActual title: '{title}'")


def assert_semantic(page: Page, assertion: str):
    """Vision LLM assertion for things that can't be expressed in DOM terms."""
    if not os.getenv("BDDFRAME_MODEL"):
        raise AssertionError(
            f"Semantic assertion requires BDDFRAME_MODEL in .env\n"
            f"  e.g. BDDFRAME_MODEL=gpt-4o"
        )
    import base64
    from bddframe.llm.client import ask_vision

    b64 = base64.b64encode(page.screenshot()).decode()
    result = ask_vision(
        prompt=f'Does this screen show: "{assertion}"? Answer YES or NO on the first line, then explain in one sentence.',
        image_b64=b64,
    )
    if 'YES' not in result.strip().split('\n')[0].upper():
        raise AssertionError(
            f"Semantic assertion failed: '{assertion}'\n"
            f"Vision LLM: {result}\nURL: {page.url}"
        )
    logger.info(f"\n  🤖 Semantic pass: {result.strip()}")


def visual_baseline(page: Page, name: str, ignore: str = None):
    """Capture semantic baseline on first run; compare on subsequent runs."""
    if not os.getenv("BDDFRAME_MODEL"):
        raise AssertionError("Visual baseline requires BDDFRAME_MODEL in .env")

    import base64
    from pathlib import Path
    from bddframe.llm.client import ask_vision

    os.makedirs("baselines", exist_ok=True)
    path = Path(f"baselines/{name.replace(' ', '_')}.txt")
    ignore_note = f" Ignore the {ignore} area." if ignore else ""

    b64 = base64.b64encode(page.screenshot()).decode()

    if not path.exists():
        description = ask_vision(
            prompt=f"Describe this page's visual layout and key content in 2-3 sentences for test automation baseline purposes.{ignore_note}",
            image_b64=b64,
        )
        path.write_text(description)
        logger.info(f"\n  📷 Baseline captured: {path}")
        return

    baseline = path.read_text()
    result = ask_vision(
        prompt=f'Does this screenshot match this baseline description? Baseline: "{baseline}"{ignore_note}\nAnswer YES or NO on the first line, then describe any differences.',
        image_b64=b64,
    )
    if 'YES' not in result.strip().split('\n')[0].upper():
        raise AssertionError(
            f"Visual baseline mismatch for '{name}'\n"
            f"Baseline: {baseline}\nDiff: {result}\nURL: {page.url}"
        )
    logger.info(f"\n  📷 Baseline matched: {result.strip()}")


def _pixel_diff_ratio(base, current, tol: int = 30):
    """Fraction of pixels that differ by more than `tol` (0..255) on any channel.
    Returns None if the two images have different sizes (treated as a mismatch
    by the caller). Pure function — no DOM — so it's unit-testable.
    ponytail: O(pixels) Python sum; fine for a screenshot, swap to numpy if a
    4K full-page diff ever gets slow."""
    from PIL import ImageChops
    base = base.convert("RGB")
    current = current.convert("RGB")
    if base.size != current.size:
        return None
    diff = ImageChops.difference(base, current).convert("L")
    changed = sum(1 for p in diff.getdata() if p > tol)
    total = base.size[0] * base.size[1]
    return changed / total if total else 0.0


def pixel_baseline(page: Page, name: str):
    """Deterministic visual regression — pixel diff, no LLM. First run captures
    baselines/<name>.png; later runs compare and fail if more than
    BDDFRAME_PIXEL_THRESHOLD (default 1%) of pixels changed, saving a diff
    image as evidence."""
    import io
    from pathlib import Path
    from PIL import Image, ImageChops

    os.makedirs("baselines", exist_ok=True)
    safe = name.replace(" ", "_").replace("/", "_")
    path = Path(f"baselines/{safe}.png")
    shot = page.screenshot(full_page=True)

    if not path.exists():
        path.write_bytes(shot)
        logger.info(f"\n  📐 Pixel baseline captured: {path}")
        return

    base = Image.open(path)
    current = Image.open(io.BytesIO(shot))
    ratio = _pixel_diff_ratio(base, current)
    threshold = float(os.getenv("BDDFRAME_PIXEL_THRESHOLD", "0.01"))

    if ratio is None:
        raise AssertionError(
            f"Pixel baseline '{name}': size changed "
            f"{base.size} → {current.size}.\nURL: {page.url}"
        )
    if ratio > threshold:
        os.makedirs("screenshots", exist_ok=True)
        diff_path = f"screenshots/DIFF_{safe}.png"
        ImageChops.difference(base.convert("RGB"), current.convert("RGB")).save(diff_path)
        raise AssertionError(
            f"Pixel baseline mismatch '{name}': {ratio:.2%} of pixels changed "
            f"(threshold {threshold:.2%}).\nDiff: {diff_path}\nURL: {page.url}"
        )
    logger.info(f"\n  📐 Pixel baseline matched: {name} ({ratio:.2%} diff)")


def wait_load(page: Page):
    page.wait_for_load_state("domcontentloaded")


def wait_networkidle(page: Page):
    page.wait_for_load_state("networkidle")


def wait_visible(page: Page, text: str):
    from .locator import wait_for
    wait_for(page, text)  # resolves via POM YAML or text, respects BDDFRAME_TIMEOUT


def wait_seconds(seconds: int):
    time.sleep(seconds)


def scroll(page: Page, direction: str):
    page.mouse.wheel(0, 500 if direction == "down" else -500)


def scroll_to(page: Page, locator_text: str):
    loc = find(page, locator_text)
    if loc is None:
        raise AssertionError(f"Could not find element to scroll to: '{locator_text}'")
    loc.scroll_into_view_if_needed()


def screenshot(page: Page, name: str, path: str = "screenshots"):
    os.makedirs(path, exist_ok=True)
    file_path = f"{path}/{name}.png"
    page.screenshot(path=file_path, full_page=True)
    return file_path


# ---------------------------------------------------------------------------
# Phase 11 — coverage expansion
# ---------------------------------------------------------------------------

_KEY_ALIASES = {"esc": "Escape", "return": "Enter", "up": "ArrowUp",
                "down": "ArrowDown", "left": "ArrowLeft", "right": "ArrowRight"}


def press_key(page: Page, key: str):
    """A real keypress (Enter/Tab/Escape/arrows…) — not a button click."""
    page.keyboard.press(_KEY_ALIASES.get(key.lower(), key))


def hover(page: Page, locator_text: str):
    loc = find(page, locator_text)
    if loc is None:
        raise AssertionError(f"Could not find element to hover: '{locator_text}'")
    loc.hover()


def wait_hidden(page: Page, text: str):
    from .locator import wait_hidden as _wait_hidden
    _wait_hidden(page, text)


def get_text(page: Page, locator_text: str) -> str:
    """Read an element's value (inputs) or visible text — used by store_text."""
    loc = find(page, locator_text)
    if loc is None:
        raise AssertionError(f"Could not find element to read: '{locator_text}'")
    try:
        val = loc.input_value()
        if val:
            return val
    except Exception:
        pass
    return (loc.inner_text() or "").strip()


def assert_value(page: Page, locator_text: str, value: str):
    actual = get_text(page, locator_text)
    if value != actual and value not in actual:
        raise AssertionError(
            f"Expected '{locator_text}' to contain '{value}' — actual: '{actual}'\nURL: {page.url}"
        )


def assert_state(page: Page, locator_text: str, state: str):
    loc = find(page, locator_text)
    if loc is None:
        raise AssertionError(f"Could not find element: '{locator_text}'")
    state = state.lower().replace("-", "").replace("read only", "readonly")
    try:
        ok = {
            "enabled":   loc.is_enabled(),
            "disabled":  not loc.is_enabled(),
            "checked":   loc.is_checked(),
            "unchecked": not loc.is_checked(),
            "selected":  loc.is_checked(),
            "editable":  loc.is_editable(),
            "readonly":  not loc.is_editable(),
        }[state]
    except KeyError:
        raise AssertionError(f"Unknown state '{state}' for '{locator_text}'")
    if not ok:
        raise AssertionError(f"Expected '{locator_text}' to be {state} — it is not.\nURL: {page.url}")


def assert_attribute(page: Page, locator_text: str, attribute: str, value: str):
    loc = find(page, locator_text)
    if loc is None:
        raise AssertionError(f"Could not find element: '{locator_text}'")
    actual = loc.get_attribute(attribute)
    if actual != value and (actual is None or value not in actual):
        raise AssertionError(
            f"Expected '{locator_text}' attribute '{attribute}' = '{value}' — actual: '{actual}'"
        )


def assert_count(page: Page, count: int, locator_text: str):
    actual = page.get_by_text(locator_text, exact=False).count()
    if actual != count:
        raise AssertionError(
            f"Expected {count} '{locator_text}' — found {actual}.\nURL: {page.url}"
        )


def click_in_row(page: Page, locator_text: str, row: str):
    """Click an element scoped to the grid row containing `row` text (D365)."""
    row_loc = page.get_by_role("row").filter(has_text=row)
    if row_loc.count() == 0:
        raise AssertionError(f"No row containing '{row}' found.\nURL: {page.url}")
    loc = find(page, locator_text, scope=row_loc.first)
    if loc is None:
        raise AssertionError(f"Could not find '{locator_text}' in row '{row}'")
    loc.click()


def click_in_section(page: Page, locator_text: str, section: str):
    """Click an element scoped to a named container/section."""
    container = find(page, section)
    if container is None:
        raise AssertionError(f"Could not find section '{section}'")
    loc = find(page, locator_text, scope=container)
    if loc is None:
        raise AssertionError(f"Could not find '{locator_text}' in section '{section}'")
    loc.click()


def assert_cell(page: Page, row: str, column: str, expected: str):
    """Assert a grid cell (row identified by text, column by header name)."""
    row_loc = page.get_by_role("row").filter(has_text=row)
    if row_loc.count() == 0:
        raise AssertionError(f"No row containing '{row}' found.\nURL: {page.url}")

    headers = page.get_by_role("columnheader")
    idx = None
    for i in range(headers.count()):
        if column.lower() in (headers.nth(i).inner_text() or "").lower():
            idx = i
            break

    cells = row_loc.first.get_by_role("cell")
    # ponytail: header-index mapping; falls back to whole-row text if no
    # columnheader role exists. Upgrade to aria-colindex if a grid needs it.
    if idx is not None and idx < cells.count():
        actual = (cells.nth(idx).inner_text() or "").strip()
    else:
        actual = (row_loc.first.inner_text() or "").strip()

    if expected != actual and expected not in actual:
        raise AssertionError(
            f"Cell [row '{row}', column '{column}'] expected '{expected}' — actual: '{actual}'"
        )


def assert_row_count(page: Page, count: int):
    rows = page.get_by_role("row")
    total = rows.count()
    has_header = page.get_by_role("columnheader").count() > 0
    data_rows = total - (1 if has_header else 0)
    # ponytail: accept either data-row count or raw row count — grids vary in
    # whether the header is a role="row". Tighten if a suite needs exactness.
    if count not in (data_rows, total):
        raise AssertionError(
            f"Expected {count} rows — found {data_rows} data rows ({total} total).\nURL: {page.url}"
        )


def switch_frame(page: Page, name: str):
    """Scope subsequent element lookups to an iframe (by name/id/url substring)."""
    from .locator import set_frame
    frame = page.frame(name=name)
    if frame is None:
        for f in page.frames:
            if name.lower() in (f.name or "").lower() or name.lower() in (f.url or "").lower():
                frame = f
                break
    if frame is None:
        raise AssertionError(
            f"No frame matching '{name}'. Available: "
            f"{[f.name or f.url for f in page.frames]}"
        )
    set_frame(frame)


def search(page: Page, query: str):
    """Fill the search box and submit (Enter) in one step. Resolves the box via
    the 'searchbox' POM key, then a 'search' label, then the searchbox role."""
    loc = find(page, "searchbox")
    if loc is None:
        loc = find(page, "search")
    if loc is None:
        role_loc = page.get_by_role("searchbox")
        if role_loc.count() == 0:
            raise AssertionError("Could not find a search box on the page")
        loc = role_loc.first
    loc.fill(query)
    page.keyboard.press("Enter")


def close_popups(page: Page):
    """Best-effort dismiss of cookie banners / modals / promo popups. Never
    fails — clicks any matching dismiss control it finds, then presses Escape.
    # ponytail: a short selector list covers the common cases; extend if a
    # specific site needs a bespoke close button."""
    selectors = [
        '#onetrust-accept-btn-handler',
        'button[aria-label="Close" i]',
        'button[aria-label="Dismiss" i]',
        '[class*="modal" i] button[class*="close" i]',
        'button:has-text("Accept All")',
        'button:has-text("Accept")',
    ]
    closed = 0
    for sel in selectors:
        try:
            loc = page.locator(sel)
            for i in range(min(loc.count(), 3)):
                el = loc.nth(i)
                if el.is_visible():
                    el.click(timeout=2000)
                    closed += 1
        except Exception:
            pass
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    if closed:
        logger.info(f"\n  🧹 Closed {closed} popup(s)")


# ---------------------------------------------------------------------------
# Phase 12 — step dependencies & shared state
# ---------------------------------------------------------------------------

def get_attribute_value(page: Page, locator_text: str, attribute: str) -> str:
    """Read an element's attribute — used by store_attribute."""
    loc = find(page, locator_text)
    if loc is None:
        raise AssertionError(f"Could not find element to read: '{locator_text}'")
    return loc.get_attribute(attribute) or ""


# ---------------------------------------------------------------------------
# Phase D — network mocking, API setup/teardown, test-data fixtures
# ---------------------------------------------------------------------------

def mock_route(page: Page, url: str, status: int, body: str = None):
    """Intercept requests matching `url` (glob) and return a canned response —
    decouples a test from a flaky/slow/absent backend."""
    page.route(url, lambda route: route.fulfill(
        status=status, body=body or "", content_type="application/json"))
    logger.info(f"\n  🔌 Mocking {url} → {status}")


def block_route(page: Page, url: str):
    """Abort requests matching `url` (glob) — kill analytics/ads/3rd-party noise."""
    page.route(url, lambda route: route.abort())
    logger.info(f"\n  🚫 Blocking {url}")


def api_call(page: Page, method: str, url: str, body: str = None):
    """Hit an HTTP endpoint directly (Playwright's request context — shares the
    browser's cookies). For data setup/teardown without driving the UI. Fails on
    a non-2xx response."""
    resp = page.request.fetch(url, method=method, data=body)
    if not resp.ok:
        raise AssertionError(f"API {method} {url} → {resp.status} {resp.status_text}")
    logger.info(f"\n  🛰  {method} {url} → {resp.status}")


def flatten_data(data: dict) -> dict:
    """Map a fixture dict to run-store keys (UPPER, spaces→underscores). Pure —
    unit-testable without a file."""
    return {str(k).upper().replace(" ", "_"): str(v) for k, v in (data or {}).items()}


def load_data(file: str) -> dict:
    """Read a YAML/JSON fixture into a flat {KEY: value} dict for the var store."""
    import yaml
    from pathlib import Path
    raw = yaml.safe_load(Path(file).read_text()) or {}
    if not isinstance(raw, dict):
        raise AssertionError(f"Test data '{file}' must be a top-level mapping, got {type(raw).__name__}")
    return flatten_data(raw)


def assert_compare(left: str, op: str, right: str):
    """Compare two already-substituted values. Numeric when both parse as
    numbers; otherwise string. No page/DOM access — operands are literals."""
    def _num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    ln, rn = _num(left), _num(right)
    numeric = ln is not None and rn is not None
    l, r = (ln, rn) if numeric else (str(left), str(right))

    ops = {
        '>':  lambda: l > r,
        '<':  lambda: l < r,
        '>=': lambda: l >= r,
        '<=': lambda: l <= r,
        '==': lambda: l == r,
        '!=': lambda: l != r,
        'contains': lambda: str(right) in str(left),
    }
    if op in ('>', '<', '>=', '<=') and not numeric:
        raise AssertionError(
            f"Cannot compare non-numeric values with '{op}': '{left}' vs '{right}'"
        )
    if op not in ops:
        raise AssertionError(f"Unknown comparison operator '{op}'")
    if not ops[op]():
        raise AssertionError(
            f"Comparison failed: '{left}' {op} '{right}' is not true"
            + (" (compared as numbers)" if numeric else " (compared as text)")
        )
