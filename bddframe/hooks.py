import os
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from bddframe.agents.web import pom as pom_module


def before_all(context):
    load_dotenv()


def before_feature(context, feature):
    # Tell POM loader which folder to look in for local pom.yaml
    pom_module.set_context(str(Path(feature.filename).parent))


def before_scenario(context, scenario):
    tags = set(scenario.effective_tags)

    headless = 'headless' in tags or os.getenv("BDDFRAME_HEADLESS", "false").lower() == "true"
    slow_mo  = 500 if 'slow' in tags else 0

    if 'firefox' in tags:
        browser_name = 'firefox'
    elif 'webkit' in tags:
        browser_name = 'webkit'
    else:
        browser_name = os.getenv("BDDFRAME_BROWSER", "chromium")

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
    context.page  = context._bctx.new_page()
    context.page.set_default_timeout(timeout)


def after_step(context, step):
    if step.status == "failed":
        os.makedirs("screenshots", exist_ok=True)
        safe_name = step.name.replace(" ", "_").replace("/", "_")[:80]
        path = f"screenshots/FAILED_{safe_name}.png"
        try:
            context.page.screenshot(path=path, full_page=True)
            print(f"\n  📸 Screenshot saved: {path}")
        except Exception:
            pass


def after_scenario(context, scenario):
    try:
        context._bctx.close()
        context._browser.close()
        context._pw.stop()
    except Exception:
        pass
