import os
from .patterns import match as pattern_match, normalize_subject


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

Valid action types: navigate, click, fill, hover, press_key, clear, select, check, uncheck, assert_visible, assert_hidden, assert_url, assert_value, assert_state, assert_attribute, assert_count, store_text, scroll, screenshot, wait_load, wait_visible, wait_hidden

Param keys by type: click/hover/clear -> locator; fill -> locator,value; press_key -> key; assert_visible/assert_hidden/wait_visible/wait_hidden -> text; assert_value -> locator,value; assert_state -> locator,state; assert_attribute -> locator,attribute,value; assert_count -> count,locator; store_text -> locator,var; set_var -> var,value; store_attribute -> attribute,locator,var; assert_compare -> left,op,right

Reply with JSON only, example: {{"type": "click", "locator": "Login"}}
"""
    import json
    raw = ask(prompt)
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        raise AssertionError(
            f"LLM returned unparseable response for: \"{step_text}\"\nResponse: {raw}"
        )
