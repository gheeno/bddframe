# BFRAME_0033 — Test Run Fix Plan

**Branch:** `feature/BFRAME_0033`
**Triggered by:** Full `features/` run on 2026-06-29 — 103 passed / 86 failed / 1 skipped

Failures fall into six categories. Each section below states what is broken,
the root cause, and the exact fix. Items are ordered by impact (most failures
fixed per change first).

---

## Fix 1 — `assert_visible` doesn't wait for async navigation ✅ DONE

**Impact:** Was causing ~60 failures (all login flows and any `should see` step
following a JS-redirect). Fixed on `feature/BFRAME_0032` during the run
session — `wait_for(state="attached")` added before the visibility scan.

**File:** `bddframe/agents/web/actions.py` — `assert_visible()`

**Status:** Merged into this branch as baseline.

---

## Fix 2 — `assert_state` eagerly evaluates `is_checked()` for all elements

**Impact:** 3 failures
**Scenarios:**
- `Assert element is enabled / disabled` (busterblock/assertions.feature)
- `Assert a button is enabled (default state)` (uitestingplayground)

**Root cause (precise):**
`actions.assert_state()` builds a dict literal `{"enabled": loc.is_enabled(), "checked": loc.is_checked(), ...}` — Python evaluates ALL values eagerly before the key lookup. So `loc.is_checked()` is always called regardless of what `state` is. Playwright throws `Locator.is_checked: Error: Not a checkbox or radio button` for any non-checkbox/radio element (`<select>`, `<button>`, etc.).

**Exact fix:**
`bddframe/agents/web/actions.py` — `assert_state()`, lines 349-357:

```python
# Current (broken):
ok = {
    "enabled":   loc.is_enabled(),
    "disabled":  not loc.is_enabled(),
    "checked":   loc.is_checked(),          # ← always called, throws on <select>
    "unchecked": not loc.is_checked(),
    ...
}[state]

# Fix — lazy lambdas, only the selected key is called:
state_checks = {
    "enabled":   lambda: loc.is_enabled(),
    "disabled":  lambda: not loc.is_enabled(),
    "checked":   lambda: loc.is_checked(),
    "unchecked": lambda: not loc.is_checked(),
    "selected":  lambda: loc.is_checked(),
    "editable":  lambda: loc.is_editable(),
    "readonly":  lambda: not loc.is_editable(),
}
if state not in state_checks:
    raise AssertionError(f"Unknown state '{state}' for '{locator_text}'")
ok = state_checks[state]()
```

**Acceptance:** `assertions.feature @state` passes without `Locator.is_checked: Error: Not a checkbox or radio button`.

---

## Fix 3 — BusterBlock count stale + two separate store_text/locator bugs

**Impact:** ~8 failures
**Scenarios:**
- `Assert a count of visible elements` — `Expected 15 visible 'Add to Cart' — found 50`
- `Grab the catalog heading text via POM alias` — `Stored HEADING = 'Catalog'` (wrong)
- `Capture element text — step dependency injection` — same heading bug
- `Variable chain — set, capture, compare` — same heading bug
- `Capture text from an element that has no accessible name` — `Could not find element to read: '"movie count" text'`
- `Grab a value from a table cell and use it in a search` — `Could not find element to read: '"Die Hard" text'`

### 3a — Count assertion: dataset expanded

**Root cause:** `movies.json` has 50 movies, not 15. The feature comment and step are stale.

**Fix:** `features/web/busterblock/assertions.feature` line 48:
```gherkin
# Then User should see 15 "Add to Cart" items
Then User should see 50 "Add to Cart" items
```

### 3b — POM lookup fires AFTER self-heal partial text (wrong priority order)

**Root cause (precise):** In `bddframe/agents/web/locator.py` — `find()`, the resolution order is:

```
1. a11y strategies (exact)
2. [if ambiguous] POM disambiguation
3. Scroll + retry a11y
4. Partial-text self-heal (first word)  ← POM comes AFTER this
5. POM YAML fallback
6. Vision LLM
```

