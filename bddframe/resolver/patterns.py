import re


def _q(s: str) -> str:
    """Strip surrounding single or double quotes from a captured group."""
    s = s.strip()
    if len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
        return s[1:-1]
    return s


def normalize_subject(text: str) -> str:
    """
    Strip the grammatical subject so patterns only describe the action.
    Accepts: User, The user, As a user, As an end user, I
    e.g. "User clicks the login button" → "clicks the login button"
         "I click the login button"     → "clicks the login button"  (normalised to 3rd person)
    """
    m = re.match(
        r'^(?:As an?\s+(?:end\s+)?user,?\s+|(?:The\s+)?[Uu]ser\s+|I\s+)',
        text
    )
    if not m:
        return text
    remainder = text[m.end():]
    # normalise 1st-person verb to 3rd-person so a single verb pattern covers both
    # "am" → "is",  "click" → "clicks", "enter" → "enters", etc.
    # Only touches the very first word.
    remainder = _to_third_person(remainder)
    return remainder


_FIRST_TO_THIRD = {
    'am': 'is',
    'enter': 'enters',
    'type': 'types',
    'fill': 'fills',
    'click': 'clicks',
    'press': 'presses',
    'tap': 'taps',
    'select': 'selects',
    'check': 'checks',
    'uncheck': 'unchecks',
    'wait': 'waits',
    'scroll': 'scrolls',
    'take': 'takes',
    'clear': 'clears',
    'open': 'opens',
    'go': 'goes',
    'navigate': 'navigates',
    'should': 'should',  # modal — no change
}


def _to_third_person(text: str) -> str:
    first_word = text.split()[0].lower() if text.split() else ''
    third = _FIRST_TO_THIRD.get(first_word)
    if third and first_word != third:
        return third + text[len(first_word):]
    return text


