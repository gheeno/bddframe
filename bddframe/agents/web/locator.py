import re
from playwright.sync_api import Page, Locator


def find(page: Page, text: str) -> Locator | None:
    """
    Resolve a human locator string to a Playwright Locator.
    Tries accessibility strategies in order — no CSS selectors written by humans.
    """
    pattern = re.compile(re.escape(text), re.IGNORECASE)

    strategies = [
        lambda: page.get_by_role("button", name=pattern),
        lambda: page.get_by_role("link", name=pattern),
        lambda: page.get_by_label(pattern),
        lambda: page.get_by_placeholder(pattern),
        lambda: page.get_by_role("textbox", name=pattern),
        lambda: page.get_by_role("combobox", name=pattern),
        lambda: page.get_by_role("checkbox", name=pattern),
        lambda: page.get_by_text(pattern, exact=False),
    ]

    for strategy in strategies:
        try:
            loc = strategy()
            if loc.count() > 0:
                return loc.first
        except Exception:
            continue

    return None
