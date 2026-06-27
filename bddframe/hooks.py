import os
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from bddframe.agents.web import pom as pom_module
from bddframe.agents.web import locator as locator_module

_VALID_BROWSERS = {"chromium", "firefox", "webkit"}

try:
    from bddframe.reporting import writer as _writer
    from bddframe.reporting import junit as _junit
    from bddframe.reporting import builder as _builder
    from bddframe.reporting import annotate as _annotate
    _REPORTING = True
except ImportError:
    _REPORTING = False

# Accumulated scenario results for JUnit XML, populated in after_scenario.
_suite_results = []


def before_all(context):
    load_dotenv()
    _suite_results.clear()


def before_feature(context, feature):
    # Tell POM loader which folder to look in for local pom.yaml
    pom_module.set_context(str(Path(feature.filename).parent))


def before_scenario(context, scenario):
    tags = set(scenario.effective_tags)

    # Per-scenario locator/POM state — reset so tags/pins don't leak between scenarios.
    locator_module.set_strict('strict' in tags or None)
    pom_module.set_active_page(None)

    # Bug 3: warn when @headed and @headless both appear — @headed wins but conflict
    # is almost always a forgotten debug tag that will break CI silently.
    if 'headed' in tags and 'headless' in tags:
        print(
            f"\n  [bddframe] WARNING: scenario '{scenario.name}' has both @headed and "
            f"@headless — @headed wins. Remove one tag to suppress this warning."
        )

    if 'headed' in tags:
        headless = False
    elif 'headless' in tags:
        headless = True
    else:
        headless = os.getenv("BDDFRAME_HEADLESS", "false").lower() == "true"

    slow_mo = 500 if 'slow' in tags else 0

    # Bug 4: validate browser name before passing to getattr(playwright, name)
    if 'firefox' in tags:
        browser_name = 'firefox'
    elif 'webkit' in tags:
        browser_name = 'webkit'
    else:
        browser_name = os.getenv("BDDFRAME_BROWSER", "chromium")

    if browser_name not in _VALID_BROWSERS:
        raise ValueError(
            f"Unsupported browser '{browser_name}'. "
            f"Valid options: {', '.join(sorted(_VALID_BROWSERS))}"
        )

    timeout = int(os.getenv("BDDFRAME_TIMEOUT", "10000"))

    context._pw = sync_playwright().start()
    browser_type = getattr(context._pw, browser_name)
    context._browser = browser_type.launch(headless=headless, slow_mo=slow_mo)

    ctx_opts = {}
    if 'mobile' in tags:
        device_name = "iPhone 13" if 'iphone' in tags else "Pixel 5"
        ctx_opts.update(context._pw.devices[device_name])
    if 'record_video' in tags:
        os.makedirs("videos", exist_ok=True)
        ctx_opts['record_video_dir'] = "videos/"

    context._bctx = context._browser.new_context(**ctx_opts)
    context.page = context._bctx.new_page()
    context.page.set_default_timeout(timeout)

    if _REPORTING:
        context._allure_result = _writer.ScenarioResult(scenario)


def _allure_result(context):
    """Return context._allure_result only when it's a real ScenarioResult instance."""
    if not _REPORTING:
        return None
    result = getattr(context, "_allure_result", None)
    if result is None:
        return None
    # Guard against MagicMock contexts in tests — only accept real ScenarioResult objects.
    if not isinstance(result, _writer.ScenarioResult):
        return None
    return result


def after_step(context, step):
    if step.status == "failed":
        os.makedirs("screenshots", exist_ok=True)
        safe_name = step.name.replace(" ", "_").replace("/", "_")[:80]
        raw_path = f"screenshots/FAILED_{safe_name}.png"
        annotated_path = None
        try:
            context.page.screenshot(path=raw_path, full_page=True)
            print(f"\n  📸 Screenshot saved: {raw_path}")
            ar = _allure_result(context)
            if ar is not None:
                annotated_path = _annotate.draw_not_found(raw_path, step.name[:60])
        except Exception:
            pass
        ar = _allure_result(context)
        if ar is not None:
            ar.add_step(step, "failed", annotated_path or raw_path)
    else:
        ar = _allure_result(context)
        if ar is not None:
            ar.add_step(step, "passed")


def after_scenario(context, scenario):
    ar = _allure_result(context)
    if ar is not None:
        ar.finish(scenario)
        _writer.write_result(ar)
        _suite_results.append(ar)

    # Bug 6: clean up each resource independently so a failure on one
    # (e.g. _bctx never created) does not skip stopping _pw and leak
    # an orphaned browser process.
    for attr, method in [
        ("_bctx",    lambda r: r.close()),
        ("_browser", lambda r: r.close()),
        ("_pw",      lambda r: r.stop()),
    ]:
        resource = getattr(context, attr, None)
        if resource is not None:
            try:
                method(resource)
            except Exception:
                pass


def after_all(context):
    if _REPORTING and _suite_results:
        _junit.write_junit(_suite_results)
        _builder.generate()
