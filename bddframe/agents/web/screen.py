"""Web pixel/OCR bridge — drive canvas/terminal UIs that have no semantic DOM.

Frames come from page.screenshot(); actions go through Playwright's mouse and
keyboard in page (CSS-pixel) coordinates. OCR is deterministic (pytesseract);
a vision LLM is a coordinate fallback only when BDDFRAME_MODEL is set.

Coordinate correctness (the easy thing to get wrong):
  - page.screenshot() pixels are at devicePixelRatio (dpr).
  - page.mouse takes CSS pixels.
  - screenshot is viewport-only (full_page=False) so its origin matches mouse's.
So OCR (device px) is divided by dpr before clicking, and a focus region (CSS
px from the viewport) is multiplied by dpr before cropping the screenshot.
"""
import io
import os
import time

from PIL import Image

from bddframe.log import logger
from bddframe.agents.visual import ocr

_WAIT_POLL = 0.5

# Per-scenario focus region in viewport CSS pixels (or None). Set by the
# `focuses on "<region>"` step, reset between scenarios by hooks.
_region = None


def set_region(region):
    global _region
    _region = region


def _dpr(page):
    try:
        return float(page.evaluate("window.devicePixelRatio")) or 1.0
    except Exception:
        return 1.0


def _to_css(x, y, dpr):
    """Device-pixel OCR coords → CSS-pixel mouse coords. Pure."""
    return x / dpr, y / dpr


def _device_region(page):
    """The CSS-pixel focus region scaled to the screenshot's device pixels."""
    if not _region:
        return None
    d = _dpr(page)
    return {k: int(v * d) for k, v in _region.items()}


def _screenshot_image(page):
    return Image.open(io.BytesIO(page.screenshot(full_page=False)))


def _screen_text(page):
    return ocr.find_all_text_in_image(_screenshot_image(page), _device_region(page))


# --- actions ----------------------------------------------------------------

def type_text(page, text):
    """Type into whatever is focused — no locator (terminals, canvas inputs)."""
    page.keyboard.type(text)


def click_at(page, x, y):
    page.mouse.click(float(x), float(y))


def _locate(page, text):
    """Rendered position of `text` → CSS-pixel (x,y), or None. OCR first;
    vision-LLM coordinate fallback when BDDFRAME_MODEL is set."""
    img = _screenshot_image(page)
    hit = ocr.find_text_in_image(img, text, _device_region(page))
    if hit is None and os.getenv("BDDFRAME_MODEL"):
        from bddframe.agents.visual import vision_locate
        hit = vision_locate.locate_by_description(text, image=img)
    if hit is None:
        return None
    return _to_css(hit[0], hit[1], _dpr(page))


def click_text(page, text):
    pos = _locate(page, text)
    if pos is None:
        raise AssertionError(f"Could not find text on screen to click: '{text}'")
    page.mouse.click(pos[0], pos[1])


def assert_text_visible(page, text):
    if text.lower() not in _screen_text(page).lower():
        raise AssertionError(
            f"Expected screen to show '{text}' — not found by OCR.\nURL: {page.url}"
        )


def assert_text_hidden(page, text):
    if text.lower() in _screen_text(page).lower():
        raise AssertionError(
            f"Expected screen NOT to show '{text}' — but OCR found it.\nURL: {page.url}"
        )


def wait_text_visible(page, text, timeout=None):
    secs = (timeout or int(os.getenv("BDDFRAME_TIMEOUT", "10000")) / 1000)
    deadline = time.monotonic() + secs
    while time.monotonic() < deadline:
        if text.lower() in _screen_text(page).lower():
            logger.info(f"\n  👁  Screen shows '{text}'")
            return
        time.sleep(_WAIT_POLL)
    raise AssertionError(f"Timed out ({secs:.0f}s) waiting for screen to show '{text}'")


# --- DOM-renderer terminals (gap 6): text IS in the DOM ---------------------

_TERMINAL_SELECTORS = ".xterm-rows, .xterm-screen, pre, code, [role=log]"


def buffer_text(page):
    """Joined inner_text of the terminal container — for DOM renderers
    (xterm.js DOM mode) and <pre>/<code> blobs where text lives in the DOM.
    POM key 'terminal' wins; otherwise a default selector set."""
    from bddframe.agents.web import pom
    loc = pom.locate(page, "terminal") or page.locator(_TERMINAL_SELECTORS)
    n = loc.count()
    if n == 0:
        return ""
    return "\n".join((loc.nth(i).inner_text() or "") for i in range(min(n, 20)))


def assert_buffer_contains(page, text):
    buf = buffer_text(page)
    if text.lower() not in buf.lower():
        raise AssertionError(
            f"Terminal buffer does not contain '{text}'.\nBuffer:\n{buf[:500]}\nURL: {page.url}"
        )
