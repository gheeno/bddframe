import os
from collections import defaultdict
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from noodle.log import logger
from noodle import healing
from noodle.reporting import paths as _paths
from noodle.agents.web import pom as pom_module
from noodle.agents.web import locator as locator_module

_VALID_BROWSERS = {"chromium", "firefox", "webkit"}

# --- Custom hook registry ---
# Valid events mirror behave's lifecycle names.
_VALID_EVENTS = frozenset({
    "before_all", "before_feature", "before_scenario",
    "after_step", "after_scenario", "after_all",
})
_registry: dict[str, list] = defaultdict(list)


def register(event: str, fn):
    """Register a callable for a lifecycle event.

    Note: before_all hooks must be registered in environment.py (step files
    are loaded after before_all fires and would miss it).
    """
    if event not in _VALID_EVENTS:
        raise ValueError(f"Unknown hook event {event!r}. Valid: {sorted(_VALID_EVENTS)}")
    _registry[event].append(fn)


def hook(event: str):
    """Decorator — @hook('before_scenario') def my_hook(context, scenario): ..."""
    def decorator(fn):
        register(event, fn)
        return fn
    return decorator


def _run_hooks(event: str, *args):
    for fn in _registry[event]:
        fn(*args)

try:
    from noodle.reporting import writer as _writer
    from noodle.reporting import junit as _junit
    from noodle.reporting import builder as _builder
    from noodle.reporting import annotate as _annotate
    _REPORTING = True
except ImportError:
    _REPORTING = False

# Accumulated scenario results for JUnit XML, populated in after_scenario.
_suite_results = []


def _load_environments():
    """Load base URLs from environments.yaml into os.environ (uppercased).
    Real env vars / .env win, so CI can override without editing the file.

    Load order (first-write wins via setdefault):
      1. <cwd>/environments.yaml                      — project-wide defaults
      2. features/**/environment/environments.yaml    — per-app overrides
    App files add keys; they cannot override root or real env vars."""
    import yaml

    def _apply(path: Path):
        if not path.exists():
            return
        data = yaml.safe_load(path.read_text()) or {}
        for key, value in data.items():
            os.environ.setdefault(key.upper(), str(value))

    _apply(Path.cwd() / "environments.yaml")
    for suite_env in sorted(Path.cwd().glob("features/**/environment/environments.yaml")):
        _apply(suite_env)


# Package dirs whose environment/.env + secrets.env have already been loaded
# this run — before_feature fires once per .feature file, but many files
# share one package dir, so re-loading would just be wasted parses.
_loaded_package_dirs: set[str] = set()


def _load_package_env(feature_dir: Path):
    """Load <feature_dir>/environment/.env + secrets.env — the per-app
    equivalent of the root loads in before_all. Same load_dotenv() semantics
    (set a key only if not already in os.environ), so root config/secrets
    still win over package-level ones on a key collision."""
    key = str(feature_dir)
    if key in _loaded_package_dirs:
        return
    _loaded_package_dirs.add(key)
    env_dir = feature_dir / "environment"
    load_dotenv(env_dir / ".env")
    load_dotenv(env_dir / "secrets.env")


def before_all(context):
    load_dotenv()                          # config (committed)
    load_dotenv("secrets.env")             # secrets (gitignored) — soon AKV
    _load_environments()
    _loaded_package_dirs.clear()
    _suite_results.clear()
    if os.getenv("NOODLE_PARALLEL_WORKER") == "1":
        # Each behavex worker is its own process — give it a private results
        # subdir so workers don't wipe/overwrite each other's files. The CLI
        # cleans the shared parent once, before spawning the workers.
        os.environ["NOODLE_RESULTS_DIR"] = f"allure-results/p{os.getpid()}"
    else:
        _clean_allure_results()
    healing.reset()
    _load_keyvault()
    _run_hooks("before_all", context)


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
    feature_dir = Path(feature.filename).parent
    # Tell POM loader which folder to look in for local pom.yaml
    pom_module.set_context(str(feature_dir))
    _load_package_env(feature_dir)

    # Flaky-test retry: re-run a failed scenario up to NOODLE_RETRIES extra
    # times (default 1). Retries fire ONLY on failure, so green scenarios cost
    # nothing. @no_retry opts a scenario out (e.g. a known-failing assertion).
    retries = int(os.getenv("NOODLE_RETRIES", "1"))
    if retries > 0:
        from behave.contrib.scenario_autoretry import patch_scenario_with_autoretry
        for scenario in feature.scenarios:
            if 'no_retry' not in scenario.effective_tags:
                patch_scenario_with_autoretry(scenario, max_attempts=retries + 1)
    _run_hooks("before_feature", context, feature)


def _ocr_available():
    """True when pytesseract + the tesseract binary are usable. Cached."""
    global _OCR_OK
    if _OCR_OK is None:
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            _OCR_OK = True
        except Exception:
            _OCR_OK = False
    return _OCR_OK


_OCR_OK = None


