import re
import time
from playwright.sync_api import Page, expect, TimeoutError as PlaywrightTimeout
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


def wait_load(page: Page):
    page.wait_for_load_state("domcontentloaded")


def wait_visible(page: Page, text: str):
    page.get_by_text(text, exact=False).first.wait_for(state="visible")


def wait_seconds(seconds: int):
    time.sleep(seconds)


def scroll(page: Page, direction: str):
    if direction == "down":
        page.mouse.wheel(0, 500)
    else:
        page.mouse.wheel(0, -500)


def scroll_to(page: Page, locator_text: str):
    loc = find(page, locator_text)
    if loc is None:
        raise AssertionError(f"Could not find element to scroll to: '{locator_text}'")
    loc.scroll_into_view_if_needed()


def screenshot(page: Page, name: str, path: str = "screenshots"):
    import os
    os.makedirs(path, exist_ok=True)
    file_path = f"{path}/{name}.png"
    page.screenshot(path=file_path, full_page=True)
    return file_path
