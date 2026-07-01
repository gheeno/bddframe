import json
import os
import re
from noodle.log import logger
from noodle.resolver.step_resolver import resolve
from noodle.agents.web import actions
from noodle.orchestrator import script_runner


def _store_script_output(context, out: str, var: str | None):
    """Stash a script's stdout in `SCRIPT_OUTPUT` (always) and an optional named
    var, so a later step can assert on it (e.g. `SCRIPT_OUTPUT` should contain …)."""
    context._vars['SCRIPT_OUTPUT'] = out
    if var:
        context._vars[var.upper().replace(" ", "_")] = out


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


def _pages(context):
    """Every open page in the scenario's browser context (newest last)."""
    bctx = getattr(context, "_bctx", None)
    return list(bctx.pages) if bctx is not None else [context.page]


def _focus(context, page):
    """Make `page` the active page. Popup tabs don't inherit the scenario's
    default timeout, so re-apply it here or assertions on a new tab wait 30s."""
    context.page = page
    to = getattr(page, "set_default_timeout", None)
    if to is not None:
        to(int(os.getenv("NOODLE_TIMEOUT", "10000")))
    front = getattr(page, "bring_to_front", None)
    if front is not None:
        front()


def _switch_tab(context, target, assert_opened=False):
    """Point context.page at another open tab. ponytail: previous/first/main all
    mean pages[0] — a real back-stack only matters past 2 tabs, add then."""
    if assert_opened:
        page = context.page
        timeout_ms = int(os.getenv("NOODLE_TIMEOUT", "10000"))
        from playwright._impl._errors import TimeoutError as _PWTimeout
        try:
            # wait_for_event("popup") retrieves the queued popup event even if
            # the click already fired — no need to wrap the click.
            new_page = page.wait_for_event("popup", timeout=timeout_ms)
            _focus(context, new_page)
            return
        except _PWTimeout:
            raise AssertionError("Expected a new tab to open, but only one tab is open")
    pages = _pages(context)
    _focus(context, pages[-1] if target in ('new', 'last') else pages[0])


def _close_tab(context):
    if len(_pages(context)) > 1:
        context.page.close()
        _focus(context, _pages(context)[0])


