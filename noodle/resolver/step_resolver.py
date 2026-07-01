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
    'load_data', 'load_resource', 'mock_route', 'navigate', 'pixel_baseline', 'press_key',
    'run_command', 'run_script', 'screenshot', 'scroll', 'scroll_to',
    'search', 'select', 'set_page', 'set_var', 'store_attribute',
    'store_text', 'switch_frame', 'uncheck', 'visual_baseline', 'wait_hidden',
    'wait_load', 'wait_networkidle', 'wait_seconds', 'wait_visible',
    # BFRAME_0024 — web pixel/OCR bridge (canvas & terminal UIs)
    'type_text', 'click_at', 'click_text', 'assert_screen_text',
    'assert_screen_text_hidden', 'wait_screen_text', 'assert_buffer',
    'focus_region',
    # BFRAME_0025 — browser history, extra clicks, form submit, tab/window
    'go_back', 'go_forward', 'reload', 'double_click', 'right_click', 'submit',
    'assert_new_tab', 'switch_tab', 'close_tab',
    # BFRAME_0029 — proper REST HTTP client
    'rest_set_header', 'rest_call', 'rest_assert_status', 'rest_assert_body',
    'rest_assert_body_table', 'rest_assert_header', 'rest_assert_header_table',
    'rest_extract_json',
})


def resolve(step_text: str) -> dict:
    """
    auto mode (default): pattern match first, LLM fallback on no match.
    full mode (NOODLE_LLM_MODE=full): skip patterns, every step goes to the LLM.

    Either way the LLM is only reachable with NOODLE_MODEL set.
    Raises AssertionError if the step can't be resolved.
    """
    full = os.getenv('NOODLE_LLM_MODE', 'auto').lower() == 'full'

    if not full:
        normalized = normalize_subject(step_text)
        result = pattern_match(normalized)
        if result:
            action_type, params = result
            return {'type': action_type, **params}
    else:
        normalized = normalize_subject(step_text)

    if os.getenv('NOODLE_MODEL'):
        return _llm_resolve(step_text)

    if full:
        raise AssertionError(
            f"\nNOODLE_LLM_MODE=full but NOODLE_MODEL is not set: \"{step_text}\"\n"
            "  → Set NOODLE_MODEL in .env (e.g. anthropic/claude-sonnet-4-6, "
            "gemini/gemini-1.5-flash, ollama/llama3)"
        )

    raise AssertionError(
        f"\nNo pattern matched: \"{step_text}\"\n"
        f"  Normalized to:      \"{normalized}\"\n"
        "  → Add a pattern to noodle/resolver/patterns.py\n"
        "  → OR set NOODLE_MODEL in .env to enable LLM fallback"
    )


def _llm_resolve(step_text: str) -> dict:
    try:
        from noodle.llm.client import ask
    except ImportError:
        raise AssertionError("LLM fallback requires: pip install noodle[llm]")

    prompt = f"""You are a test automation interpreter. Convert this test step to a JSON action.

Step: "{step_text}"

WEB action types: navigate, search, close_popups, click, fill, hover, press_key, clear, select, check, uncheck, assert_visible, assert_hidden, assert_url, assert_title, assert_value, assert_state, assert_attribute, assert_count, store_text, set_var, store_attribute, assert_compare, scroll, screenshot, wait_load, wait_visible, wait_hidden

WEB param keys by type: navigate -> url; search -> query; click/hover/clear -> locator; fill -> locator,value; press_key -> key; select -> locator,value; check/uncheck -> locator; assert_visible/assert_hidden/wait_visible/wait_hidden -> text; assert_url/assert_title -> fragment; assert_value -> locator,value; assert_state -> locator,state; assert_attribute -> locator,attribute,value; assert_count -> count,locator; store_text -> locator,var; set_var -> var,value; store_attribute -> attribute,locator,var; assert_compare -> left,op,right; scroll -> direction; screenshot -> name

REST (HTTP API) action types and params:
  rest_set_header -> name,value
  rest_call -> method (GET/POST/PUT/PATCH/DELETE), path; optional body (JSON string), var (store response)
  rest_assert_status -> expected (integer)
  rest_assert_body -> needle (substring expected in body)
  rest_assert_header -> name,value
  rest_extract_json -> key,var (store a JSON field into a variable)

Rules:
- Use "path" (not "url") for rest_call. "expected" for rest_assert_status must be an integer.
- For REST steps with a Gherkin data table (step ends with ":"), do NOT use the LLM — those are pattern-only. Never emit a type ending in "_table".

Reply with JSON only.
Web example:  {{"type": "click", "locator": "Login"}}
REST example: {{"type": "rest_call", "method": "POST", "path": "/users", "body": "{{\\"name\\":\\"Alice\\"}}", "var": null}}
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
