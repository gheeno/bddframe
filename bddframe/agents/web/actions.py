import os
import time
from playwright.sync_api import Page
from .locator import find


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
    if loc.count() > 0 and loc.first.is_visible():
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
