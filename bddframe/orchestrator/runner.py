import os
import re
from bddframe.resolver.step_resolver import resolve
from bddframe.agents.web import actions


def substitute(text: str, extra: dict | None = None) -> str:
    """Replace [variable name] with a run-stored value (11.1) or env var."""
    extra = extra or {}
    def lookup(m):
        key = m.group(1).upper().replace(" ", "_")
        if key in extra:
            return extra[key]
        return os.getenv(key, m.group(0))
    return re.sub(r'\[([^\]]+)\]', lookup, text)


def execute_step(step_text: str, context):
    if getattr(context, "_vars", None) is None:
        context._vars = {}
    step_text = substitute(step_text, context._vars)
    action = resolve(step_text)
    page = context.page

    t = action['type']

    if t == 'set_page':
        actions.set_page(action['name'])
    elif t == 'navigate':
        actions.navigate(page, action['url'])
    elif t == 'click':
        actions.click(page, action['locator'])
    elif t == 'fill':
        actions.fill(page, action['locator'], action['value'])
    elif t == 'clear':
        actions.clear(page, action['locator'])
    elif t == 'select':
        actions.select_option(page, action['locator'], action['value'])
    elif t == 'check':
        actions.check(page, action['locator'])
    elif t == 'uncheck':
        actions.uncheck(page, action['locator'])
    elif t == 'assert_visible':
        actions.assert_visible(page, action['text'])
    elif t == 'assert_hidden':
        actions.assert_hidden(page, action['text'])
    elif t == 'assert_url':
        actions.assert_url(page, action['fragment'])
    elif t == 'wait_load':
        actions.wait_load(page)
    elif t == 'wait_networkidle':
        actions.wait_networkidle(page)
    elif t == 'wait_visible':
        actions.wait_visible(page, action['text'])
    elif t == 'wait_seconds':
        actions.wait_seconds(action['seconds'])
    elif t == 'scroll':
        actions.scroll(page, action['direction'])
    elif t == 'scroll_to':
        actions.scroll_to(page, action['locator'])
    elif t == 'assert_title':
        actions.assert_title(page, action['fragment'])
    elif t == 'assert_semantic':
        actions.assert_semantic(page, action['assertion'])
    elif t == 'visual_baseline':
        actions.visual_baseline(page, action['name'], action.get('ignore'))
    elif t == 'screenshot':
        actions.screenshot(page, action['name'])
    # --- Phase 11 ---
    elif t == 'press_key':
        actions.press_key(page, action['key'])
    elif t == 'hover':
        actions.hover(page, action['locator'])
    elif t == 'wait_hidden':
        actions.wait_hidden(page, action['text'])
    elif t == 'assert_value':
        actions.assert_value(page, action['locator'], action['value'])
    elif t == 'assert_state':
        actions.assert_state(page, action['locator'], action['state'])
    elif t == 'assert_attribute':
        actions.assert_attribute(page, action['locator'], action['attribute'], action['value'])
    elif t == 'assert_count':
        actions.assert_count(page, action['count'], action['locator'])
    elif t == 'store_text':
        key = action['var'].upper().replace(" ", "_")
        context._vars[key] = actions.get_text(page, action['locator'])
        print(f"\n  💾 Stored [{key}] = {context._vars[key]!r}")
    elif t == 'click_in_row':
        actions.click_in_row(page, action['locator'], action['row'])
    elif t == 'click_in_section':
        actions.click_in_section(page, action['locator'], action['section'])
    elif t == 'assert_cell':
        actions.assert_cell(page, action['row'], action['column'], action['expected'])
    elif t == 'assert_row_count':
        actions.assert_row_count(page, action['count'])
    elif t == 'switch_frame':
        actions.switch_frame(page, action['name'])
    else:
        raise AssertionError(f"Unknown action type: '{t}'")