For locator `catalog heading`:
- a11y: not found (element is an `<h1>`, its text is "VHS Catalog …", doesn't match "catalog heading")
- Scroll retry: same
- Partial text: first word `catalog` → `get_by_label(re.compile("catalog"))` → matches `<h1>` partially, but `inner_text()` on a deeply-nested element that `get_by_text("catalog")` resolves to returns just `'Catalog'` (a text node), not the full h1 text — **returns early, POM never reached**
- Result: `HEADING = 'Catalog'` not `'VHS Catalog'`

**Fix:** `bddframe/agents/web/locator.py` — `find()`: move POM lookup to immediately after the initial a11y miss, before self-heal:

```python
# nothing found — check POM first (explicit > heuristic)
loc = pom.locate(page, text)
if loc:
    logger.info(f"\n  📋 POM: resolved '{text}' via pom.yaml")
    return loc

# Self-heal 1: scroll and retry
...
```

### 3c — `store_text` pattern captures quoted locator + trailing qualifier as one string

**Root cause (precise):** Pattern `^(?:stores?|grabs?) (?:the )?(.+?) (?:as|into|in) …` is lazy but captures EVERYTHING up to ` as `:
- `stores the "movie count" text as \`COUNT_TEXT\`` → group 1 = `"movie count" text`
- `grabs the "Die Hard" text as \`MOVIE_TITLE\`` → group 1 = `"Die Hard" text`

`_q('"movie count" text')` → first char `"`, last char `t` → no stripping → locator = `"movie count" text` → POM lookup misses key `movie count`.

**Fix:** `bddframe/resolver/patterns.py` — add a quoted-locator variant of `store_text` **before** the existing pattern. It strips inner quotes and consumes an optional single trailing qualifier word (`text`, `heading`, `value`, `content`, `label`, `element`):

```python
# Quoted locator with optional qualifier: stores the "X" text/heading as `VAR`
(r'^(?:stores?|grabs?) (?:the )?["\'](.+?)["\'](?:\s+\w+)? (?:as|into|in) [\[`]([^\]`]+)[\]`]$',
                                               'store_text',  lambda m: {'locator': m.group(1), 'var': m.group(2)}),
# Existing unquoted pattern stays as fallback:
(r'^(?:stores?|grabs?) (?:the )?(.+?) (?:as|into|in) [\[`]([^\]`]+)[\]`]$',
                                               'store_text',  lambda m: {'locator': _q(m.group(1)), 'var': m.group(2)}),
```

This makes:
- `stores the "movie count" text as \`X\`` → locator = `movie count` → POM → `id: movie-count` ✓
- `grabs the "Die Hard" text as \`X\`` → locator = `Die Hard` → a11y finds text ✓
- `stores the "catalog heading" as \`X\`` → locator = `catalog heading` → POM → `css: main h1` ✓
- `stores the "VHS Catalog" heading as \`X\`` → locator = `VHS Catalog` → a11y finds heading ✓

**Files to change:**
- `features/web/busterblock/assertions.feature` (3a)
- `bddframe/agents/web/locator.py` — `find()` POM priority (3b)
- `bddframe/resolver/patterns.py` — quoted store_text pattern (3c)

**Acceptance:** All six scenarios above pass.

---

## Fix 4 — New tab detection fails in headless mode (synchronous check, no wait)

**Impact:** 2 failures
**Scenarios:**
- `A click opens a new tab — assert content, then switch back`
- `Checkout receipt opens in a new tab, close it, return to catalog`

**Root cause (precise):**
The step sequence is:
1. `User clicks "Preview"` → click fires; browser starts opening `target="_blank"` tab asynchronously
2. `a new tab should open` → immediately calls `_switch_tab(context, 'new', assert_opened=True)`

`_switch_tab` in `bddframe/orchestrator/runner.py` calls `_pages(context)` synchronously. The browser event hasn't fired yet, so `len(pages) == 1` → raises immediately. No wait at all.

**Exact fix:** `bddframe/orchestrator/runner.py` — `_switch_tab()`:

```python
def _switch_tab(context, target, assert_opened=False):
    pages = _pages(context)
    if assert_opened and len(pages) < 2:
        # New tab opens asynchronously — wait for the page event.
        bctx = getattr(context, "_bctx", None)
        if bctx is None:
            raise AssertionError("Expected a new tab to open, but only one tab is open")
        timeout_ms = int(os.getenv("BDDFRAME_TIMEOUT", "10000"))
        try:
            bctx.wait_for_event("page", timeout=timeout_ms)
        except Exception:
            raise AssertionError("Expected a new tab to open, but only one tab is open")
        pages = _pages(context)  # refresh after event fired
    _focus(context, pages[-1] if target in ('new', 'last') else pages[0])
```

