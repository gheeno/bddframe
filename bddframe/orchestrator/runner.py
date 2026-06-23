import os
import re
from bddframe.resolver.step_resolver import resolve
from bddframe.agents.web import actions


def substitute(text: str) -> str:
    """Replace [variable name] with the matching env var value."""
    def lookup(m):
        key = m.group(1).upper().replace(" ", "_")
        return os.getenv(key, m.group(0))
    return re.sub(r'\[([^\]]+)\]', lookup, text)


def execute_step(step_text: str, context):
    step_text = substitute(step_text)
    action = resolve(step_text)
    page = context.page

    t = action['type']

    if t == 'navigate':
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
    elif t == 'wait_visible':
        actions.wait_visible(page, action['text'])
    elif t == 'wait_seconds':
        actions.wait_seconds(action['seconds'])
    elif t == 'scroll':
        actions.scroll(page, action['direction'])
    elif t == 'scroll_to':
        actions.scroll_to(page, action['locator'])
    elif t == 'screenshot':
        actions.screenshot(page, action['name'])
    else:
        raise AssertionError(f"Unknown action type: '{t}'")
