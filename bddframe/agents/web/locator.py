import os
import re
from playwright.sync_api import Page, Locator
from bddframe.log import logger
from bddframe import healing
from . import pom

# Strict locator mode: when an accessibility strategy matches MORE THAN ONE
# element and no POM entry disambiguates it, strict mode fails the step with
# the candidate list instead of silently taking .first.
# Set by hooks.before_scenario from the @strict tag, or BDDFRAME_STRICT_LOCATOR.
_strict: bool | None = None


def set_strict(value: bool | None):
    global _strict
    _strict = value


# Active iframe scope (11.2). When set by actions.switch_frame, element lookups
# resolve inside this frame instead of the top-level page. Reset per scenario.
_frame = None


def set_frame(frame):
    global _frame
    _frame = frame


def _is_strict() -> bool:
    if _strict is not None:
        return _strict
    return os.getenv("BDDFRAME_STRICT_LOCATOR", "false").lower() == "true"


def find(page: Page, text: str, scope=None) -> Locator | None:
    """
    Resolve a human label to a Playwright Locator.
    Order: accessibility (unique) → POM (if ambiguous or not found)
           → self-heal scroll → self-heal partial → vision LLM.

    `scope` (11.2) constrains the accessibility search to a sub-region — a row
    Locator, a named section, or a frame. Defaults to the active iframe scope
    (set_frame) or the whole page. POM/vision self-heal still use `page`.
    """
    search = scope if scope is not None else (_frame if _frame is not None else page)
    loc, ambiguous = _try_strategies(search, text)

    if loc is not None and not ambiguous:
        return loc.first  # exactly one match — safe

    if ambiguous:
        # Do NOT trust a blind .first. Prefer an explicit POM selector that
        # scopes to the intended element; otherwise escalate per mode.
        scoped = pom.locate(page, text)
        if scoped is not None:
            logger.info(f"\n  📋 POM: disambiguated '{text}' via pom.yaml")
            healing.record(text, "pom-disambiguation")
            return scoped
        return _on_ambiguous(page, text, loc)

    # Nothing found — run the self-heal chain.
    # Self-heal 1: scroll and retry
    page.mouse.wheel(0, 300)
    loc, ambiguous = _try_strategies(search, text)
    if loc is not None and not ambiguous:
        logger.info(f"\n  🔧 Healed: found '{text}' after scroll")
        healing.record(text, "scroll")
        return loc.first

    # Self-heal 2: partial text (first word)
    first_word = text.split()[0] if text.split() else text
    if first_word != text:
        loc2, amb2 = _try_strategies(search, first_word)
        if loc2 is not None and not amb2:
            logger.info(f"\n  🔧 Healed: matched '{text}' via partial text '{first_word}'")
            healing.record(text, "partial-text", f"matched on '{first_word}'")
            return loc2.first

    # Fallback 1: POM YAML
    loc = pom.locate(page, text)
    if loc:
        logger.info(f"\n  📋 POM: resolved '{text}' via pom.yaml")
        return loc

    # Fallback 2: vision LLM
    loc = _vision_locate(page, text)
    if loc:
        logger.info(f"\n  🔧 Healed: found '{text}' via vision LLM")
        healing.record(text, "vision-llm")
        return loc

    return None


def wait_for(page: Page, text: str, timeout: int | None = None):
    """
    Wait for an element to become visible.
    Tries accessibility strategies and POM YAML — handles dynamic/slow-loading content.
    """
    import time
    timeout_ms = timeout or int(os.getenv("BDDFRAME_TIMEOUT", "10000"))

    # Try POM first for named elements.
    loc = pom.locate(page, text)
    if loc is not None:
        loc.wait_for(state="visible", timeout=timeout_ms)
        return

    # Text: poll for the first VISIBLE match — skip sr-only/hidden duplicates
    # that would otherwise sort first and never become visible.
    matches = page.get_by_text(text, exact=False)
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        for i in range(min(matches.count(), 30)):
            try:
                if matches.nth(i).is_visible():
                    return
            except Exception:
                pass
        page.wait_for_timeout(250)
    raise AssertionError(f"Timed out waiting for visible text '{text}' ({timeout_ms}ms)")


def wait_hidden(page: Page, text: str, timeout: int | None = None):
    """Wait until an element/text is gone or no longer visible (mirror of wait_for)."""
    import time
    timeout_ms = timeout or int(os.getenv("BDDFRAME_TIMEOUT", "10000"))

    loc = pom.locate(page, text)
    if loc is not None:
        loc.wait_for(state="hidden", timeout=timeout_ms)
        return

    matches = page.get_by_text(text, exact=False)
    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        visible = False
        for i in range(min(matches.count(), 30)):
            try:
                if matches.nth(i).is_visible():
                    visible = True
                    break
            except Exception:
                pass
        if not visible:
            return
        page.wait_for_timeout(250)
    raise AssertionError(f"Timed out waiting for '{text}' to disappear ({timeout_ms}ms)")