Key: `bctx.wait_for_event("page")` blocks until a new `Page` is created in the context (timeout in ms). The fast-path `if len(pages) < 2` means if the tab already opened by the time we check, we skip the wait entirely.

**File to change:** `bddframe/orchestrator/runner.py` — `_switch_tab()`

**Acceptance:** Both navigation tab scenarios pass with `--headless`.

---

## Fix 5 — UITestingPlayground "password" field ambiguity

**Impact:** ~4 failures (sampleapp login scenarios across persona_test suite)
**Scenarios:**
- `Press Tab to move focus between fields`
- `Valid credentials log the user in` (persona_test/09_e2e_login)
- `Store welcome message text…`
- `Screenshot captured on successful login`

**Root cause:**
UITestingPlayground's `/sampleapp` page has this in the prose:

```html
<p>Fill in and submit the form. For successful login use…</p>
```

`get_by_text("password", exact=False)` matches this `<p>` element before it
reaches the actual `<input type="password">`. Playwright then tries to call
`.fill()` on a `<p>` and throws `Element is not an <input>…`.

**Fix:**
Add a POM alias file for UITestingPlayground sampleapp so the "password" step
resolves by id/label rather than text search:

```yaml
# features/persona_test/pom.yaml  (create if not present)
password:
  selector: "#password"   # <input id="password"> on /sampleapp
username:
  selector: "#userName"
```

This is the correct BDDFrame mechanism for pages where accessible labels are
ambiguous — POM aliases short-circuit the text search.

**Files to change:**
- Create `features/persona_test/pom.yaml`

**Acceptance:** All sampleapp login scenarios pass; "password" resolves to the
`<input>` not the `<p>`.

---

## Fix 6 — Ollama llama3.1:8b (text-only) fails pure_llm and llm_fallback

**Impact:** 5 failures
**Scenarios:**
- `Full LLM mode — entire login flow interpreted by the model`
- `Full LLM mode — catalog interaction in natural language`
- `An unrecognised verb falls through to the LLM`
- `A second unrecognised verb handled by the model`
- `Authenticate using a verb the regex layer cannot parse` (web/fallback-demo)

**Root cause:**
`llama3.1:8b` is text-only. Without a screenshot it cannot locate elements
visually. Specific failure modes observed:

| Scenario | Error | Cause |
|----------|-------|-------|
| Login flow (pure_llm) | Stuck on `about:blank` | Model returned no valid action for "BusterBlock video store is open at URL" |
| Catalog interaction (pure_llm) | `unknown url type: '/login'` | Model returned relative URL `/login` instead of full URL |
| llm_fallback "authenticates" | `Could not find element: 'login_button'` | Model returned snake_case locator; element text is `Login` |
| llm_fallback "verifies" | Follows above failure | Cascades from failed login |
| web/fallback-demo | Same `login_button` issue | Same model, same pattern |

**Fix options (in order of preference):**

**6a — Pull llava (recommended, free, stays local):**
```bash
ollama pull llava
```
Then run LLM tests with `BDDFRAME_MODEL=ollama/llava`. Vision-capable; can see
the screenshot to locate elements correctly.

**6b — Use a cloud vision model for LLM tests only:**
```bash
BDDFRAME_MODEL=anthropic/claude-haiku-4-5-20251001 ANTHROPIC_API_KEY=... \
bddframe run features/web/busterblock/llm_fallback.feature features/web/busterblock/pure_llm.feature
```

**6c — Improve the LLM system prompt for text-only models:**
The prompt currently assumes the model will receive a screenshot. For text-only
fallback, the prompt should make the accessibility tree available explicitly so
the model can return a correct locator. This is a deeper change — log as
`BFRAME_0034` if needed.

**Acceptance:** All five LLM scenarios pass when run with `ollama/llava` or a
cloud vision model.

---

## Fix 7 — UITestingPlayground count and navigation regressions

