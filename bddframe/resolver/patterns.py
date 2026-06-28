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
    'hover': 'hovers',
    'store': 'stores',
    'switch': 'switches',
    'set': 'sets',
    'search': 'searches',
    'close': 'closes',
    'grab': 'grabs',
    'focus': 'focuses',
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

    # Close popups / cookie banners / modals (best-effort, never fails)
    (r'^closes? (?:all )?(?:the )?(?:pop-?ups?|modals?|dialogs?|banners?)(?: windows?)?$',
                                                   'close_popups',   lambda m: {}),

    # Search — fill the search box and submit, in one step
    (r'^searches? for ["\'](.+?)["\']$',           'search',         lambda m: {'query': _q(m.group(1))}),

    # --- Phase D: network mocking, API setup/teardown, test data -------------
    # Mock a network response (Playwright route.fulfill).
    (r'^mocks? ["\'](.+?)["\'] with status (\d+)(?: and body ["\'](.+?)["\'])?$',
                                                   'mock_route',     lambda m: {'url': _q(m.group(1)), 'status': int(m.group(2)), 'body': m.group(3)}),
    # Block requests to a URL glob (route.abort) — e.g. analytics/ads.
    (r'^blocks? requests? to ["\'](.+?)["\']$',    'block_route',    lambda m: {'url': _q(m.group(1))}),
    # API setup/teardown — call an endpoint directly (no browser nav).
    (r'^calls? (GET|POST|PUT|DELETE|PATCH) ["\'](.+?)["\'](?: with body ["\'](.+?)["\'])?$',
                                                   'api_call',       lambda m: {'method': m.group(1).upper(), 'url': _q(m.group(2)), 'body': m.group(3)}),
    # Load a YAML/JSON fixture file into the run-scoped variable store.
    (r'^loads? (?:test )?data from ["\'](.+?)["\']$',
                                                   'load_data',      lambda m: {'file': _q(m.group(1))}),

    # --- Run an external script / command as a step (BFRAME_0016) -------------
    # Execute a user script (py/js/jar/sh/...) or a shell command — e.g. seed a
    # database before the UI test. stdout is captured into `SCRIPT_OUTPUT` (and an
    # optional named var), so a later step can assert on the result.
    (r'^runs? (?:the )?script ["\'](.+?)["\'](?: with (?:args? )?["\'](.+?)["\'])?(?: (?:and )?stor(?:e|ing) (?:the )?output (?:as|in) [\[`]([^\]`]+)[\]`])?$',
                                                   'run_script',     lambda m: {'path': _q(m.group(1)), 'args': m.group(2), 'var': m.group(3)}),
    (r'^(?:the )?script ["\'](.+?)["\'] (?:runs?|executes?|is executed|completes? successfully)$',
                                                   'run_script',     lambda m: {'path': _q(m.group(1)), 'args': None, 'var': None}),
    (r'^runs? (?:the )?command ["\'](.+?)["\'](?: (?:and )?stor(?:e|ing) (?:the )?output (?:as|in) [\[`]([^\]`]+)[\]`])?$',
                                                   'run_command',    lambda m: {'command': _q(m.group(1)), 'var': m.group(2)}),
    (r'^(?:the )?command ["\'](.+?)["\'] (?:runs?|executes?|is executed)$',
                                                   'run_command',    lambda m: {'command': _q(m.group(1)), 'var': None}),

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

    # --- Screen/terminal bridge (BFRAME_0024) — OCR + page-coordinate, no DOM.
    # Raw keyboard type (no locator): "types 'ls -la'" / "enters 'login admin'".
    # MUST follow the fill patterns above so "types X into Y" still routes to fill.
    (r'^(?:types?|enters?) ["\'](.+?)["\']$',      'type_text',      lambda m: {'text': _q(m.group(1))}),
    # Focus OCR/screen reads to a region: "focuses on the 'top-left' region".
    (r'^focus(?:es)? on (?:the )?["\'](.+?)["\'] (?:region|area)$',
                                                   'focus_region',   lambda m: {'region': _q(m.group(1))}),

    # Scoped clicks (11.2) — MUST precede the generic click catch-alls below,
    # which would otherwise swallow the whole "X in the row/section ..." phrase.
    (r'^clicks? ["\']?(.+?)["\']? in (?:the )?row (?:containing|with) ["\'](.+?)["\']$',
                                                   'click_in_row',   lambda m: {'locator': _q(m.group(1)), 'row': _q(m.group(2))}),
    (r'^clicks? ["\']?(.+?)["\']? in (?:the )?["\'](.+?)["\'] (?:section|panel|dialog|region|area)$',
                                                   'click_in_section', lambda m: {'locator': _q(m.group(1)), 'section': _q(m.group(2))}),

    # Keyboard keys (11.1) — a real keypress, distinct from "press the X button"
    # (a click). MUST precede the press-button + click catch-alls.
    (r'^presses? (?:the )?["\']?(Enter|Return|Tab|Escape|Esc|Space|Backspace|Delete|ArrowUp|ArrowDown|ArrowLeft|ArrowRight|Up|Down|Left|Right|Home|End|PageUp|PageDown)["\']?(?: key)?$',
                                                   'press_key',      lambda m: {'key': m.group(1)}),

    # Coordinate / OCR clicks (BFRAME_0024) — MUST precede the generic click
    # catch-alls, which would otherwise capture "at 10, 20" / "on the text ..."
    # as a DOM locator.
    (r'^clicks? at \(?(\d+)\s*,\s*(\d+)\)?$',       'click_at',       lambda m: {'x': int(m.group(1)), 'y': int(m.group(2))}),
    (r'^clicks? on (?:the )?(?:screen )?text ["\'](.+?)["\']$',
                                                   'click_text',     lambda m: {'text': _q(m.group(1))}),

    # Click / Press / Tap
    (r'^clicks? (?:the )?(.+?) button$',           'click',          lambda m: {'locator': _q(m.group(1))}),
    (r'^clicks? (?:the )?(.+?) link$',             'click',          lambda m: {'locator': _q(m.group(1))}),
    (r'^clicks? ["\'](.+?)["\']$',                 'click',          lambda m: {'locator': _q(m.group(1))}),
    (r'^clicks? (?:the )?(.+)$',                   'click',          lambda m: {'locator': _q(m.group(1))}),
    (r'^presses? (?:the )?(.+?) button$',          'click',          lambda m: {'locator': _q(m.group(1))}),
    (r'^taps? (?:the )?(.+)$',                     'click',          lambda m: {'locator': _q(m.group(1))}),

    # Hover (11.1)
    (r'^hovers? (?:over|on) (?:the )?(.+)$',        'hover',          lambda m: {'locator': _q(m.group(1))}),

    # Variable write target: `name` (captured, preferred) or [name] (legacy).
    # Seed a literal into a variable (12.1) — e.g. an expected value.
    (r'^sets? [\[`]([^\]`]+)[\]`] to ["\'](.+?)["\']$',
                                                   'set_var',        lambda m: {'var': m.group(1), 'value': _q(m.group(2))}),

    # Store an element ATTRIBUTE into a variable (12.1) — MUST precede the
    # generic store-text pattern below, which would otherwise eat the phrase.
    (r'^stores? attribute ["\'](.+?)["\'] of (?:the )?(.+?) (?:as|into|in) [\[`]([^\]`]+)[\]`]$',
                                                   'store_attribute', lambda m: {'attribute': _q(m.group(1)), 'locator': _q(m.group(2)), 'var': m.group(3)}),

    # Store/grab element text into a variable (11.1) — usable by later steps.
    (r'^(?:stores?|grabs?) (?:the )?(.+?) (?:as|into|in) [\[`]([^\]`]+)[\]`]$',
                                                   'store_text',     lambda m: {'locator': _q(m.group(1)), 'var': m.group(2)}),

    # Switch into an iframe (11.2)
    (r'^switches? to (?:the )?["\'](.+?)["\'] (?:frame|iframe)$',
                                                   'switch_frame',   lambda m: {'name': _q(m.group(1))}),

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
    # OCR wait (BFRAME_0024) — MUST precede the generic wait-until below.
    (r'^waits? until (?:the )?(?:screen|terminal) (?:shows?|displays?) ["\'](.+?)["\']$',
                                                   'wait_screen_text', lambda m: {'text': _q(m.group(1))}),
    (r'^waits? until ["\'](.+?)["\'] (?:is visible|appears?|loads?)$',
                                                   'wait_visible',     lambda m: {'text': _q(m.group(1))}),
    (r'^waits? until (.+?) (?:is visible|appears?|loads?)$',
                                                   'wait_visible',     lambda m: {'text': m.group(1)}),
    (r'^waits? until ["\'](.+?)["\'] (?:disappears?|is hidden|is gone|vanishes)$',
                                                   'wait_hidden',      lambda m: {'text': _q(m.group(1))}),
    (r'^waits? until (.+?) (?:disappears?|is hidden|is gone|vanishes)$',
                                                   'wait_hidden',      lambda m: {'text': m.group(1)}),
    (r'^waits? (\d+) seconds?$',                   'wait_seconds',     lambda m: {'seconds': int(m.group(1))}),

    # Scroll
    (r'^scrolls? down$',                           'scroll',         lambda m: {'direction': 'down'}),
    (r'^scrolls? up$',                             'scroll',         lambda m: {'direction': 'up'}),
    (r'^scrolls? to ["\'](.+?)["\']$',             'scroll_to',      lambda m: {'locator': _q(m.group(1))}),

    # Assertions
    # Count assertion (11.1) — MUST precede the generic "should see X" below.
    (r'^should see (\d+) ["\']?(.+?)["\']?(?: items?| results?| rows?| elements?| entries?)?$',
                                                   'assert_count',   lambda m: {'count': int(m.group(1)), 'locator': _q(m.group(2))}),
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

    # Table / grid assertions (11.2) — MUST precede the semantic catch-all,
    # which would otherwise eat "... should have ..." / "... should be ...".
    (r'^the (?:grid|table) should have (\d+) rows?$',
                                                   'assert_row_count', lambda m: {'count': int(m.group(1))}),
    (r'^the cell in (?:the )?row ["\'](.+?)["\'] column ["\'](.+?)["\'] should (?:be|contain|equal|show) ["\'](.+?)["\']$',
                                                   'assert_cell',     lambda m: {'row': _q(m.group(1)), 'column': _q(m.group(2)), 'expected': _q(m.group(3))}),

    # Element-scoped assertions (11.1) — attribute / value / state. Also before
    # the semantic catch-all for the same reason.
    (r'^the (.+?) should have attribute ["\'](.+?)["\'] (?:equal to|=|of) ["\'](.+?)["\']$',
                                                   'assert_attribute', lambda m: {'locator': _q(m.group(1)), 'attribute': _q(m.group(2)), 'value': _q(m.group(3))}),
    (r'^the ["\']?(.+?)["\']? (?:field|input|box) should (?:contain|have|show)(?: the)?(?: value| text)? ["\'](.+?)["\']$',
                                                   'assert_value',    lambda m: {'locator': _q(m.group(1)), 'value': _q(m.group(2))}),
    (r'^the ["\']?(.+?)["\']? should have value ["\'](.+?)["\']$',
                                                   'assert_value',    lambda m: {'locator': _q(m.group(1)), 'value': _q(m.group(2))}),
    (r'^the ["\']?(.+?)["\']?(?: (?:button|field|input|box|link|checkbox|element|icon|dropdown|menu))? should be (enabled|disabled|checked|unchecked|selected|editable|read-?only)$',
                                                   'assert_state',    lambda m: {'locator': _q(m.group(1)), 'state': m.group(2)}),

    # Value comparison assertions (12.2) — both operands are already [VAR]-
    # substituted to literals by the time we get here. Order: longest operator
    # phrase first so "greater than or equal to" isn't eaten by "greater than".
    (r'^["\']?(.+?)["\']? should be (?:greater than or equal to|at least) ["\']?(.+?)["\']?$',
                                                   'assert_compare',  lambda m: {'left': _q(m.group(1)), 'op': '>=', 'right': _q(m.group(2))}),
    (r'^["\']?(.+?)["\']? should be (?:less than or equal to|at most) ["\']?(.+?)["\']?$',
                                                   'assert_compare',  lambda m: {'left': _q(m.group(1)), 'op': '<=', 'right': _q(m.group(2))}),
    (r'^["\']?(.+?)["\']? should be (?:greater than|more than) ["\']?(.+?)["\']?$',
                                                   'assert_compare',  lambda m: {'left': _q(m.group(1)), 'op': '>', 'right': _q(m.group(2))}),
    (r'^["\']?(.+?)["\']? should be (?:less than|fewer than) ["\']?(.+?)["\']?$',
                                                   'assert_compare',  lambda m: {'left': _q(m.group(1)), 'op': '<', 'right': _q(m.group(2))}),
    (r'^["\']?(.+?)["\']? should not (?:equal|be equal to) ["\']?(.+?)["\']?$',
                                                   'assert_compare',  lambda m: {'left': _q(m.group(1)), 'op': '!=', 'right': _q(m.group(2))}),
    (r'^["\']?(.+?)["\']? should (?:equal|be equal to) ["\']?(.+?)["\']?$',
                                                   'assert_compare',  lambda m: {'left': _q(m.group(1)), 'op': '==', 'right': _q(m.group(2))}),
    (r'^["\']?(.+?)["\']? should contain ["\']?(.+?)["\']?$',
                                                   'assert_compare',  lambda m: {'left': _q(m.group(1)), 'op': 'contains', 'right': _q(m.group(2))}),

    # OCR / terminal-buffer assertions (BFRAME_0024) — deterministic, no LLM.
    # MUST precede the semantic catch-all, which would otherwise eat them.
    (r'^the (?:screen|terminal) should not (?:show|display) ["\'](.+?)["\']$',
                                                   'assert_screen_text_hidden', lambda m: {'text': _q(m.group(1))}),
    (r'^the (?:screen|terminal) (?:shows?|displays?) ["\'](.+?)["\']$',
                                                   'assert_screen_text', lambda m: {'text': _q(m.group(1))}),
    (r'^the terminal buffer (?:contains?|shows?|includes?) ["\'](.+?)["\']$',
                                                   'assert_buffer',   lambda m: {'text': _q(m.group(1))}),

    # Semantic (vision LLM) assertions
    (r'^the (.+?) should (?:show|display|have) (?:a )?(.+)$',
                                                   'assert_semantic', lambda m: {'assertion': f"{m.group(1)} shows {m.group(2)}"}),
    (r'^the (.+?) should look (.+)$',
                                                   'assert_semantic', lambda m: {'assertion': f"{m.group(1)} looks {m.group(2)}"}),

    # Deterministic pixel baseline (no LLM) — MUST precede the LLM visual_baseline
    # so "should match the baseline" routes to the pixel diff, not the model.
    (r'^the screen should match (?:the )?(?:pixel )?baseline$',
                                                   'pixel_baseline', lambda m: {'name': 'default'}),
    (r'^the ["\'](.+?)["\'] screen should match (?:the )?(?:pixel )?baseline$',
                                                   'pixel_baseline', lambda m: {'name': _q(m.group(1))}),

    # Visual baseline (semantic, LLM)
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
