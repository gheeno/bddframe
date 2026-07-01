"""Unit tests for noodle/resolver/visual_patterns.py — no screen access."""
import pytest
from noodle.resolver.visual_patterns import match


class TestClickImage:
    def test_basic(self):
        r = match('click image "submit_btn.png"')
        assert r == ('click_image', {'template': 'submit_btn.png', 'confidence': 0.85})

    def test_single_quotes(self):
        r = match("click image 'submit_btn.png'")
        assert r is not None
        assert r[1]['template'] == 'submit_btn.png'

    def test_with_confidence(self):
        r = match('click image "submit_btn.png" with confidence 0.75')
        assert r == ('click_image', {'template': 'submit_btn.png', 'confidence': 0.75})

    def test_right_click(self):
        r = match('right-click image "icon.png"')
        assert r == ('right_click_image', {'template': 'icon.png'})

    def test_right_click_no_hyphen(self):
        r = match('rightclick image "icon.png"')
        assert r is not None

    def test_double_click(self):
        r = match('double-click image "icon.png"')
        assert r == ('double_click_image', {'template': 'icon.png'})


class TestScrollAndDrag:
    def test_scroll_down(self):
        r = match('scroll down 3 times')
        assert r == ('scroll', {'direction': 'down', 'clicks': 3})

    def test_scroll_up_singular(self):
        r = match('scroll up 1 time')
        assert r == ('scroll', {'direction': 'up', 'clicks': 1})

    def test_scroll_to_image(self):
        r = match('scroll to image "header.png"')
        assert r == ('scroll_to_image', {'template': 'header.png'})

    def test_drag(self):
        r = match('drag "source.png" to "target.png"')
        assert r == ('drag_image', {'source': 'source.png', 'target': 'target.png'})


class TestTextSteps:
    def test_click_text(self):
        r = match('click text "Submit Order" on screen')
        assert r == ('click_text', {'text': 'Submit Order'})

    def test_assert_text_visible(self):
        r = match('should see text "Order Confirmed" on screen')
        assert r == ('assert_text_visible', {'text': 'Order Confirmed'})

    def test_wait_text(self):
        r = match('wait until text "Loading..." appears on screen')
        assert r == ('wait_text_visible', {'text': 'Loading...'})


class TestKeyboard:
    def test_type(self):
        r = match('type "hello world"')
        assert r == ('type_text', {'text': 'hello world'})

    def test_press_key(self):
        r = match('press key "Enter"')
        assert r == ('press_key', {'key': 'Enter'})


class TestAssertions:
    def test_assert_image_visible(self):
        r = match('should see image "logo.png" on screen')
        assert r == ('assert_image_visible', {'template': 'logo.png'})

    def test_assert_image_hidden(self):
        r = match('should not see image "spinner.png" on screen')
        assert r == ('assert_image_hidden', {'template': 'spinner.png'})

    def test_wait_image_visible(self):
        r = match('wait until image "dialog.png" appears')
        assert r == ('wait_image_visible', {'template': 'dialog.png'})

    def test_wait_image_hidden(self):
        r = match('wait until image "loader.png" disappears')
        assert r == ('wait_image_hidden', {'template': 'loader.png'})


class TestRegion:
    def test_focus_region(self):
        r = match('focus on screen region "top-left"')
        assert r == ('focus_region', {'region': 'top-left'})


class TestNoMatch:
    def test_unknown_returns_none(self):
        assert match('do something completely made up') is None

    def test_empty_returns_none(self):
        assert match('') is None