**Impact:** ~4 failures
**Scenarios:**
- `Count of visible section links on the home page` — `Expected 1, found 2`
- `Browser back and forward through history`
- `Assert page title contains 'UI Test AutomationPlayground'`
- `Double-click on a mouseover link` (timeout)

**Root cause:**
UITestingPlayground's live site has changed since these tests were written:
- Home page now has 2 elements matching "Dynamic ID" (count was 1)
- `<title>` on the click-trap page is `Sample App` not `UI Test AutomationPlayground`
- Back/forward history scenario lands on the wrong page
- Double-click anchor has a JS mouseenter handler that repositions the element
  before `dblclick()` fires, causing a timeout

**Fix:**
These are live-site tests — the site changed. Options:

**7a — Update the feature assertions to match current site state:**
- Change `Expected 1 visible 'Dynamic ID'` to `2`
- Update the title assertion to the current `<title>` value
- Fix the back/forward scenario to match current page structure

**7b — Tag these scenarios `@live` and skip in CI:**
Live-site tests are inherently fragile. Tag them `@live` so they're excluded
from the headless CI run and only run deliberately:
```bash
bddframe run features/ --tag ~@live   # skip live-site tests
bddframe run features/ --tag @live    # run only live-site tests
```

**Recommended:** 7b — add `@live` tag, update known counts, skip double-click
or wrap it in `@xfail`-equivalent (`@quarantine`).

**Files to change:**
- `features/persona_test/` — affected scenarios
- `features/canadiantire/` — these are also live-site; add `@live`

---

## Fix 8 — External REST API daily rate limit

**Impact:** ~10 failures (all `persona_test/` REST suite + `features/api/`)
**Cause:** `restful-api.dev` enforces 50 req/24h unauthenticated. Running the
full suite in one pass exhausts the quota.

**Not a code fix.** Options:

**8a — Register a free account** at `https://restful-api.dev/sign-in` and add
the auth header to REST steps via `secrets.env`.

**8b — Spread runs across the day** or run REST tests in isolation first.

**8c — Mock the REST API** for the assertion/count scenarios and keep only the
lifecycle tests (create → read → delete, scoped to self-created objects) as
live-API tests.

**Recommended:** 8b short-term. Log 8c as a future improvement if the suite
grows large enough to routinely hit the cap.

---

## Fix 9 — Scenario outline data: Jaws is Thriller, not Horror

**Impact:** 1 failure
**Scenario:** `Genre filter — one outline, multiple genre/movie combos -- @1.2`

**Root cause:** `movies.json` has `Jaws` with `genre: "Thriller"`, not `"Horror"`. The Examples table says `| Horror | Jaws |`. After filtering to Horror, Jaws doesn't appear → `assert_visible("Jaws")` fails. @1.1 (Action/Die Hard) passes because Action IS Die Hard's genre. @1.3 (Sci-Fi/Back to the Future) also passes — correct genre.

**Fix:** `features/web/busterblock/scenario_outline.feature` — Examples table:
```gherkin
Examples:
  | genre  | expected_movie      |
  | Action | Die Hard            |
  | Horror | Halloween           |   # ← was Jaws (Thriller); Halloween is Horror
  | Sci-Fi | Back to the Future  |
```
Horror movies in dataset: `Halloween`, `The Shining`, `Poltergeist`, `A Nightmare on Elm Street`.

**File to change:** `features/web/busterblock/scenario_outline.feature`

---

## Fix 10 — `assert_hidden` is synchronous; race condition with debounced search

**Impact:** 1 failure
**Scenario:** `Fill the catalog search field` (text_input.feature)

**Root cause:** BusterBlock's search field uses `addEventListener('input', debounce(loadMovies, 280))` — the catalog refilters 280ms after the last keystroke. Playwright's `fill()` triggers the `input` event once, starting the 280ms timer. The next step `assert_visible("The Terminator")` passes immediately (Terminator is already in the full catalog, no wait needed). Then `assert_hidden("Die Hard")` fires before the 280ms debounce resolves → Die Hard is still visible → failure.

`assert_hidden` is a synchronous point-in-time check — no retry/wait at all:
```python
def assert_hidden(page: Page, text: str):
    loc = page.get_by_text(text, exact=False)
    if loc.count() == 0 or not loc.first.is_visible():
        return
    raise AssertionError(...)  # immediate fail, no wait
```

