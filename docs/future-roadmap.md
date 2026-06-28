# BDDFrame — Future Roadmap

Implementation plan for the gaps identified in the 2026-06-28 peer review.
Source: [enterprise-plan.md → Future Plans](enterprise-plan.md#future-plans).

Status: proposed. Not yet scheduled.

---

## Phase E — Parallelism ceiling (F1) ✅ Done

**Status:** implemented in `feature/BFRAME_0021`.
[`scripts/list_features.py`](../scripts/list_features.py) discovers web feature
files and both Azure pipelines consume it as a dynamic matrix. Sharding is
**web-only** by design — files tagged `@appium`/`@desktop`/etc. are excluded
(see Phase F/G for those platforms' own runners).

**Goal:** shard at the feature-*file* level, not the feature-*folder* level.
Eliminates uneven agent load and removes the manual matrix-row requirement.

**Approach:** dynamic Azure DevOps matrix. A pre-job discovers all `.feature`
files and emits the matrix JSON; the test job consumes it. No new Python
dependencies. behave stays single-process per shard — we just shard finer.

### Steps

1. **Add a discovery script** (`scripts/list_features.py`).
   - Walks `features/` and prints a JSON array of relative paths.
   - Filters out files with no scenarios (empty or comment-only).

2. **Update `azure-pipelines.yml`.**
   - Add a `discover` job that runs the script and sets an output variable
     (`featuresJson`).
   - Change the `tests` job to `dependsOn: discover` and set
     `strategy.matrix` from `$[ dependencies.discover.outputs['...'] ]`.
   - Each matrix entry gets `featurePath` pointing at one `.feature` file.

3. **Update `azure-pipelines-windows.yml`** with the same change.

4. **Verify** that `allure-results/` from each shard are published under
   distinct artifact names and merged correctly in the Tests tab.

### Acceptance criteria

- Adding a new `.feature` file anywhere in `features/` auto-appears as a
  shard with no YAML edit.
- No agent runs more than one feature file per job.
- Existing JUnit + Allure artifact publishing is unchanged.

### Follow-up — local parallelism (BFRAME_0022) ✅ Done

- `behavex` added as an opt-in `[parallel]` extra for **local** multi-process
  runs (`bddframe run --parallel N`, web only). CI stays on the dynamic matrix;
  the two aren't stacked. Reporting was made parallel-safe (per-worker
  `allure-results/p<pid>/` dirs, merged on completion).
- `pytest-bdd` migration — still skipped; no benefit over behave + behavex.

---

## Phase F — Appium / native mobile (F2)

**Goal:** `@appium` tag drives a real device or emulator via Appium, using the
same plain-English Gherkin steps as the web agent where possible.

### Steps

1. **Add `[mobile]` optional dependency** in `pyproject.toml`.
   ```
   mobile = ["Appium-Python-Client>=3.0.0"]
   ```

2. **Create `bddframe/agents/mobile/` package.**
   - `driver.py` — session lifecycle: `start_session(capabilities)`,
     `stop_session()`. Capabilities loaded from `BDDFRAME_APPIUM_URL`,
     `BDDFRAME_APPIUM_CAPS` (JSON string or path to a `.json` file).
   - `locator.py` — find by `accessibility_id`, `resource-id`, `content-desc`,
     XPath. Mirror the fallback chain from the web locator (accessibility first,
     POM YAML second, fail loudly third).
   - `actions.py` — tap, swipe, long-press, back, home, send-keys. Wrap
     Appium's `TouchAction` / W3C Actions.

3. **Add mobile patterns** to `bddframe/resolver/patterns.py`.
   - `tap the "X" button` → `{type: tap, locator: X}`
   - `swipe left|right|up|down` → `{type: swipe, direction: ...}`
   - `press the back button` → `{type: back}`
   - Existing `click`, `fill`, `assert_visible` patterns stay unchanged and
     are re-used where Appium's accessibility tree supports them.

4. **Wire `@appium` into `hooks.py`.**
   - `before_scenario`: if `'appium' in tags`, start an Appium session instead
     of a Playwright browser. Store the driver as `context.driver`.
   - `after_scenario`: call `driver.quit()`.
   - Keep web and visual paths untouched.

5. **Route in `orchestrator/runner.py`.**
   - Add `elif t == 'tap': mobile_actions.tap(...)` etc. alongside existing
     web dispatch.

6. **Add an `environments.yaml` key** for the Appium server URL so tests can
   reference `[APPIUM_SERVER]` without hardcoding.

7. **Write a smoke feature** (`features/mobile/smoke.feature`) targeting
   Android Settings as a known-stable target for CI validation.

### Acceptance criteria

- `bddframe run features/mobile/ --tag appium` drives a connected emulator.
- `@web` scenarios are unaffected.
- Session cleanup runs even on scenario failure.

### Skipped for now

- iOS XCUITest path — validate Android first; iOS requires macOS agent and
  Xcode, defer until Android path is stable.
- Biometric/gesture advanced actions.

---

## Phase G — Desktop automation gaps (F3)

Three sub-phases in priority order.

### G1 — Wire `focus_region` (highest priority, ~1 day)

**Problem:** `focus_region` parses the region string but never narrows the
OpenCV or OCR search area. Any step that follows it searches the full screen.

**Fix:**

1. Add a module-level `_active_region: dict | None = None` to
   `bddframe/agents/visual/screenshot.py` (or a new `context.py`).

2. Update `capture()` in `screenshot.py` to crop the captured frame to
   `_active_region` when set.

3. In `visual_runner.py`, handle `focus_region` by calling
   `screenshot.set_region(regions.parse_region(params["region"]))` instead of
   the current no-op. Reset to `None` at scenario start (add to `hooks.before_scenario`).

4. All downstream calls (`matcher.find_on_screen`, `ocr.find_text_on_screen`,
   `vision_locate.locate_by_description`) pick up the crop automatically via
   `capture()` — no changes needed in those files.

5. Add unit tests: region crops correctly; `None` region returns full frame.

### G2 — Multi-word OCR phrase matching (~half day)

**Problem:** `ocr.find_text_on_screen("Save As")` fails when Tesseract returns
`"Save"` and `"As"` as separate bounding boxes on the same line.

**Fix in `ocr.py`:**

1. After `image_to_data`, group words by `(block_num, par_num, line_num)`.
2. Join each group into a line string with spaces.
3. Search `needle` in the joined line (case-insensitive).
4. Return the centroid of the matched word range within that line.

Existing single-word searches continue to work — they're a subset of phrase
matching.

### G3 — Window management (~1 day)

**Problem:** no way to bring a desktop window to the foreground or find a
window by title before interacting with it. Causes focus-stealing failures when
multiple apps are open.

**Fix:**

1. Add `bddframe/agents/visual/window.py`.
   - `focus_window(title: str)` — uses `pygetwindow` on Windows/macOS,
     `wmctrl` on Linux. Falls back gracefully with a clear error if neither
     is available.
   - `list_windows() -> list[str]` — for debugging.

2. Add `[desktop]` optional dependency: `pygetwindow>=0.0.9`.

3. Add a visual pattern: `focus window "title"` → `focus_window` action.

4. Wire dispatch in `visual_runner.py`.

### Deferred (F3d, F3e)

- **Multi-monitor** (F3d): expose `BDDFRAME_MONITOR=N` and thread it through
  `mss` capture. Low complexity, low demand — add when a user reports it.
- **Win32/COM** (F3e): only viable if a specific legacy app is targeted.
  Requires Windows-only CI agent. Defer indefinitely until there is a named
  app to test against.

---

## Phase H — Remote browser execution (F4)

**Goal:** `BDDFRAME_REMOTE_URL` points Playwright at a remote CDP endpoint
(BrowserStack, Sauce Labs, Playwright grid).

### Steps

1. **`hooks.before_scenario`**: if `BDDFRAME_REMOTE_URL` is set, call
   `browser_type.connect(ws_endpoint=url)` instead of `browser_type.launch(...)`.
   The rest of the scenario lifecycle is unchanged — `context.page` is the same
   object either way.

2. **Add `BDDFRAME_REMOTE_URL`** to `.env.example` and `docs/guide.md`.

3. **Document capability injection** for BrowserStack/Sauce Labs (they require
   a capabilities header in the WS URL).

4. **CI matrix**: add an optional `remote` job that runs the saucedemo suite
   against BrowserStack when `BDDFRAME_REMOTE_URL` is set in the variable group.

### Acceptance criteria

- `BDDFRAME_REMOTE_URL=wss://... bddframe run features/saucedemo/` runs against
  a remote browser without code changes.
- Local runs (no `BDDFRAME_REMOTE_URL`) are unaffected.

---

## Phase I — LLM cost cap (F5)

**Goal:** prevent runaway model spend when a build is badly broken.

### Steps

1. Add `BDDFRAME_LLM_MAX_CALLS` (int, default `0` = unlimited) to `.env.example`.

2. Add a call counter to `bddframe/llm/client.py` — module-level `_call_count`
   reset in `hooks.before_all`.

3. Before every `ask()` / `ask_vision()` call, check the counter. If at cap,
   log a warning and raise `AssertionError` with a clear message
   ("LLM call cap reached — set BDDFRAME_LLM_MAX_CALLS to raise or 0 to disable").

4. RCA calls (`rca.review`) are counted separately via `BDDFRAME_RCA_MAX_CALLS`
   so a cap on fallback steps doesn't also silence RCA.

---

## Phase J — Multi-user / multi-context flows (F6)

**Goal:** a single scenario can drive two simultaneous browser sessions (e.g.
buyer and seller, two concurrent users).

### Steps

1. Extend `context._vars` to store named browser contexts:
   `context._named_contexts: dict[str, Page] = {}`.

2. Add patterns:
   - `Given a new browser context as "buyer"` — creates a second
     `BrowserContext` + `Page`, stores as `context._named_contexts["buyer"]`.
   - `When acting as "buyer"` — sets `context.page` to the named context's page
     for the duration of the step block.
   - `Then acting as "seller"` — same pattern, different name.

3. `hooks.after_scenario`: close all named contexts before the primary one.

4. Write a demo feature in `features/busterblock/` that seeds two user carts
   and asserts both are isolated.

---

## Phase K — Step-level retry (F7)

**Goal:** a flaky single step (SSO redirect, CDN asset) retries in place without
restarting the scenario.

### Steps

1. Add `BDDFRAME_STEP_RETRIES` (int, default `0`) to `.env.example`.

2. In `bddframe/steps/catch_all.py` (the catch-all step that calls
   `execute_step`), wrap the call in a retry loop when the count is > 0.
   Only retry on `AssertionError` or Playwright `TimeoutError`; let
   unexpected exceptions propagate immediately.

3. Add a `@retry_step` scenario tag that overrides the env var to `1` for
   that scenario, so individual flaky scenarios can opt in without enabling
   it globally.

4. Record step-level retries in `healing.jsonl` with `strategy: "step-retry"`
   so they show up in the healing report alongside locator heals.

---

## Suggested sequencing

| Phase | Effort | Impact | Suggested order |
|-------|--------|--------|-----------------|
| G1 — focus_region wire-up | ~1 day | Unblocks reliable desktop testing | First |
| E — file-level sharding | ~2 days | Removes parallelism ceiling | Second |
| G2 — multi-word OCR | ~0.5 day | Correctness fix for desktop | With G1 |
| I — LLM cost cap | ~0.5 day | Risk control, low effort | Third |
| H — remote browser | ~1 day | BrowserStack/Sauce Labs unlock | Fourth |
| G3 — window management | ~1 day | Completes desktop story | Fifth |
| K — step-level retry | ~1 day | Quality-of-life for flaky suites | Sixth |
| J — multi-context flows | ~2 days | Unlocks multi-user scenarios | Seventh |
| F — Appium | ~1 week | New platform, largest scope | Last |