# ---------------------------------------------------------------------------
# Patterns — written in 3rd-person (after normalize_subject).
# Each entry: (regex, action_type, param_extractor)
# Patterns tried top-to-bottom; first match wins.
# ---------------------------------------------------------------------------
PATTERNS = [
    # Page pin (9.3) — set the active POM page for SPAs where the URL is static.
    # Must precede the navigate patterns; ends in " page" so it can't be a URL.
    (r'^is on (?:the )?["\'](.+?)["\'] page$',     'set_page',       lambda m: {'name': _q(m.group(1))}),

    # Navigate
    (r'^is on ["\'](.+)["\']$',                   'navigate',       lambda m: {'url': _q(m.group(1))}),
    (r'^navigates? to ["\'](.+)["\']$',            'navigate',       lambda m: {'url': _q(m.group(1))}),
    (r'^opens? ["\'](.+)["\']$',                   'navigate',       lambda m: {'url': _q(m.group(1))}),
    (r'^goes? to ["\'](.+)["\']$',                 'navigate',       lambda m: {'url': _q(m.group(1))}),

    # Fill / Enter / Type
    (r'^enters? (.+?) in(?:to)? (?:the )?(.+?) (?:field|box|input)$',
                                                   'fill',           lambda m: {'value': _q(m.group(1)), 'locator': _q(m.group(2))}),
    (r'^types? (.+?) (?:in|into) (?:the )?(.+)$',
                                                   'fill',           lambda m: {'value': _q(m.group(1)), 'locator': _q(m.group(2))}),
    (r'^fills? (?:in )?(?:the )?(.+?) with (.+)$',
                                                   'fill',           lambda m: {'locator': _q(m.group(1)), 'value': _q(m.group(2))}),
    (r'^clears? (?:the )?(.+?) (?:field|box|input)$',
                                                   'clear',          lambda m: {'locator': _q(m.group(1))}),

    # Click / Press / Tap
    (r'^clicks? (?:the )?(.+?) button$',           'click',          lambda m: {'locator': _q(m.group(1))}),
    (r'^clicks? (?:the )?(.+?) link$',             'click',          lambda m: {'locator': _q(m.group(1))}),
    (r'^clicks? ["\'](.+?)["\']$',                 'click',          lambda m: {'locator': _q(m.group(1))}),
    (r'^clicks? (?:the )?(.+)$',                   'click',          lambda m: {'locator': _q(m.group(1))}),
    (r'^presses? (?:the )?(.+?) button$',          'click',          lambda m: {'locator': _q(m.group(1))}),
    (r'^taps? (?:the )?(.+)$',                     'click',          lambda m: {'locator': _q(m.group(1))}),

    # Select / Check
    (r'^selects? ["\'](.+?)["\'] from (?:the )?(.+)$',
                                                   'select',         lambda m: {'value': _q(m.group(1)), 'locator': _q(m.group(2))}),
    (r'^checks? (?:the )?["\']?(.+?)["\']? checkbox$',
                                                   'check',          lambda m: {'locator': _q(m.group(1))}),
    (r'^unchecks? (?:the )?["\']?(.+?)["\']? checkbox$',
                                                   'uncheck',        lambda m: {'locator': _q(m.group(1))}),

    # Wait
    (r'^waits? for (?:the )?page to (?:load|be ready)$',
                                                   'wait_load',        lambda m: {}),
    (r'^waits? for (?:the )?page to fully load$',
                                                   'wait_networkidle', lambda m: {}),
    (r'^waits? for (?:the )?network to be idle$',
                                                   'wait_networkidle', lambda m: {}),
    (r'^waits? until ["\'](.+?)["\'] (?:is visible|appears?|loads?)$',
                                                   'wait_visible',     lambda m: {'text': _q(m.group(1))}),
    (r'^waits? until (.+?) (?:is visible|appears?|loads?)$',
                                                   'wait_visible',     lambda m: {'text': m.group(1)}),
    (r'^waits? (\d+) seconds?$',                   'wait_seconds',     lambda m: {'seconds': int(m.group(1))}),

    # Scroll
    (r'^scrolls? down$',                           'scroll',         lambda m: {'direction': 'down'}),
    (r'^scrolls? up$',                             'scroll',         lambda m: {'direction': 'up'}),
    (r'^scrolls? to ["\'](.+?)["\']$',             'scroll_to',      lambda m: {'locator': _q(m.group(1))}),

    # Assertions
    (r'^should see ["\'](.+?)["\']$',              'assert_visible', lambda m: {'text': _q(m.group(1))}),
    (r'^should see (.+)$',                         'assert_visible', lambda m: {'text': m.group(1)}),
    (r'^should not see ["\'](.+?)["\']$',          'assert_hidden',  lambda m: {'text': _q(m.group(1))}),
    (r'^should not see (.+)$',                     'assert_hidden',  lambda m: {'text': m.group(1)}),
    (r'^should be (?:on|at) (?:the )?(.+?) page$',
                                                   'assert_url',     lambda m: {'fragment': m.group(1)}),
    (r'^should have url containing ["\'](.+?)["\']$',
                                                   'assert_url',     lambda m: {'fragment': _q(m.group(1))}),

    # Title assertion
    (r'^the page title should (?:contain|include) ["\'](.+?)["\']$',
                                                   'assert_title',    lambda m: {'fragment': _q(m.group(1))}),

    # Semantic (vision LLM) assertions
    (r'^the (.+?) should (?:show|display|have) (?:a )?(.+)$',
                                                   'assert_semantic', lambda m: {'assertion': f"{m.group(1)} shows {m.group(2)}"}),
    (r'^the (.+?) should look (.+)$',
                                                   'assert_semantic', lambda m: {'assertion': f"{m.group(1)} looks {m.group(2)}"}),

    # Visual baseline
    (r'^the screen should look the same as before(?: ignoring (?:the )?(.+))?$',
                                                   'visual_baseline', lambda m: {'name': 'default', 'ignore': m.group(1)}),
    (r'^the ["\'](.+?)["\'] screen should look the same as before(?: ignoring (?:the )?(.+))?$',
                                                   'visual_baseline', lambda m: {'name': _q(m.group(1)), 'ignore': m.group(2)}),

    # Screenshot
    (r'^takes? a screenshot(?: ["\'](.+?)["\'])?$',
                                                   'screenshot',      lambda m: {'name': _q(m.group(1)) if m.group(1) else 'manual'}),
]


def match(step_text: str):
    """Return (action_type, params) or None."""
    for pattern, action_type, extractor in PATTERNS:
        m = re.match(pattern, step_text, re.IGNORECASE)
        if m:
            return action_type, extractor(m)
    return None
