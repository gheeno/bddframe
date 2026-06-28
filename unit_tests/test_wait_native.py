"""BFRAME_0018-4 — wait_for / wait_hidden use Playwright's native wait.

The old code ran a manual 250ms Python polling loop with a race window between
a poll and the element (dis)appearing. These tests assert we now delegate to
Playwright's native locator.wait_for (MutationObserver-backed) on both the POM
and the text paths, and surface a clean AssertionError on timeout. Page is
mocked — no browser.
"""
from unittest.mock import MagicMock

import pytest

from bddframe.agents.web import locator


def test_wait_for_uses_pom_native_wait(monkeypatch):
    pom_loc = MagicMock()
    monkeypatch.setattr(locator.pom, "locate", lambda page, text: pom_loc)
    page = MagicMock()

    locator.wait_for(page, "Login", timeout=5000)

    pom_loc.wait_for.assert_called_once_with(state="visible", timeout=5000)
    page.get_by_text.assert_not_called()   # POM short-circuits the text path


def test_wait_for_text_path_filters_visible_and_waits(monkeypatch):
    monkeypatch.setattr(locator.pom, "locate", lambda page, text: None)
    page = MagicMock()

    locator.wait_for(page, "Welcome", timeout=3000)

    page.get_by_text.assert_called_once_with("Welcome", exact=False)
    visible = page.get_by_text.return_value.locator
    visible.assert_called_once_with("visible=true")
    visible.return_value.first.wait_for.assert_called_once_with(
        state="visible", timeout=3000
    )


def test_wait_for_timeout_raises_assertion(monkeypatch):
    monkeypatch.setattr(locator.pom, "locate", lambda page, text: None)
    page = MagicMock()
    page.get_by_text.return_value.locator.return_value.first.wait_for.side_effect = (
        RuntimeError("timeout")
    )

    with pytest.raises(AssertionError, match="Timed out waiting for visible text 'Ghost'"):
        locator.wait_for(page, "Ghost", timeout=1000)


def test_wait_hidden_text_path_waits_hidden(monkeypatch):
    monkeypatch.setattr(locator.pom, "locate", lambda page, text: None)
    page = MagicMock()

    locator.wait_hidden(page, "Spinner", timeout=2000)

    visible = page.get_by_text.return_value.locator
    visible.assert_called_once_with("visible=true")
    visible.return_value.first.wait_for.assert_called_once_with(
        state="hidden", timeout=2000
    )


def test_wait_hidden_timeout_raises_assertion(monkeypatch):
    monkeypatch.setattr(locator.pom, "locate", lambda page, text: None)
    page = MagicMock()
    page.get_by_text.return_value.locator.return_value.first.wait_for.side_effect = (
        RuntimeError("still there")
    )

    with pytest.raises(AssertionError, match="Timed out waiting for 'Spinner' to disappear"):
        locator.wait_hidden(page, "Spinner", timeout=1000)
