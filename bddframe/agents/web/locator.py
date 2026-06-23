import re
from playwright.sync_api import Page, Locator
from . import pom


def find(page: Page, text: str) -> Locator | None:
    """
    Resolve a human label to a Playwright Locator.
    Order: accessibility → self-heal scroll → self-heal partial → POM YAML → vision LLM.
    """
    loc = _try_strategies(page, text)
    if loc:
        return loc

    # Self-heal 1: scroll and retry
    page.mouse.wheel(0, 300)
    loc = _try_strategies(page, text)
    if loc:
        print(f"\n  🔧 Healed: found '{text}' after scroll")
        return loc

    # Self-heal 2: partial text (first word)
    first_word = text.split()[0] if text.split() else text
    if first_word != text:
        loc = _try_strategies(page, first_word)
        if loc:
            print(f"\n  🔧 Healed: matched '{text}' via partial text '{first_word}'")
            return loc

    # Fallback 1: POM YAML
    loc = pom.locate(page, text)
    if loc:
        print(f"\n  📋 POM: resolved '{text}' via pom.yaml")
        return loc

    # Fallback 2: vision LLM
    loc = _vision_locate(page, text)
    if loc:
        print(f"\n  🔧 Healed: found '{text}' via vision LLM")
        return loc

    return None


def wait_for(page: Page, text: str, timeout: int | None = None):
    """
    Wait for an element to become visible.
    Tries accessibility strategies and POM YAML — handles dynamic/slow-loading content.
    """
    import os
    timeout_ms = timeout or int(os.getenv("BDDFRAME_TIMEOUT", "10000"))

    # Try POM first for named elements, then fall back to text
    loc = pom.locate(page, text)
    if loc is None:
        loc = page.get_by_text(text, exact=False).first

    loc.wait_for(state="visible", timeout=timeout_ms)


def _try_strategies(page: Page, text: str) -> Locator | None:
    pattern = re.compile(re.escape(text), re.IGNORECASE)
    strategies = [
        lambda: page.get_by_role("button",   name=pattern),
        lambda: page.get_by_role("link",     name=pattern),
        lambda: page.get_by_label(pattern),
        lambda: page.get_by_placeholder(pattern),
        lambda: page.get_by_role("textbox",  name=pattern),
        lambda: page.get_by_role("combobox", name=pattern),
        lambda: page.get_by_role("checkbox", name=pattern),
        lambda: page.get_by_title(pattern),
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


def _vision_locate(page: Page, text: str) -> Locator | None:
    import os
    if not os.getenv("BDDFRAME_MODEL"):
        return None
    try:
        import base64
        from bddframe.llm.client import ask_vision
        b64 = base64.b64encode(page.screenshot()).decode()
        css = ask_vision(
            prompt=(
                f'Return ONLY a CSS selector for the element labelled "{text}" '
                f'visible in this screenshot. No explanation, just the selector.'
            ),
            image_b64=b64,
        ).strip().strip('`')
        loc = page.locator(css)
        if loc.count() > 0:
            return loc.first
    except Exception:
        pass
    return None
