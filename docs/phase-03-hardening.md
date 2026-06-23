# Phase 3 — CLI & Hooks Hardening

**Goal**: Close the six correctness bugs found in the Phase 2 review before any new features are added. Every item here has a concrete failure scenario against real code.

---

## Explain like I'm 5

Phase 2 added a lot of new features — browser tags, video recording, mobile emulation, POM YAML. The review found places where the code works fine in the happy path but silently does the wrong thing in edge cases a real team will hit. This phase fixes all of them before they reach production.

---

## Bug 1 — Non-canonical `BDDFRAME_HEADLESS` passthrough

**File**: `bddframe/cli.py`

**Current code**:
```python
env["BDDFRAME_HEADLESS"] = "true" if headless else env.get("BDDFRAME_HEADLESS", "false")
```

**Problem**: When neither `--headless` nor `--headed` is passed, the env var is inherited verbatim from the parent environment. `hooks.py` accepts only the string `"true"` (`.lower() == "true"`), so any non-canonical truthy value (`1`, `yes`, `TRUE`, `on`) silently degrades to headed mode.

**Failure scenario**: CI sets `BDDFRAME_HEADLESS=1`. Developer runs `bddframe run features/` with no flags. `cli.py` propagates `"1"` to behave. `hooks.py` evaluates `"1".lower() == "true"` → `False`. Browser launches headed. Headless CI crashes or produces display errors with no diagnostic.

**Fix**:
```python
# Normalize to canonical "true"/"false" on every write — never pass env through raw.
if headed:
    env["BDDFRAME_HEADLESS"] = "false"
elif headless:
    env["BDDFRAME_HEADLESS"] = "true"
else:
    raw = env.get("BDDFRAME_HEADLESS", "false").strip().lower()
    env["BDDFRAME_HEADLESS"] = "true" if raw in ("1", "true", "yes", "on") else "false"
```

---

## Bug 2 — Silent winner when `--headed` and `--headless` are both passed

**File**: `bddframe/cli.py`

**Problem**: No guard against passing both flags simultaneously. `--headed` wins silently with no error or warning emitted.

**Failure scenario**: A CI template always appends `--headless`. A developer adds `--headed` to the same invocation for local debugging and forgets to remove it before pushing. The `headed=True` branch fires, the env var is set to `"false"`, and headed mode runs in headless CI. No error is raised.

**Fix**:
```python
if headed and headless:
    raise typer.BadParameter(
        "--headed and --headless are mutually exclusive. Pass one or neither.",
        param_hint="'--headed' / '--headless'",
    )
```

Added before the env assignment block.

---

## Bug 3 — `@headed` + `@headless` tag collision changes behavior silently

**File**: `bddframe/hooks.py`

**Current code**:
```python
if 'headed' in tags:
    headless = False
elif 'headless' in tags:
    headless = True
else:
    headless = os.getenv("BDDFRAME_HEADLESS", "false").lower() == "true"
```

**Problem**: `@headed` takes priority when both tags appear on a scenario. This is a breaking change vs. the pre-Phase-2 behavior where `@headed` did not exist. A scenario that inherited `@headless` from a Feature tag and later received `@headed` for a debugging session (and was never cleaned up) now silently switches to headed in CI.

**Fix**: Add a warning when both tags appear on the same scenario:
```python
if 'headed' in tags and 'headless' in tags:
    print(
        f"\n  [bddframe] WARNING: scenario '{scenario.name}' has both @headed and "
        f"@headless — @headed wins. Remove one tag to suppress this warning."
    )
```

The priority order (`@headed` > `@headless`) is intentional and correct. The fix is to surface the conflict rather than silently pick a winner.

---

## Bug 4 — `BDDFRAME_BROWSER` not validated before Playwright call

**File**: `bddframe/hooks.py`

**Current code**:
```python
browser_name = os.getenv("BDDFRAME_BROWSER", "chromium")
...
browser_type = getattr(context._pw, browser_name)
```

**Problem**: Any invalid value (e.g. `BDDFRAME_BROWSER=chrome`, `BDDFRAME_BROWSER=safari`) reaches `getattr(context._pw, browser_name)` and raises `AttributeError: 'SyncPlaywright' object has no attribute 'chrome'`. This is a cryptic traceback with no mention of valid browser names.

