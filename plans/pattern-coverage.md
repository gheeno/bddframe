# BDDFrame — Pattern Coverage Review (BFRAME_0025)

Review of the plain-English steps in `features/**.feature` against the built-in
pattern table (`bddframe/resolver/patterns.py`), plus the manual-tester actions
a mature suite expects but the table doesn't yet cover.

Source date: 2026-06-28. Method: ran `patterns.match(normalize_subject(step))`
over every unique step in the repo; cross-checked against common
Playwright/Selenium tester vocabularies.

---

## 1. Current coverage

117 unique steps. **113 resolve to a built-in pattern; 4 do not** and only work
when the LLM fallback is enabled (`BDDFRAME_MODEL`), which is non-deterministic
and costs a model call per step.

| Unmatched step (in repo today) | Why it misses | Phase |
|--------------------------------|---------------|-------|
| `selects "Action" in the genre filter` | `select` pattern only accepts `… from the X`, not `in the X` | 1 |
| `submits the login form` | no `submit` verb at all | 1 |
| `switches to the previous tab` | no tab/window handling exists | 1 |
| `a new tab should open` | no tab/window handling exists | 1 |

Also relying on the LLM fallback (matched the *wrong* pattern — `should see X`
swallows the suffix and asserts against the **current** page, not the new one):

- `User should see "PLAY" in the new tab`
- `User clicks "Close Tab" in the new tab`

So an entire feature file (`features/busterblock/new_tab.feature`, 3 `@smoke`
scenarios) has **no deterministic support** — it is the single biggest gap.

---

## 2. Manual-tester actions missing (think: someone clicking through an app)

Beyond what's in the repo today, a tester reaches for these constantly. None
have a pattern:

| Action | Example phrasing | Playwright primitive |
|--------|------------------|----------------------|
| Browser nav | `goes back`, `goes forward`, `reloads the page` | `page.go_back/forward/reload` |
| New tab / window | `a new tab should open`, `switches to the new tab` | `context.pages` |
| Double / right click | `double-clicks "Row"`, `right-clicks "File"` | `dblclick`, `click(button="right")` |
| File upload | `uploads "cv.pdf" to the "Resume" field` | `set_input_files` |
| JS dialog | `accepts the dialog`, `dismisses the dialog` | `page.on("dialog")` |
| Key combo | `presses "Control+A"` | `keyboard.press` (single keys only today) |
| Drag & drop | `drags "Card" onto "Done"` | `drag_to` |
| Submit form | `submits the login form` | `form.requestSubmit()` / submit btn |
| Select by label | `selects "Action" in the genre dropdown` | `select_option` |

## 3. FAANG / industry baseline checked against

Patterns common to Cypress, Playwright Test, Selenide and internal FAANG DSLs
that we measured ourselves against:

- **Web-first / auto-retrying assertions** — already covered (Playwright
  locators + our `wait_*`).
- **Accessibility-first locators** — already the core resolution strategy.
- **Explicit waits over sleeps** — covered (`wait_visible/hidden/networkidle`).
- **Tab/window control** — *missing* (Phase 1).
- **Dialog handling, file upload, keyboard combos** — *missing* (Phase 2).
- **Soft assertions / drag-drop / network assertions** — nice-to-have (Phase 3).

---

## Phases

### Phase 1 — close the real gaps + cheap high-value verbs ✅ (this ticket)

Everything that is either used in the repo today or a one-line Playwright call.
No new dependencies.

1. **Tab/window management** (the headline gap):
   - `a new tab should open` — assert a 2nd page exists, focus it.
   - `switches to the new tab` / `switches to the previous|original|first tab`.
   - `closes the tab` / `closes the new tab` — close + fall back to first.
   - `… in the new tab` **suffix** on any step — run that step against the
     newest page (so `should see "X" in the new tab` finally means it).
   - Wired in `execute_step` (it owns `context`, which owns the pages).
2. `submits the (…) form` → click the form's submit control.
3. `selects "X" in the Y (dropdown|filter|menu|list|select)` — widen `select`.
4. `goes back` / `goes forward` / `reloads|refreshes the page`.
5. `double-clicks X` / `right-clicks X`.

### Phase 2 — input-heavy actions (~half day)

- File upload (`uploads "f" to the "X" field`) → `set_input_files`.
- JS dialogs (`accepts|dismisses the dialog`) → register a one-shot
  `page.on("dialog")` handler in `before_scenario`, consumed by the step.
- Key combos (`presses "Control+A"`) → relax `press_key` to allow `Mod+Key`.

### Phase 3 — advanced (when a suite needs it)

- Drag & drop (`drags "A" onto "B"`) → `locator.drag_to`.
- Soft assertions (collect failures, report at scenario end).
- Network assertions (`a request to "X" should have been made`).

Phases 2–3 are deferred, not designed-out — pull them forward by asking.

---

## For testers — the step catalogue

The authoritative, copy-pasteable list of every built-in phrase lives in
**[`guide.md` §6 Built-in step reference](guide.md#6-built-in-step-reference)** —
grouped by Navigation, Forms, Clicks, Tabs & windows, Waiting, Tables,
Assertions, Visual, Network, etc. It is the single source of truth; this
coverage doc only records *gaps and phases*, so we don't keep two lists in sync.

Rule of thumb for writing a step: **say what a manual tester would say.** The
subject (`User` / `I`) and tense are normalised away, so `I click the login
button` and `User clicks the login button` are identical. If a phrase isn't in
§6, either it maps to an existing one (try a synonym) or it's a real gap — open
a ticket and add a pattern (this doc shows how the table is structured).

---

## VSCode — Gherkin LSP (stop the "Undefined step" warnings)

BDDFrame has **no per-step definitions** — the whole suite runs through one
catch-all regex step (`bddframe/steps/catch_all.py`: `@step(r"(?P<anything>.*)")`).
A Gherkin language server that doesn't know this flags **every** line as an
undefined step.

The repo already ships the fix, so a tester only has to **install one
extension**:

- **`.cucumber_stubs.py`** (repo root) — wildcard `@given/@when/@then('.*')`
  stubs. They live *outside* `features/steps/` so behave never loads them; they
  exist only to tell the editor "every step is defined." This file is what the
  extension parses (the default-parser stubs read cleaner than behave's `re`
  matcher).
- **`.vscode/settings.json`** — already points the extension at the stubs:

  ```json
  {
    "cucumberautocomplete.steps": [".cucumber_stubs.py"],
    "cucumberautocomplete.syncfeatures": "features/**/*.feature",
    "cucumberautocomplete.strictGherkinCompletion": false
  }
  ```

### Steps

1. **Install the extension** (Cucumber/behave-aware, language-agnostic):

   ```
   code --install-extension alexkrechik.cucumberautocomplete
   ```

   (or Extensions panel → search **"Cucumber (Gherkin) Full Support"**).

2. **Trigger it**: reload the window — `Cmd/Ctrl+Shift+P` →
   *Developer: Reload Window*. Open any `.feature` file: the undefined-step
   squiggles are gone, with no per-tester config.

> **Caveat:** because every step resolves to the single `.*` stub, the LSP can't
> autocomplete BDDFrame's *English* phrases (they live as regexes in
> `resolver/patterns.py`, not as discrete step defs). Use §6 above as the
> autocomplete reference. The extension still gives Gherkin syntax highlighting,
> table formatting, and snippets — it just won't suggest our verbs.
