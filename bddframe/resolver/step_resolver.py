import os
from .patterns import match as pattern_match, normalize_subject

# Every action type the runner can dispatch (orchestrator/runner.py). The LLM
# fallback is validated against this — a syntactically valid JSON with a bogus
# `type` would otherwise dispatch the wrong action (or crash deep in the runner
# with no step context). ponytail: hand-kept mirror of runner.py's if/elif;
# the runner is a flat dispatch with no list to import. If a new action type is
# added there, add it here (test_llm_resolve_rejects guards the common slips).
VALID_TYPES = frozenset({
    'api_call', 'assert_attribute', 'assert_cell', 'assert_compare',
    'assert_count', 'assert_hidden', 'assert_row_count', 'assert_semantic',
    'assert_state', 'assert_title', 'assert_url', 'assert_value',
    'assert_visible', 'block_route', 'check', 'clear', 'click',
    'click_in_row', 'click_in_section', 'close_popups', 'fill', 'hover',
    'load_data', 'mock_route', 'navigate', 'pixel_baseline', 'press_key',
    'run_command', 'run_script', 'screenshot', 'scroll', 'scroll_to',
    'search', 'select', 'set_page', 'set_var', 'store_attribute',
    'store_text', 'switch_frame', 'uncheck', 'visual_baseline', 'wait_hidden',
    'wait_load', 'wait_networkidle', 'wait_seconds', 'wait_visible',
})


def resolve(step_text: str) -> dict:
    """
    Tier 1: normalize subject → pattern match.
    Tier 2: LLM fallback (only if BDDFRAME_MODEL is set).
    Raises AssertionError if neither resolves the step.
    """
    normalized = normalize_subject(step_text)
    result = pattern_match(normalized)
    if result:
        action_type, params = result
        return {'type': action_type, **params}

    if os.getenv('BDDFRAME_MODEL'):
        return _llm_resolve(step_text)

    raise AssertionError(
        f"\nNo pattern matched: \"{step_text}\"\n"
        f"  Normalized to:      \"{normalized}\"\n"
        "  → Add a pattern to bddframe/resolver/patterns.py\n"
        "  → OR set BDDFRAME_MODEL in .env to enable LLM fallback"
    )


def _llm_resolve(step_text: str) -> dict:
    try:
        from bddframe.llm.client import ask
    except ImportError:
        raise AssertionError("LLM fallback requires: pip install bddframe[llm]")

    prompt = f"""You are a test automation interpreter. Convert this test step to a JSON action.

Step: "{step_text}"

Valid action types: navigate, search, close_popups, click, fill, hover, press_key, clear, select, check, uncheck, assert_visible, assert_hidden, assert_url, assert_value, assert_state, assert_attribute, assert_count, store_text, scroll, screenshot, wait_load, wait_visible, wait_hidden

Param keys by type: click/hover/clear -> locator; fill -> locator,value; press_key -> key; assert_visible/assert_hidden/wait_visible/wait_hidden -> text; assert_value -> locator,value; assert_state -> locator,state; assert_attribute -> locator,attribute,value; assert_count -> count,locator; store_text -> locator,var; set_var -> var,value; store_attribute -> attribute,locator,var; assert_compare -> left,op,right

Reply with JSON only, example: {{"type": "click", "locator": "Login"}}
"""
    import json
    # One retry: models occasionally prefix the JSON with a stray sentence.
    raw = ask(prompt)
    action = _parse_action(raw)
    if action is None:
        raw = ask(prompt)
        action = _parse_action(raw)
    if action is None:
        raise AssertionError(
            f"LLM returned unparseable response for: \"{step_text}\"\nResponse: {raw}"
        )

    t = action.get('type')
    if t not in VALID_TYPES:
        raise AssertionError(
            f"LLM returned an unknown action type {t!r} for: \"{step_text}\"\n"
            f"Response: {raw}\n"
            f"  → Valid types: {', '.join(sorted(VALID_TYPES))}"
        )
    return action


def _parse_action(raw: str) -> dict | None:
    """Parse the model's reply into an action dict, or None if it isn't JSON.
    Tolerates a ```json fence and leading/trailing prose around the object."""
    import json
    import re
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    # Strip a markdown code fence if the model wrapped the JSON in one.
    text = re.sub(r'^```[a-zA-Z]*\n?|\n?```$', '', text).strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        # Fall back to the first {...} object embedded in surrounding prose.
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return obj if isinstance(obj, dict) else None