def _try_strategies(scope, text: str) -> tuple[Locator | None, bool]:
    """
    Returns (locator, ambiguous).
    `scope` is anything with the get_by_* API — a Page, Frame, or Locator —
    so the same strategies work scoped to a row/section/frame (11.2).
    Strategies are tried in priority order; the first one that matches wins.
    Returns the FULL locator (not .first) so ambiguous candidates can be
    enumerated, plus whether it matched exactly one element (ambiguous=False)
    or several (ambiguous=True). Callers take .first.
    """
    pattern = re.compile(re.escape(text), re.IGNORECASE)
    strategies = [
        lambda: scope.get_by_role("button",   name=pattern),
        lambda: scope.get_by_role("link",     name=pattern),
        lambda: scope.get_by_label(pattern),
        lambda: scope.get_by_placeholder(pattern),
        lambda: scope.get_by_role("textbox",  name=pattern),
        lambda: scope.get_by_role("combobox", name=pattern),
        lambda: scope.get_by_role("checkbox", name=pattern),
        lambda: scope.get_by_title(pattern),
        lambda: scope.get_by_text(pattern, exact=False),
    ]
    for strategy in strategies:
        try:
            loc = strategy()
            count = loc.count()
            if count >= 1:
                return loc, count > 1
        except Exception:
            continue
    return None, False


def _on_ambiguous(page: Page, text: str, loc: Locator):
    """
    Reached when accessibility matched >1 element and no POM entry exists.
    Strict: fail with the candidate list. Lenient: warn + return .first.
    """
    candidates = _describe_candidates(loc)
    msg = (
        f"Ambiguous locator '{text}' — matched multiple elements:\n"
        + "\n".join(f"    [{i}] {c}" for i, c in enumerate(candidates))
        + f"\n  → Add a scoped entry to pom.yaml under key '{text.lower()}' "
        f"(e.g. an xpath/css that targets the intended one)."
    )
    if _is_strict():
        raise AssertionError(msg)
    logger.warning(f"\n  ⚠️  {msg}\n  (lenient mode — using the first match; "
          f"set BDDFRAME_STRICT_LOCATOR=true or @strict to fail instead)")
    return loc.first


def _describe_candidates(loc: Locator, limit: int = 5) -> list[str]:
    """Short text/role description of each ambiguous candidate, for evidence."""
    out = []
    try:
        handles = loc.element_handles()[:limit]
        for h in handles:
            try:
                tag = h.evaluate("e => e.tagName.toLowerCase()")
                txt = (h.inner_text() or "").strip().replace("\n", " ")[:50]
                out.append(f"<{tag}> {txt!r}")
            except Exception:
                out.append("<?>")
    except Exception:
        out.append("(could not enumerate candidates)")
    return out or ["(none)"]


def _parse_vision_selector(raw: str) -> str | None:
    """Extract a CSS selector from the vision model's reply, or None when it
    reports it can't find the element. Tolerates a ```json fence, prose around
    the object, the structured {"selector": ...} form, and a bare selector
    string. Pure — unit-testable without a page or model.

    The structured null path ({"selector": null}) is what stops a hallucinated
    selector from being fed to page.locator: a model that can't see the element
    says so instead of inventing one."""
    import json
    import re
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    # Strip a markdown code fence — the old code only stripped single backticks,
    # so a fenced reply broke page.locator(). This is the headline 0018-2 fix.
    text = re.sub(r'^```[a-zA-Z]*\n?|\n?```$', '', text).strip()
    # Structured form: {"selector": "<css>"} or {"selector": null}.
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            obj = None
        if isinstance(obj, dict) and 'selector' in obj:
            sel = obj['selector']
            return sel.strip() if isinstance(sel, str) and sel.strip() else None
    # Bare-selector fallback (model ignored the JSON instruction). Still gated
    # by loc.count() in the caller, so a hallucinated selector matches nothing.
    text = text.strip('`').strip()
    return text or None


def _vision_locate(page: Page, text: str) -> Locator | None:
    if not os.getenv("BDDFRAME_MODEL"):
        return None
    try:
        import base64
        from bddframe.llm.client import ask_vision
        b64 = base64.b64encode(page.screenshot()).decode()
        raw = ask_vision(
            prompt=(
                f'Find the element labelled "{text}" in this screenshot and return '
                f'a CSS selector for it. Reply with JSON only: '
                f'{{"selector": "<css>"}} if you can identify it, or '
                f'{{"selector": null}} if you cannot. No other text.'
            ),
            image_b64=b64,
        )
        css = _parse_vision_selector(raw)
        if not css:
            return None
        loc = page.locator(css)
        if loc.count() > 0:
            return loc.first
    except Exception:
        pass
    return None
