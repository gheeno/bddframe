import os
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from bddframe.log import logger
from bddframe import healing
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


def _load_environments():
    """Load base URLs from environments.yaml into os.environ (uppercased).
    Real env vars / .env win, so CI can override without editing the file."""
    path = Path.cwd() / "environments.yaml"
    if not path.exists():
        return
    import yaml
    data = yaml.safe_load(path.read_text()) or {}
    for key, value in data.items():
        os.environ.setdefault(key.upper(), str(value))


def before_all(context):
    load_dotenv()                          # config (committed)
    load_dotenv("secrets.env")             # secrets (gitignored) — soon AKV
    _load_environments()
    _suite_results.clear()
    _clean_allure_results()
    healing.reset()
    _load_keyvault()


def _clean_allure_results():
    """Delete stale per-scenario JSON + junit from a previous run so the report
    and the quarantine exit-code scan (cli.py) only reflect THIS run. Keeps the
    dir itself and allure-report/history (trend data lives there)."""
    results = Path("allure-results")
    if not results.is_dir():
        return
    for f in results.glob("*-result.json"):
        f.unlink(missing_ok=True)
    (results / "junit.xml").unlink(missing_ok=True)


def before_feature(context, feature):
    # Tell POM loader which folder to look in for local pom.yaml
    pom_module.set_context(str(Path(feature.filename).parent))

    # Flaky-test retry: re-run a failed scenario up to BDDFRAME_RETRIES extra
    # times (default 1). Retries fire ONLY on failure, so green scenarios cost
    # nothing. @no_retry opts a scenario out (e.g. a known-failing assertion).
    retries = int(os.getenv("BDDFRAME_RETRIES", "1"))
    if retries > 0:
        from behave.contrib.scenario_autoretry import patch_scenario_with_autoretry
        for scenario in feature.scenarios:
            if 'no_retry' not in scenario.effective_tags:
                patch_scenario_with_autoretry(scenario, max_attempts=retries + 1)


def before_scenario(context, scenario):
    tags = set(scenario.effective_tags)

    # Per-scenario locator/POM state — reset so tags/pins don't leak between scenarios.
    locator_module.set_strict('strict' in tags or None)
    locator_module.set_frame(None)        # 11.2 — clear any iframe scope
    pom_module.set_active_page(None)
    context._vars = {}                     # 11.1 — run-scoped stored values
    context._scenario_failed = False       # set by after_step; gates trace save

    # Bug 3: warn when @headed and @headless both appear — @headed wins but conflict
    # is almost always a forgotten debug tag that will break CI silently.
    if 'headed' in tags and 'headless' in tags:
        logger.warning(
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

    # Playwright tracing — DOM snapshots + network + sources. Started for every
    # scenario, but only SAVED on failure (after_scenario); discarded on pass so
    # green runs cost no disk. The trace viewer is the headline debugging edge
    # over Selenium/Selenide. ponytail: always-on capture, save-on-fail; the only
    # cheaper option (start-on-retry) needs a retry loop we don't have yet.
    try:
        context._bctx.tracing.start(screenshots=True, snapshots=True, sources=True)
        context._tracing = True
    except Exception:
        context._tracing = False

    context.page = context._bctx.new_page()
    context.page.set_default_timeout(timeout)

    if _REPORTING:
        context._allure_result = _writer.ScenarioResult(scenario)

    # Data preconditions — seed BusterBlock state via @precondition:NAME before the
    # UI test runs (the JDBC-fixture analog). Setup failures abort the scenario.
    from bddframe import preconditions
    preconditions.run(scenario, "setup")


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
        context._scenario_failed = True
        os.makedirs("screenshots", exist_ok=True)
        safe_name = step.name.replace(" ", "_").replace("/", "_")[:80]
        raw_path = f"screenshots/FAILED_{safe_name}.png"
        annotated_path = None
        try:
            context.page.screenshot(path=raw_path, full_page=True)
            logger.info(f"\n  📸 Screenshot saved: {raw_path}")
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
    # Teardown first, so it always runs even if the scenario failed (the point of
    # teardown). Failures here are logged, not raised — see preconditions.run.
    from bddframe import preconditions
    preconditions.run(scenario, "teardown")

    ar = _allure_result(context)
    if ar is not None:
        ar.finish(scenario)
        _writer.write_result(ar)
        _suite_results.append(ar)

    # Stop tracing BEFORE closing the context (tracing.stop needs it alive).
    # Save the zip only when the scenario failed; otherwise discard.
    if getattr(context, "_tracing", False):
        bctx = getattr(context, "_bctx", None)
        try:
            if context._scenario_failed and bctx is not None:
                os.makedirs("traces", exist_ok=True)
                safe_name = scenario.name.replace(" ", "_").replace("/", "_")[:80]
                trace_path = f"traces/{safe_name}.zip"
                bctx.tracing.stop(path=trace_path)
                logger.info(f"\n  🧭 Trace saved: {trace_path}"
                            f"\n     View it: playwright show-trace {trace_path}")
            elif bctx is not None:
                bctx.tracing.stop()       # passed — discard
        except Exception:
            pass

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
    healing.write_report()
    if _REPORTING and _suite_results:
        _junit.write_junit(_suite_results)
        _builder.generate()


def _load_keyvault():
    """Load secrets from Azure Key Vault when BDDFRAME_KEYVAULT_URL is set
    (managed identity / az login in CI). No URL → no-op, .env is used. Fetched
    secrets override env so the vault is the source of truth when configured."""
    url = os.getenv("BDDFRAME_KEYVAULT_URL")
    # Azure leaves "$(VAR)" literal when the variable is undefined — treat that
    # (and empty) as "no vault configured".
    if not url or url.startswith("$("):
        return
    try:
        from bddframe.secrets_akv import load_into_environ
    except ImportError as e:
        raise RuntimeError(
            "BDDFRAME_KEYVAULT_URL is set but the Azure SDK is missing — "
            "install with: pip install bddframe[azure]"
        ) from e
    count = load_into_environ(url)
    logger.info(f"\n  🔑 Loaded {count} secret(s) from Key Vault")