def before_scenario(context, scenario):
    tags = set(scenario.effective_tags)

    # @live scenarios hit a real external site — opt-in only, so CI and casual
    # runs never make surprise network calls. Set NOODLE_RUN_LIVE=1 to run.
    if 'live' in tags and os.getenv("NOODLE_RUN_LIVE", "").lower() not in ("1", "true", "yes"):
        scenario.skip("@live is opt-in — set NOODLE_RUN_LIVE=1 to run real-site tests")
        return

    # @terminal scenarios need the OCR engine — skip (not fail) where tesseract
    # isn't installed, so a suite stays green on a box without the [visual] extra.
    if 'terminal' in tags and not _ocr_available():
        scenario.skip("OCR engine (tesseract) not installed — pip install noodle[visual]")
        return

    # Per-scenario locator/POM state — reset so tags/pins don't leak between scenarios.
    locator_module.set_strict('strict' in tags or None)
    locator_module.set_frame(None)        # 11.2 — clear any iframe scope
    pom_module.set_active_page(None)
    from noodle.agents.web import screen as _screen
    _screen.set_region(None)              # 0024 — clear any OCR focus region
    context._vars = {}                     # 11.1 — run-scoped stored values
    context._scenario_failed = False       # set by after_step; gates trace save

    # Bug 3: warn when @headed and @headless both appear — @headed wins but conflict
    # is almost always a forgotten debug tag that will break CI silently.
    if 'headed' in tags and 'headless' in tags:
        logger.warning(
            f"\n  [noodle] WARNING: scenario '{scenario.name}' has both @headed and "
            f"@headless — @headed wins. Remove one tag to suppress this warning."
        )

    if 'headed' in tags:
        headless = False
    elif 'headless' in tags:
        headless = True
    else:
        headless = os.getenv("NOODLE_HEADLESS", "false").lower() == "true"

    slow_mo = 500 if 'slow' in tags else 0

    # Bug 4: validate browser name before passing to getattr(playwright, name)
    if 'firefox' in tags:
        browser_name = 'firefox'
    elif 'webkit' in tags:
        browser_name = 'webkit'
    else:
        browser_name = os.getenv("NOODLE_BROWSER", "chromium")

    if browser_name not in _VALID_BROWSERS:
        raise ValueError(
            f"Unsupported browser '{browser_name}'. "
            f"Valid options: {', '.join(sorted(_VALID_BROWSERS))}"
        )

    timeout = int(os.getenv("NOODLE_TIMEOUT", "10000"))

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
    from noodle import preconditions
    preconditions.run(scenario, "setup")
    _run_hooks("before_scenario", context, scenario)


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
    _run_hooks("after_step", context, step)
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

        # Agentic RCA (opt-in: NOODLE_RCA + NOODLE_MODEL). Classify the
        # failure's root cause from the screenshot and tag the Allure result so
        # the report can be filtered by category. Best-effort, never raises.
        from noodle import rca
        verdict = rca.review(step.name, step.error_message, raw_path)
        if verdict is not None and ar is not None:
            ar.result["labels"].append(
                {"name": "rca_category", "value": verdict["label"]}
            )
    else:
        ar = _allure_result(context)
        if ar is not None:
            ar.add_step(step, "passed")


def after_scenario(context, scenario):
    # User after_scenario hooks run first — context.page is still alive here.
    _run_hooks("after_scenario", context, scenario)

    # Teardown first, so it always runs even if the scenario failed (the point of
    # teardown). Failures here are logged, not raised — see preconditions.run.
    from noodle import preconditions
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
    _run_hooks("after_all", context)
    parallel = os.getenv("NOODLE_PARALLEL_WORKER") == "1"
    rdir = _paths.results_dir()
    # In parallel mode keep every output inside the worker's own dir and skip
    # the report build — the CLI merges all worker dirs into one report once.
    healing.write_report(str(rdir / "healing-report.txt") if parallel else "healing-report.txt")
    if _REPORTING and _suite_results:
        _junit.write_junit(_suite_results, str(rdir / "junit.xml"))
        if not parallel:
            _builder.generate()


def _load_keyvault():
    """Load secrets from Azure Key Vault when NOODLE_KEYVAULT_URL is set
    (managed identity / az login in CI). No URL → no-op, .env is used. Fetched
    secrets override env so the vault is the source of truth when configured."""
    url = os.getenv("NOODLE_KEYVAULT_URL")
    # Azure leaves "$(VAR)" literal when the variable is undefined — treat that
    # (and empty) as "no vault configured".
    if not url or url.startswith("$("):
        return
    try:
        from noodle.secrets_akv import load_into_environ
    except ImportError as e:
        raise RuntimeError(
            "NOODLE_KEYVAULT_URL is set but the Azure SDK is missing — "
            "install with: pip install noodle[azure]"
        ) from e
    count = load_into_environ(url)
    logger.info(f"\n  🔑 Loaded {count} secret(s) from Key Vault")