**Failure scenario**: Developer sets `BDDFRAME_BROWSER=chrome` in `.env` (Chrome vs Chromium is a common mistake). Every scenario in the suite aborts with a confusing `AttributeError` rather than a clear "unsupported browser" message.

**Fix**:
```python
VALID_BROWSERS = {"chromium", "firefox", "webkit"}
if browser_name not in VALID_BROWSERS:
    raise ValueError(
        f"Unsupported browser '{browser_name}'. "
        f"Valid options: {', '.join(sorted(VALID_BROWSERS))}"
    )
```

---

## Bug 5 — Hardcoded `features/` base directory breaks non-standard layouts

**File**: `bddframe/cli.py`

**Current code**:
```python
if path.endswith(".feature"):
    args = ["behave", "features/", "--include", Path(path).stem, "--no-capture"]
```

**Problem**: Behave is always rooted at `features/` regardless of where the passed `.feature` file actually lives. Projects that store features under `tests/`, `specs/`, or nested subdirectories silently run the wrong features — or run nothing and exit 0.

**Failure scenario**: Project keeps features under `tests/`. Developer runs `bddframe run tests/checkout.feature`. CLI constructs `["behave", "features/", "--include", "checkout", ...]`. Behave scans `features/` for `checkout` — which may not exist — and either skips silently (false green) or runs a different `checkout.feature` from the expected location.

**Fix**: Derive the behave base from the path that was passed, walking up to the parent that contains a `steps/` or `environment.py`:
```python
if path.endswith(".feature"):
    feature_path = Path(path).resolve()
    # Find the behave root: nearest ancestor that contains steps/ or environment.py
    base = feature_path.parent
    while base != base.parent:
        if (base / "steps").is_dir() or (base / "environment.py").exists():
            break
        base = base.parent
    else:
        base = Path("features")  # fallback if no marker found
    args = ["behave", str(base), "--include", feature_path.stem, "--no-capture"]
```

---

## Bug 6 — Bare `except Exception: pass` in `after_scenario` leaks Playwright processes

**File**: `bddframe/hooks.py`

**Current code**:
```python
def after_scenario(context, scenario):
    try:
        context._bctx.close()
        context._browser.close()
        context._pw.stop()
    except Exception:
        pass
```

**Problem**: The entire cleanup block is inside one `try/except`. If `context._bctx.close()` raises (e.g. the context was never created because `browser.launch()` failed mid-scenario), the exception is swallowed and the remaining two cleanup calls are skipped. Each failed scenario leaks a running Playwright process.

**Failure scenario**: `before_scenario` fails after `browser.launch()` but before `new_context()` completes (e.g. port collision on the browser debugger). `context._bctx` is never set. `after_scenario` hits `context._bctx.close()` → `AttributeError` → caught by `except`, exits early. `context._pw.stop()` is never called. Over a full suite run, dozens of orphaned browser processes exhaust ports or memory.

**Fix**: Use `hasattr` guards or separate `try/except` blocks per resource:
```python
def after_scenario(context, scenario):
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
```

---

## Deliverables

- [x] `bddframe/cli.py` — Bug 1: normalize `BDDFRAME_HEADLESS` on passthrough
- [x] `bddframe/cli.py` — Bug 2: mutual-exclusion guard for `--headed` + `--headless`
- [x] `bddframe/hooks.py` — Bug 3: conflict warning when `@headed` and `@headless` both present
- [x] `bddframe/hooks.py` — Bug 4: validate `BDDFRAME_BROWSER` before `getattr` call
- [x] `bddframe/cli.py` — Bug 5: derive behave base from passed path, not hardcoded `features/`
- [x] `bddframe/hooks.py` — Bug 6: per-resource cleanup with `hasattr` guards
- [x] `tests/test_cli_hardening.py` — unit tests for bugs 1, 2, 5 (no browser needed)
- [x] `tests/test_hooks_hardening.py` — unit tests for bugs 3, 4, 6 (mock Playwright context)