**Fix:** `bddframe/agents/web/actions.py` — `assert_hidden()`: if the element IS visible at the moment of check, wait up to `BDDFRAME_TIMEOUT` ms for it to become hidden before failing:

```python
def assert_hidden(page: Page, text: str):
    loc = page.get_by_text(text, exact=False)
    if loc.count() == 0:
        return
    if not loc.first.is_visible():
        return
    # Element is visible — wait for it to disappear (handles debounced filters etc.)
    timeout_ms = int(os.getenv("BDDFRAME_TIMEOUT", "10000"))
    try:
        loc.first.wait_for(state="hidden", timeout=timeout_ms)
    except Exception:
        raise AssertionError(
            f"Expected '{text}' to NOT be visible — but it is.\nURL: {page.url}"
        )
```

Fast-path: if element absent (`count == 0`) or already hidden → return immediately (no perf hit for normal cases). Slow-path: element visible → wait up to timeout for it to hide.

**File to change:** `bddframe/agents/web/actions.py` — `assert_hidden()`

---

## Fix 11 — `re.match` without `re.DOTALL` breaks multi-line substituted values

**Impact:** 1 failure
**Scenario:** `Load multiple payloads from a table — each stored by filename stem` (resource_files.feature)

**Root cause:** `seed_cart.json` is a multi-line JSON file:
```json
{
  "username": "reel_ryan",
  "items": [{"movieId": 2, "qty": 1}]
}
```
After `load_resource` stores it and `` `PAYLOAD` `` is substituted into the step text, the result is:
```
{\n  "username": "reel_ryan",\n  ...}\n should contain "reel_ryan"
```
`patterns.match()` calls `re.match(pattern, step_text, re.IGNORECASE)`. Without `re.DOTALL`, `.` doesn't match `\n`, so `(.+?)` in `assert_compare` pattern can't consume the newlines → no pattern matches → step falls through to LLM (auto mode) → LLM not configured → empty `AssertionError`.

**Fix:** `bddframe/resolver/patterns.py` — `match()`: add `re.DOTALL`:

```python
def match(step_text: str):
    for pattern, action_type, extractor in PATTERNS:
        m = re.match(pattern, step_text, re.IGNORECASE | re.DOTALL)
        if m:
            return action_type, extractor(m)
    return None
```

`re.DOTALL` only affects `.` (now matches `\n`); it does NOT change `^`/`$` behaviour (those need `re.MULTILINE`). Anchors still bind to string start/end, so no existing patterns are broken.

**File to change:** `bddframe/resolver/patterns.py` — `match()`

---

## Execution order

| Priority | Fix | Est. effort | Scenarios recovered |
|----------|-----|-------------|---------------------|
| 1 | Fix 2 — `assert_state` lazy eval (`is_checked` eager throw) | 10 min | 1+ |
| 2 | Fix 3a — BusterBlock count stale (15→50) | 5 min | 1 |
| 3 | Fix 3b — POM priority before self-heal partial text | 10 min | 3 |
| 4 | Fix 3c — `store_text` quoted pattern + qualifier | 15 min | 2 |
| 5 | Fix 4 — New tab `wait_for_event("page")` | 10 min | 2 |
| 6 | Fix 9 — Outline data: Jaws→Halloween | 2 min | 1 |
| 7 | Fix 10 — `assert_hidden` wait for disappear | 10 min | 1 |
| 8 | Fix 11 — `re.DOTALL` in pattern match | 5 min | 1 |
| 9 | Fix 5 — UITestingPlayground POM aliases | 30 min | 4 |
| 10 | Fix 6 — `ollama pull llava` | 15 min | 5 |
| 11 | Fix 7 — Live-site tag + count updates | 1 h | 4 |
| 12 | Fix 8 — REST rate limit (defer or mock) | — | 10 |

Fixes 2–11 (busterblock-targeted) recover **12 scenarios** across saucedemo/canadiantire/busterblock with pure BDDFrameEngine.
Completing all fixes should bring the full suite to **~120+ passing with <15 expected failures** (live-site / rate-limited category).
