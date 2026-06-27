"""
Tier-1 step patterns for the visual/desktop agent.
Same structure as patterns.py — PATTERNS list + match() function.
"""
import re

PATTERNS = [
    # Image matching
    (r'^click image ["\'](.+?)["\']$',
     'click_image', lambda m: {'template': m.group(1), 'confidence': 0.85}),

    (r'^click image ["\'](.+?)["\'] with confidence ([\d.]+)$',
     'click_image', lambda m: {'template': m.group(1), 'confidence': float(m.group(2))}),

    (r'^right-?click image ["\'](.+?)["\']$',
     'right_click_image', lambda m: {'template': m.group(1)}),

    (r'^double-?click image ["\'](.+?)["\']$',
     'double_click_image', lambda m: {'template': m.group(1)}),

    (r'^scroll to image ["\'](.+?)["\']$',
     'scroll_to_image', lambda m: {'template': m.group(1)}),

    (r'^(?:i )?should see image ["\'](.+?)["\'] on screen$',
     'assert_image_visible', lambda m: {'template': m.group(1)}),

    (r'^(?:i )?should not see image ["\'](.+?)["\'] on screen$',
     'assert_image_hidden', lambda m: {'template': m.group(1)}),

    (r'^wait until image ["\'](.+?)["\'] appears?$',
     'wait_image_visible', lambda m: {'template': m.group(1)}),

    (r'^wait until image ["\'](.+?)["\'] disappears?$',
     'wait_image_hidden', lambda m: {'template': m.group(1)}),

    # OCR / text on screen
    (r'^click text ["\'](.+?)["\'] on screen$',
     'click_text', lambda m: {'text': m.group(1)}),

    (r'^(?:i )?should see text ["\'](.+?)["\'] on screen$',
     'assert_text_visible', lambda m: {'text': m.group(1)}),

    (r'^wait until text ["\'](.+?)["\'] appears? on screen$',
     'wait_text_visible', lambda m: {'text': m.group(1)}),

    # Keyboard / typing
    (r'^type ["\'](.+?)["\']$',
     'type_text', lambda m: {'text': m.group(1)}),

    (r'^press key ["\'](.+?)["\']$',
     'press_key', lambda m: {'key': m.group(1)}),

    # Scroll
    (r'^scroll down (\d+) times?$',
     'scroll', lambda m: {'direction': 'down', 'clicks': int(m.group(1))}),

    (r'^scroll up (\d+) times?$',
     'scroll', lambda m: {'direction': 'up', 'clicks': int(m.group(1))}),

    # Drag
    (r'^drag ["\'](.+?)["\'] to ["\'](.+?)["\']$',
     'drag_image', lambda m: {'source': m.group(1), 'target': m.group(2)}),

    # Region focus
    (r'^focus on screen region ["\'](.+?)["\']$',
     'focus_region', lambda m: {'region': m.group(1)}),
]


def match(step_text: str):
    """Return (action_type, params) or None."""
    for pattern, action_type, extractor in PATTERNS:
        m = re.match(pattern, step_text.strip(), re.IGNORECASE)
        if m:
            return action_type, extractor(m)
    return None
