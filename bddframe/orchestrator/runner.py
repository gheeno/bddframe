import os
import re
from bddframe.resolver.step_resolver import resolve
from bddframe.agents.web import actions


def substitute(text: str, extra: dict | None = None) -> str:
    """Expand variable references:

      `name`  → a value captured during this run (set/store) — NEVER .env.
      [name]  → a .env / config value (with captured-store fallback for
                backward compatibility).

    The two delimiters keep secrets (`[...]`) visually separate from values
    produced mid-scenario (backticks). Unknown refs are left untouched.
    """
    extra = extra or {}
    def _key(raw: str) -> str:
        return raw.upper().replace(" ", "_")

    def backtick(m):                       # captured values only
        return extra.get(_key(m.group(1)), m.group(0))
    text = re.sub(r'`([^`]+)`', backtick, text)

    def bracket(m):                        # .env / config (store fallback)
        key = _key(m.group(1))
        if key in extra:
            return extra[key]
        return os.getenv(key, m.group(0))
    return re.sub(r'\[([^\]]+)\]', bracket, text)


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
    elif t == 'search':
        actions.search(page, action['query'])
    elif t == 'close_popups':
        actions.close_popups(page)
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
        print(f"\n  💾 Stored `{key}` = {context._vars[key]!r}")
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
    # --- Phase 12 ---
    elif t == 'set_var':
        key = action['var'].upper().replace(" ", "_")
        context._vars[key] = action['value']
        print(f"\n  💾 Set `{key}` = {context._vars[key]!r}")
    elif t == 'store_attribute':
        key = action['var'].upper().replace(" ", "_")
        context._vars[key] = actions.get_attribute_value(page, action['locator'], action['attribute'])
        print(f"\n  💾 Stored `{key}` = {context._vars[key]!r}")
    elif t == 'assert_compare':
        actions.assert_compare(action['left'], action['op'], action['right'])
    else:
        raise AssertionError(f"Unknown action type: '{t}'")
