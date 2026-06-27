"""Dispatch visual step actions to the visual agent."""
import time

from bddframe.resolver.visual_patterns import match
from bddframe.agents.visual import (
    matcher, ocr, desktop, vision_locate, regions
)

_WAIT_POLL = 0.5
_WAIT_TIMEOUT = 10.0


def execute_visual_step(step_text: str):
    result = match(step_text)
    if result is None:
        raise AssertionError(
            f'\nNo visual pattern matched: "{step_text}"\n'
            "  → Add a pattern to bddframe/resolver/visual_patterns.py"
        )
    action_type, params = result
    _dispatch(action_type, params)


def _dispatch(action_type: str, params: dict):
    if action_type == "click_image":
        coords = _locate_image(params["template"], params.get("confidence", 0.85))
        desktop.click(*coords)

    elif action_type == "right_click_image":
        coords = _locate_image(params["template"])
        desktop.right_click(*coords)

    elif action_type == "double_click_image":
        coords = _locate_image(params["template"])
        desktop.double_click(*coords)

    elif action_type == "scroll_to_image":
        coords = desktop.scroll_to_image(params["template"])
        if coords is None:
            raise AssertionError(f"Could not scroll to image: '{params['template']}'")

    elif action_type == "assert_image_visible":
        coords = matcher.find_on_screen(params["template"])
        if coords is None:
            raise AssertionError(f"Expected image on screen: '{params['template']}'")

    elif action_type == "assert_image_hidden":
        coords = matcher.find_on_screen(params["template"])
        if coords is not None:
            raise AssertionError(f"Expected image NOT on screen but found it: '{params['template']}'")

    elif action_type == "wait_image_visible":
        _wait_for(lambda: matcher.find_on_screen(params["template"]) is not None,
                  f"image '{params['template']}' to appear")

    elif action_type == "wait_image_hidden":
        _wait_for(lambda: matcher.find_on_screen(params["template"]) is None,
                  f"image '{params['template']}' to disappear")

    elif action_type == "click_text":
        coords = ocr.find_text_on_screen(params["text"])
        if coords is None:
            raise AssertionError(f"Could not find text on screen: '{params['text']}'")
        desktop.click(*coords)

    elif action_type == "assert_text_visible":
        coords = ocr.find_text_on_screen(params["text"])
        if coords is None:
            raise AssertionError(f"Expected text on screen: '{params['text']}'")

    elif action_type == "wait_text_visible":
        _wait_for(lambda: ocr.find_text_on_screen(params["text"]) is not None,
                  f"text '{params['text']}' to appear on screen")

    elif action_type == "type_text":
        desktop.type_text(params["text"])

    elif action_type == "press_key":
        desktop.press_key(params["key"])

    elif action_type == "scroll":
        desktop.scroll(params["direction"], params.get("clicks", 3))

    elif action_type == "drag_image":
        src = _locate_image(params["source"])
        dst = _locate_image(params["target"])
        desktop.drag(src[0], src[1], dst[0], dst[1])

    elif action_type == "focus_region":
        # Parsed for future use; sets an active region on the context.
        # For now, validates the region string is well-formed.
        regions.parse_region(params["region"])

    else:
        raise AssertionError(f"Unknown visual action type: '{action_type}'")


def _locate_image(template: str, confidence: float = 0.85) -> tuple[int, int]:
    """Try image match, then vision LLM fallback."""
    coords = matcher.find_on_screen(template, confidence)
    if coords:
        return coords
    coords = vision_locate.locate_by_description(template)
    if coords:
        return coords
    raise AssertionError(f"Could not find image on screen: '{template}'")


def _wait_for(condition, description: str, timeout: float = _WAIT_TIMEOUT):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(_WAIT_POLL)
    raise AssertionError(f"Timed out waiting for {description}")
