# BDDFrame — The Complete Guide

Everything a tester needs, in the order you'll need it: install, write your first
test, run it, read the output, then the harder stuff — problematic locators
(`pom.yaml`), shared state, tags, recording, reports, CI, and the editor.

New to *how* it works under the hood? Read **[Architecture](architecture.md)**.
Just want the elevator pitch and copy-paste commands? The
**[README](../README.md)** has them.

---

## Contents

1. [Install](#1-install)
2. [Configure — `.env`](#2-configure--env)
3. [Write your first test](#3-write-your-first-test)
4. [Run it & read the output](#4-run-it--read-the-output)
5. [`pom.yaml` — when natural naming fails](#5-pomyaml--when-natural-naming-fails)
6. [Built-in step reference](#6-built-in-step-reference)
7. [Variables & shared state](#7-variables--shared-state)
8. [Reports](#8-reports)
9. [Recording a test](#9-recording-a-test)
10. [The visual / desktop agent](#10-the-visual--desktop-agent)
11. [CI — Azure DevOps](#11-ci--azure-devops)
12. [VS Code extension](#12-vs-code-extension)
13. [Testing the framework itself](#13-testing-the-framework-itself)

---

## 1. Install

**Prerequisites:** Python 3.11+, and [uv](https://docs.astral.sh/uv/) (the
project ships `uv.lock`; plain `pip` also works everywhere below).

```bash
git clone https://github.com/gheeno/bddframe.git
cd bddframe

# Core only (no LLM, no OpenCV)
uv pip install -e .            # or: pip install -e .
playwright install chromium

# OR everything at once
uv pip install -e ".[all]"
playwright install chromium
```

Install only the extras you need:

| Extra | Adds | Command |
|-------|------|---------|
| `llm` | LLM step fallback + semantic assertions | `uv pip install -e ".[llm]"` |
| `reporting` | Allure reports + JUnit XML | `uv pip install -e ".[reporting]"` |
| `visual` | Desktop agent (OpenCV, Tesseract, PyAutoGUI) | `uv pip install -e ".[visual]"` |
| `lsp` | VS Code language server | `uv pip install -e ".[lsp]"` |
| `all` | Everything | `uv pip install -e ".[all]"` |

For reports you also need the **Allure CLI** binary: `brew install allure`
(macOS) / scoop / `npm i -g allure-commandline`.

### Project layout

```
bddframe/           ← the package (cli, hooks, agents, resolver, reporting, llm, lsp)
features/           ← your tests live here
  saucedemo/
    checkout.feature
    pom.yaml        ← element aliases for this folder (optional)
  pom.yaml          ← global element aliases (optional)
  steps/            ← auto-wired catch-all — do not edit
  environment.py    ← hooks entry point — do not edit
.env                ← credentials + config (gitignored)
.env.example        ← copy this to .env
```

---

## 2. Configure — `.env`

```bash
cp .env.example .env
```

Three tiers of settings:

**Global browser defaults** (rarely change):

```bash
BDDFRAME_BROWSER=chromium        # chromium | firefox | webkit
BDDFRAME_HEADLESS=false          # true = no visible window
BDDFRAME_TIMEOUT=10000           # ms to wait for elements
BDDFRAME_STRICT_LOCATOR=false    # true = ambiguous locators FAIL (recommended in CI)
```

**Per-app credentials/URLs** — the bundled example uses the public
[saucedemo.com](https://www.saucedemo.com) (safe to use):

```bash
SAUCE_USERNAME=standard_user
SAUCE_PASSWORD=secret_sauce
BASE_URL=https://www.saucedemo.com
```

**LLM (optional)** — leave unset for a fully local run. See
[Architecture → The LLM layer](architecture.md#5-the-llm-layer):

```bash
# BDDFRAME_MODEL=ollama/llama3
# BDDFRAME_LLM_URL=http://localhost:11434
# BDDFRAME_VISION_MODEL=ollama/llava
```

Any `[variable]` in a `.feature` file maps to the matching env var, uppercased
with spaces → underscores: `[sauce username]` → `SAUCE_USERNAME`. Values load
from `.env` first, then the shell environment (so CI pipeline variables work
unchanged).

---

## 3. Write your first test

Feature files live in `features/`, one subfolder per app or domain. Here's a
complete, real test against the public demo site — **no Python, no selectors, no
page objects.**

`features/login/login.feature`:

```gherkin
@web @headless
Feature: Login

  Scenario: Standard user logs in
    Given User is on "https://www.saucedemo.com"
    When User enters [SAUCE_USERNAME] in the username field
    And User enters [SAUCE_PASSWORD] in the password field
    And User clicks the login button
    Then User should see "Products"
```

Why each step resolves with zero config:

| Step | Resolves via |
|------|--------------|
| `... username field` | input placeholder "Username" |
| `... password field` | input placeholder "Password" |
| `clicks the login button` | button accessible name "Login" |
| `should see "Products"` | plain DOM text |

The subject (`User`, `I`, `The user`, `As a user`) is stripped automatically, so
`User clicks…`, `I click…`, and `clicks…` are equivalent.

The bundled `features/saucedemo/checkout.feature` is a full end-to-end purchase
flow if you want a longer example.

---

## 4. Run it & read the output

```bash
bddframe run                                   # all features
bddframe run features/login/login.feature      # one file
bddframe run features/saucedemo/               # one folder
bddframe run --tag smoke                        # only @smoke scenarios
bddframe run --headless                         # no visible browser
bddframe run --headed                           # force visible (overrides .env)
bddframe run --browser firefox                  # firefox | webkit
bddframe list                                   # discovered scenarios, no browser
bddframe validate                               # parse + check [variables], no browser
```

**What to expect:**

- Pass/fail printed per scenario.
- On failure: `screenshots/FAILED_<step>.png` (annotated).
- With `[reporting]` installed: Allure JSON written to `allure-results/` automatically.

**Log lines that tell you which resolution path fired:**

| Log line | Means |
|----------|-------|
| *(a step that's neither logged nor errored)* | resolved by the accessibility tree — free |
| `📋 POM: resolved '<key>' via pom.yaml` | accessibility missed → POM fallback hit |
| `🔧 Healed: found '<text>' via vision LLM` | both missed → vision LLM (Trigger 2) hit |
| `⚠️  Ambiguous locator '<text>' — matched multiple elements` | label matched 2+ elements (warns, or fails under `@strict`) |

Capture is off by default, so everything streams live.

### Browser & display tags

Add tags to a `Scenario` or `Feature` (feature-level applies to every scenario):

| Tag | Effect |
|-----|--------|
| `@web` | Chromium (default) |
| `@headless` / `@headed` | No window / force visible (overrides `--headless` and `.env`) |
| `@firefox` / `@webkit` | Switch engine |
| `@mobile @iphone` / `@mobile @android` | iPhone 13 / Pixel 5 emulation |
| `@slow` | 500 ms delay between actions (debugging) |
| `@record_video` | Record `.webm` to `videos/` |
| `@strict` | Ambiguous locators **fail** instead of using the first match |
| `@visual` | Route to the desktop/OpenCV agent |

**Priority (highest wins):** `@headed` > `@headless` > `--headed` > `--headless` > `.env`

```gherkin
@headless
Feature: Regression Suite        ← all scenarios headless

  @web @smoke
  Scenario: Standard login        ← headless (inherited)

  @web @headed
  Scenario: Debug this one        ← headed, overrides the Feature tag
```

---

## 5. `pom.yaml` — when natural naming fails

Write the step in plain sentences first and **run it**. Only reach for `pom.yaml`
when a step actually fails or warns — the message prints the exact key to use.
These are the three problems you'll actually hit.

### Problem A — element has no readable label (icon-only button)

Saucedemo's burger menu is `<button id="react-burger-menu-btn">Open Menu</button>`
— the text is visually hidden, so `clicks the burger menu` finds nothing.

```
Assertion Failed: Could not find element to click: 'burger menu'
```

**Fix:** add a `pom.yaml` next to the feature. The key is the step label minus the
subject, `the`, and the type suffix (`button`/`field`/`input`/`box`):

```yaml
# features/<app>/pom.yaml
burger menu:
  id: react-burger-menu-btn
```

Re-run and you'll see `📋 POM: resolved 'burger menu' via pom.yaml`.

Supported selector types: `css`, `xpath`, `id`, `testid`, `text`, `role`.

> **Key mapping:** `clicks the search button` → key `search`; `enters X in the
> username field` → key `username`; `clicks "Add to Cart"` → key `Add to Cart`
> (quoted = exact, nothing stripped). Keys are case- and whitespace-insensitive.

### Problem B — the label matches many elements (ambiguous)

Six identical "Add to cart" buttons → `clicks "Add to cart"` matches all six.
Default (lenient): warns and clicks the first. Two ways to handle it:

1. **Make CI strict** — `@strict` tag or `BDDFRAME_STRICT_LOCATOR=true`. The step
   then fails with the candidate list, forcing you to disambiguate.
2. **Scope it in `pom.yaml`** — a POM entry is always used *before* blind
   first-match:
   ```yaml
   add to cart:
     xpath: "(//button[contains(.,'Add to cart')])[1]"   # or a container scope
   ```

Prefer container scoping (`//header//input[@type='search']`) over positional
`[1]` — it survives DOM reordering.

### Problem C — same name, different element per page

`search` means the home bar on `/` but the results filter on `/search`. Scope by
URL — the framework reads the live URL and picks the matching block:

```yaml
pages:
  home:
    match: { url_contains: "saucedemo.com/$" }   # regex on page.url
    search: { css: "input.home-search" }
  results:
    match: { url_contains: "/inventory" }
    search: { css: "input.results-filter" }
shared:                                           # checked after the active page
  cookie accept: { id: onetrust-accept-btn-handler }
```

For single-page apps where the URL never changes, pin the page explicitly:

```gherkin
Given User is on the "results" page
```

### Scope: local vs global

| File | Applies to | Use for |
|------|-----------|---------|
| `features/<app>/pom.yaml` | that subfolder only | site-specific elements |
| `features/pom.yaml` | all feature files | shared elements (cookie banners, nav) |

Local wins when the same key exists in both. A flat `pom.yaml` (no `pages:` /
`shared:`) is fully supported — page-scoping is opt-in.

### Lookup order (what the framework tries)

```
1. Accessibility tree — role / label / placeholder / text   (most steps stop here)
2. If MANY match → ambiguity: POM scoped entry, else warn/fail   (Problem B)
3. Self-heal: scroll, then partial-text retry
4. POM yaml — page-scoped block → shared → flat keys   (Problems A & C)
5. Vision LLM (only if BDDFRAME_MODEL is set; else the step fails)
```

Full picture, including the LLM boundary: [Architecture → Resolution hierarchy](architecture.md#4-the-resolution-hierarchy).

### Shadow DOM, SVG & containers

- **Shadow DOM** — Playwright's `css`/`role`/`text`/`id`/`testid` engines pierce *open* shadow DOM automatically, so web-component pages mostly "just work." **Avoid `xpath` POM selectors on shadow-DOM pages — XPath does not cross shadow boundaries.** *Closed* shadow DOM is reachable only by the vision LLM.
- **SVG** — real DOM, so it's targetable. An SVG with `<title>` or `role="img"` + `aria-label` resolves by name; otherwise treat it like an icon-only button (a `css`/`testid` POM entry).
- **Containers** — scope with a row/section step (below) or a scoped `pom.yaml` page-block; don't bake container paths into the sentence.

---

## 6. Built-in step reference

40+ patterns work out of the box. Subject is stripped automatically.

### Navigation
```gherkin
Given User is on "https://example.com"
When User navigates to "https://example.com/cart"
When User goes to "https://example.com/checkout"
When User opens "https://example.com"
Given User is on the "results" page          # pin a POM page (SPAs)
```

### Forms
```gherkin
When User enters "value" in the email field
When User enters [MY_EMAIL] in the email field
When User fills in the username with "admin"
When User types "hello" into the search box
When User clears the search field
When User selects "Medium" from the size dropdown
When User checks the "Remember me" checkbox
When User unchecks the newsletter checkbox
```

### Clicks, keyboard & hover
```gherkin
When User clicks the login button
When User clicks "Submit"
When User clicks the "Proceed to Checkout" link
When User presses the confirm button          # a click
When User taps "Menu"
When User presses Enter                        # a keyboard key
When User hovers over the "Account" menu
```

### Waiting & scrolling
```gherkin
And User waits for the page to load
And User waits until "Order confirmed" appears
And User waits until "Spinner" disappears
And User waits 2 seconds
When User scrolls down
When User scrolls to "Footer"
```

### Tables & containers (D365-style grids)
```gherkin
When User clicks "Edit" in the row containing "Contoso"
When User clicks the "Save" button in the "Payment" section
Then the cell in row "Contoso" column "Status" should be "Active"
And the grid should have 5 rows
Given User switches to the "main" frame        # iframe
```

### Assertions
```gherkin
Then User should see "Products"
Then User should not see "Error"
Then User should have url containing "dashboard"
And the page title should contain "Swag Labs"
Then the "Email" field should contain "a@b.com"      # element value
Then the "Submit" button should be disabled          # enabled/disabled/checked
And the chart line should have attribute "stroke" equal to "green"
And User should see 3 "result" items                 # count
```

### Semantic / visual (requires `BDDFRAME_MODEL`)
```gherkin
Then the checkout form should show a success state
And the screen should look the same as before
And the "header" screen should look the same as before ignoring the navigation
```

### Screenshots
```gherkin
And User takes a screenshot "after-login"
```

---

## 7. Variables & shared state

**Config & secrets** use `[brackets]` and come from `.env`:

```gherkin
When User enters [MY_EMAIL] in the email field      # reads MY_EMAIL
```

**Values captured during the test** use `` `backticks` `` and come from a
per-scenario run store — never `.env`. The two delimiters keep a captured value
visually distinct from a secret:

```gherkin
When User stores the order number as `order`         # capture → run store
And  User enters "`order`" in the reference field     # reuse it later
Then `order` should equal `confirmation`              # compare two captures
```

Other state steps:

```gherkin
When User sets [TAX_RATE] to "0.13"                          # seed a literal
When User stores attribute "data-id" of the row as `id`      # capture an attribute
Then `total` should be greater than "0"                      # numeric/string compare
And  "abc" should contain "b"
```

The principle: **the app computes, the test observes.** BDDFrame stores the app's
output and asserts on it — it never re-implements the app's arithmetic. Variables
reset between scenarios (tests stay independent).

---

## 8. Reports

Requires `[reporting]` installed and `allure` on your PATH.

```bash
bddframe run features/             # 1. produces allure-results/
bddframe report generate           # 2. allure-results/ → allure-report/ (HTML)
bddframe report open               # 3. build + open in a browser
```

> ⚠️ You can't double-click `allure-report/index.html` — it loads data over XHR,
> which browsers block on `file://`. It must be served over HTTP (the commands
> above do that).

| Goal | Command |
|------|---------|
| Build static HTML only (CI artifact) | `bddframe report generate` → `allure-report/` |
| Build + open on a local server | `bddframe report open` |
| One-shot from results (no saved dir) | `allure serve allure-results` |
| Host an already-built report (no Allure CLI) | `python -m http.server 8000 --directory allure-report` |

Keep trends across runs by carrying the history folder forward:

```bash
cp -r allure-report/history allure-results/history 2>/dev/null || true
bddframe run features/
bddframe report generate           # now shows trends
```

**What you see:** overview (pass/fail/skip + trend), suites (feature → scenario →
step), each failed step with error + annotated screenshot, timeline. For *how*
the report is built, see [Architecture → Where the report comes from](architecture.md#6-where-the-report-comes-from).

---

## 9. Recording a test

Rather click through your app than write Gherkin?

```bash
bddframe record --output features/myapp/login.feature --name "Login Flow"
```

A browser opens. Perform the flow. Close it. BDDFrame writes the `.feature` file.
Sensitive values (emails, card numbers, passwords) are auto-detected and replaced
with `[VARIABLE]` placeholders — the real values go in `.env`.

---

## 10. The visual / desktop agent

For UIs with no accessible DOM (desktop apps, Electron, Citrix, legacy web):

```bash
uv pip install -e ".[visual]"
brew install tesseract        # macOS  (apt install tesseract-ocr on Linux)
```

Tag the scenario `@visual` and store reference images in `tests/assets/`:

```gherkin
@visual
Scenario: Upload via file picker
  When I click image "upload_button.png"
  Then I should see text "File picker" on screen
  And I type [FILE_PATH]
  And I press key "enter"
```

It finds targets by OpenCV template match (with DPI-scale variants) → Tesseract
OCR → optional vision LLM (only if `BDDFRAME_VISION_MODEL` is set). Web and visual
steps can mix in one scenario; the orchestrator switches agents per step.

---

## 11. CI — Azure DevOps

Drop-in pipeline files are in the project root: `azure-pipelines.yml` (Linux) and
`azure-pipelines-windows.yml` (Windows).

1. Create a variable group `bddframe-secrets` with your credentials (`BASE_URL`, `MY_EMAIL`, …).
2. Link the pipeline YAML.

Recommended CI defaults: `BDDFRAME_HEADLESS=true` and `BDDFRAME_STRICT_LOCATOR=true`.

What you get:

| Pipeline step | Shows up as |
|---------------|-------------|
| `PublishTestResults@2` (JUnit `allure-results/junit.xml`) | **Run → Tests tab** — native pass/fail dashboard, trends, per-test history |
| `PublishPipelineArtifact@1` (`allure-report`) | **Run → Artifacts → TestReport** — the Allure HTML as a downloadable zip |

The Tests tab is a real dashboard for free. (A *hosted, browsable* Allure
dashboard inside Azure DevOps is not built — the HTML is a downloadable artifact.
The lightest path if you want it is the Allure Azure DevOps marketplace
extension.)

---

## 12. VS Code extension

Syntax highlighting, `[variable]` colouring, step-validation squiggles, and
`@tag` autocomplete.

```bash
uv pip install -e ".[lsp]"
cd vscode-extension && npm install && cd ..
ln -s $(pwd)/vscode-extension ~/.vscode/extensions/bddframe-0.1.0
```

Fully quit VS Code (`Cmd+Q`, not just close the window), then reopen.

**Disable the Cucumber extension for this workspace** — both activate on
`.feature` files and conflict: `Cmd+Shift+X` → search "Cucumber" → right-click
`alexkrechik.cucumberautocomplete` → **Disable (Workspace)** → reload window.

Unknown steps get a yellow squiggle (the LLM may handle them at runtime). Tune it
in `.vscode/settings.json`:

```json
{ "bddframe.unknownStepSeverity": "none" }   // "warning" (default) | "information" | "none"
```

---

## 13. Testing the framework itself

BDDFrame's own suite runs with **no browser, no LLM, and no display**.

```bash
make test                          # == python -m pytest tests/ -v
python -m pytest tests/test_lsp.py -v   # a single file
```

**Expected: 172 passed, 0 failed.** Coverage spans CLI hardening, hooks
lifecycle, step patterns (incl. tables and shared-state), visual patterns,
OpenCV matcher (mocked), Allure writer, JUnit output, screenshot annotation,
recorder + sensitive redaction, LSP validation, page-scoped POM lookup, and
locator ambiguity detection.
</content>
