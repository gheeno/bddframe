import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright


def before_all(context):
    load_dotenv()


def before_scenario(context, scenario):
    headless = os.getenv("BDDFRAME_HEADLESS", "false").lower() == "true"
    browser_name = os.getenv("BDDFRAME_BROWSER", "chromium")
    timeout = int(os.getenv("BDDFRAME_TIMEOUT", "10000"))

    context._pw = sync_playwright().start()
    browser_type = getattr(context._pw, browser_name)
    context._browser = browser_type.launch(headless=headless)
    context.page = context._browser.new_page()
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
        context._browser.close()
        context._pw.stop()
    except Exception:
        pass