def execute_step(step_text: str, context):
    if getattr(context, "_vars", None) is None:
        context._vars = {}
    step_text = substitute(step_text, context._vars)
    # "... in the new tab" (BFRAME_0025) — run the rest of the step against the
    # newest page, then drop the suffix so the inner verb resolves normally.
    m = re.search(r'\s+in the (?:new|last) (?:tab|window)$', step_text, re.IGNORECASE)
    if m:
        pages = _pages(context)
        if len(pages) > 1:
            _focus(context, pages[-1])
        step_text = step_text[:m.start()]
    action = resolve(step_text)
    page = context.page

    t = action['type']

    if t == 'set_page':
        actions.set_page(action['name'])
    elif t == 'navigate':
        actions.navigate(page, action['url'])
    elif t == 'click':
        actions.click(page, action['locator'])
    # --- BFRAME_0025: history, extra clicks, form submit, tab/window ----------
    elif t == 'go_back':
        actions.go_back(page)
    elif t == 'go_forward':
        actions.go_forward(page)
    elif t == 'reload':
        actions.reload(page)
    elif t == 'double_click':
        actions.double_click(page, action['locator'])
    elif t == 'right_click':
        actions.right_click(page, action['locator'])
    elif t == 'submit':
        actions.submit(page, action['locator'])
    elif t == 'assert_new_tab':
        _switch_tab(context, 'new', assert_opened=True)
    elif t == 'switch_tab':
        _switch_tab(context, action['target'])
    elif t == 'close_tab':
        _close_tab(context)
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
    elif t == 'pixel_baseline':
        actions.pixel_baseline(page, action['name'])
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
        logger.info(f"\n  💾 Stored `{key}` = {context._vars[key]!r}")
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
        logger.info(f"\n  💾 Set `{key}` = {context._vars[key]!r}")
    elif t == 'store_attribute':
        key = action['var'].upper().replace(" ", "_")
        context._vars[key] = actions.get_attribute_value(page, action['locator'], action['attribute'])
        logger.info(f"\n  💾 Stored `{key}` = {context._vars[key]!r}")
    elif t == 'assert_compare':
        actions.assert_compare(action['left'], action['op'], action['right'])
    # --- Phase D ---
    elif t == 'mock_route':
        actions.mock_route(page, action['url'], action['status'], action.get('body'))
    elif t == 'block_route':
        actions.block_route(page, action['url'])
    elif t == 'api_call':
        actions.api_call(page, action['method'], action['url'], action.get('body'))
    elif t == 'load_data':
        context._vars.update(actions.load_data(action['file']))
        logger.info(f"\n  📦 Loaded test data from {action['file']}")
    elif t == 'load_resource':
        feature_dir = os.path.dirname(os.path.abspath(context.feature.filename))
        paths = [action['path']] if action['path'] else [row['payload'] for row in context.table]
        for rel in paths:
            full = os.path.join(feature_dir, 'resources', rel)
            with open(full) as fh:
                content = fh.read()
            # Compact JSON so substituted values stay single-line for regex patterns.
            try:
                content = json.dumps(json.loads(content))
            except (json.JSONDecodeError, ValueError):
                content = content.strip()
            stem = os.path.splitext(os.path.basename(rel))[0].upper().replace('-', '_').replace(' ', '_')
            context._vars[f'PAYLOAD_{stem}'] = content
            context._vars['PAYLOAD'] = content  # ponytail: last-loaded wins; named vars cover multi-file use
            logger.info(f"\n  📄 Loaded resource {rel}")
    # --- BFRAME_0016: run an external script / command -----------------------
    elif t == 'run_script':
        out = script_runner.run_script(action['path'], action.get('args'))
        _store_script_output(context, out, action.get('var'))
        logger.info(f"\n  🛠  Ran script {action['path']} → {out!r}")
    elif t == 'run_command':
        out = script_runner.run_command(action['command'])
        _store_script_output(context, out, action.get('var'))
        logger.info(f"\n  🛠  Ran command {action['command']!r} → {out!r}")
    # --- BFRAME_0024: web pixel/OCR bridge (canvas & terminal UIs) -----------
    elif t in ('type_text', 'click_at', 'click_text', 'assert_screen_text',
               'assert_screen_text_hidden', 'wait_screen_text', 'assert_buffer',
               'focus_region'):
        from noodle.agents.web import screen
        if t == 'type_text':
            screen.type_text(page, action['text'])
        elif t == 'click_at':
            screen.click_at(page, action['x'], action['y'])
        elif t == 'click_text':
            screen.click_text(page, action['text'])
        elif t == 'assert_screen_text':
            screen.assert_text_visible(page, action['text'])
        elif t == 'assert_screen_text_hidden':
            screen.assert_text_hidden(page, action['text'])
        elif t == 'wait_screen_text':
            screen.wait_text_visible(page, action['text'])
        elif t == 'assert_buffer':
            screen.assert_buffer_contains(page, action['text'])
        elif t == 'focus_region':
            from noodle.agents.visual import regions
            vp = page.viewport_size or {"width": 1280, "height": 720}
            screen.set_region(regions.parse_region(action['region'], (vp["width"], vp["height"])))
    # --- BFRAME_0029: proper REST HTTP client ------------------------------------
    elif t == 'rest_set_header':
        hdrs = json.loads(context._vars.get('_REST_HEADERS', '{}'))
        hdrs[action['name']] = action['value']
        context._vars['_REST_HEADERS'] = json.dumps(hdrs)
    elif t == 'rest_call':
        from noodle.agents.web import rest_client
        base = context._vars.get('REST_BASE_URL', '')
        hdrs = json.loads(context._vars.get('_REST_HEADERS', '{}'))
        path = action['path']
        url = path if path.startswith('http') else base.rstrip('/') + '/' + path.lstrip('/')
        status, body, headers = rest_client.rest_call(action['method'], url, action.get('body'), hdrs)
        context._vars['REST_STATUS'] = str(status)
        context._vars['REST_BODY'] = body
        context._vars['REST_HEADERS'] = json.dumps(dict(headers))
        if action.get('var'):
            context._vars[action['var'].upper().replace(' ', '_')] = body
        logger.info(f"\n  🌐 {action['method']} {url} → {status}")
    elif t == 'rest_assert_status':
        actual = int(context._vars.get('REST_STATUS', 0))
        assert actual == action['expected'], f"Expected status {action['expected']}, got {actual}"
    elif t == 'rest_extract_json':
        body = context._vars.get('REST_BODY', '{}')
        try:
            data = json.loads(body)
        except ValueError as exc:
            raise AssertionError(f"REST_BODY is not valid JSON: {body[:100]}") from exc
        key = action['key']
        item = data[0] if isinstance(data, list) else data
        if key not in item:
            raise AssertionError(f"Key '{key}' not found in response JSON")
        target = action['var'].upper().replace(' ', '_')
        context._vars[target] = str(item[key])
        logger.info(f"\n  💾 Extracted '{key}' → `{target}` = {context._vars[target]!r}")
    elif t == 'rest_assert_body':
        body = context._vars.get('REST_BODY', '')
        assert action['needle'] in body, f"Response body does not contain '{action['needle']}'"
    elif t == 'rest_assert_body_table':
        body = context._vars.get('REST_BODY', '')
        for row in context.table:
            key, value = row['Key'], row.get('Value', '').strip()
            assert key in body, f"Response body does not contain key '{key}'"
            if value:
                assert value in body, f"Response body does not contain value '{value}' for key '{key}'"
    elif t == 'rest_assert_header':
        headers = json.loads(context._vars.get('REST_HEADERS', '{}'))
        actual = next((v for k, v in headers.items() if k.lower() == action['name'].lower()), None)
        assert actual is not None, f"Response header '{action['name']}' not found"
        assert action['value'].lower() in actual.lower(), \
            f"Header '{action['name']}': expected '{action['value']}', got '{actual}'"
    elif t == 'rest_assert_header_table':
        headers = json.loads(context._vars.get('REST_HEADERS', '{}'))
        for row in context.table:
            name, expected = row['Header'], row.get('Value', '').strip()
            actual = next((v for k, v in headers.items() if k.lower() == name.lower()), None)
            assert actual is not None, f"Response header '{name}' not found"
            if expected:
                assert expected.lower() in actual.lower(), \
                    f"Header '{name}': expected '{expected}', got '{actual}'"
    else:
        raise AssertionError(f"Unknown action type: '{t}'")
