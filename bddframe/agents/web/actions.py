import os
import time
from playwright.sync_api import Page
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
    print(f"\n  🤖 Semantic pass: {result.strip()}")


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
        print(f"\n  📷 Baseline captured: {path}")
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
    print(f"\n  📷 Baseline matched: {result.strip()}")


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
