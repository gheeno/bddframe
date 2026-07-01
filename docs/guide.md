# Noodle Test Framework — The Complete Guide

Everything a tester needs, in the order you'll need it: install, write your first
test, run it, read the output, then the harder stuff — problematic locators
(`pom.yaml`), shared state, tags, recording, reports, CI, and the editor.

New to *how* it works under the hood? Read **[Architecture](architecture.md)**.
Just want the elevator pitch and copy-paste commands? The
**[README](../README.md)** has them.

---

## Contents

1. [Install](#1-install)
2. [Configure](#2-configure)
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
14. [Custom hooks](#14-custom-hooks)
15. [Writing a custom step](#15-writing-a-custom-step)
16. [Using an LLM — setup, providers, and modes](#16-using-an-llm--setup-providers-and-modes)

---

## 1. Install

**Prerequisites:** Python 3.11+, and [uv](https://docs.astral.sh/uv/) (the
project ships `uv.lock`; plain `pip` also works everywhere below).

```bash
git clone https://github.com/gheeno/noodle.git
cd noodle

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
| `azure` | Azure Key Vault secret loader | `uv pip install -e ".[azure]"` |
| `all` | Everything | `uv pip install -e ".[all]"` |

For reports you also need the **Allure CLI** binary: `brew install allure`
(macOS) / scoop / `npm i -g allure-commandline`.

### Docker (reproducible runner)

A `Dockerfile` based on the official Playwright image (browsers + system deps
preinstalled) runs the whole suite with no local Python setup:

```bash
docker build -t noodle .
docker run --rm noodle                       # default: noodle run features/ --headless
docker run --rm noodle run features/web/busterblock/ --headless
```

`.devcontainer/` opens the same image in VS Code ("Reopen in Container").

### Project layout

```
noodle/             ← the package (cli, hooks, agents, resolver, reporting, llm, lsp)
features/             ← your tests live here
  saucedemo/
    checkout.feature
    pom.yaml          ← element aliases for this folder (optional)
  busterblock/        ← example suite for the bundled test app (needs it running)
    environment/      ← package-scoped .env / secrets.env / environments.yaml (optional)
    preconditions.yaml ← @precondition data fixtures (optional)
    scripts/          ← scripts invoked by "run the script ..." steps
  pom.yaml            ← global element aliases (optional)
  steps/              ← auto-wired catch-all — do not edit
  environment.py      ← hooks entry point — do not edit
test-app/   ← bundled local test app (BusterBlock.ca) — see §4
environments.yaml     ← base URLs per environment ([SAUCEDEMO], [BUSTERBLOCK]) — committed
.env                  ← browser/run settings, NO secrets — committed
secrets.env           ← credentials (gitignored); or use Azure Key Vault
```

---

## 2. Configure

Settings live in **three files by purpose** — base URLs, secrets, and run
settings are kept apart so secrets never sit next to URLs and CI can swap each
independently.

| File | Holds | Committed? |
|------|-------|------------|
| `environments.yaml` | base URLs per environment | ✅ yes (no secrets) |
| `secrets.env` | credentials / tokens — or [Azure Key Vault](#secrets--azure-key-vault) | ❌ gitignored |
| `.env` | browser & run settings | ✅ yes (no secrets) |

```bash
cp .env.example .env                 # run/browser settings
cp secrets.env.example secrets.env   # credentials (then edit)
```

**Base URLs — `environments.yaml`.** Top-level keys become `[KEY]` references:

```yaml
saucedemo: https://www.saucedemo.com
staging:   https://staging.example.com
```

```gherkin
Given User is on "[SAUCEDEMO]"      # → https://www.saucedemo.com
```

**Secrets — `secrets.env`** (gitignored; for CI, prefer
[Key Vault](#secrets--azure-key-vault) or a pipeline variable group):

```bash
SAUCE_USERNAME=standard_user
SAUCE_PASSWORD=secret_sauce
```

**Run settings — `.env`** (no secrets):

```bash
NOODLE_BROWSER=chromium        # chromium | firefox | webkit
NOODLE_HEADLESS=false          # true = no visible window
NOODLE_TIMEOUT=10000           # ms to wait for elements
NOODLE_STRICT_LOCATOR=false    # true = ambiguous locators FAIL (recommended in CI)
NOODLE_RETRIES=1               # re-run a failed scenario N extra times (flaky guard)
NOODLE_PIXEL_THRESHOLD=0.01    # max fraction of changed pixels for "match the baseline"
NOODLE_LOG_LEVEL=INFO          # DEBUG | INFO | WARNING | ERROR
```

**LLM (optional)** — Noodle Test Framework works fully without one. By default no LLM is
called and no AI costs are incurred. To enable, see
**[§16 Using an LLM](#16-using-an-llm--setup-providers-and-modes)** — it covers
every provider, step-by-step setup, and which file each setting goes in.

The short version of what goes in `.env`:

```bash
NOODLE_MODEL=gemini/gemini-1.5-flash   # which LLM to use (free Gemini shown)
NOODLE_LLM_MODE=auto                   # auto (default) or full — see §16
# NOODLE_LLM_URL=...                   # only for Ollama / self-hosted endpoints
# NOODLE_VISION_MODEL=...              # separate model for the @visual agent
```

API keys (never in `.env`) → `secrets.env`.

Any `[variable]` in a `.feature` maps to the matching key, uppercased with spaces
→ underscores: `[sauce username]` → `SAUCE_USERNAME`. **Resolution order, highest
wins:** Key Vault (if configured) → shell / CI variables → `.env` → `secrets.env`
→ `environments.yaml`.

**Per-app overrides.** Any app folder (e.g. `features/web/busterblock/`) can
carry its own `environment/.env`, `environment/secrets.env` and
`environment/environments.yaml` instead of adding keys to the root files —
see **[docs/feature-packages.md](feature-packages.md)** for the full
resolution order and the package layout.

### Secrets — Azure Key Vault

For enterprise CI, pull secrets from a vault instead of `secrets.env`:

```bash
uv pip install -e ".[azure]"
export NOODLE_KEYVAULT_URL=https://my-vault.vault.azure.net/
```

On set, `before_all` authenticates with `DefaultAzureCredential` (a managed
identity on Azure agents; `az login` or env locally), loads **every** secret in
the vault into the environment, and these override other sources. Vault names map
to env keys by dash→underscore + uppercase (`sauce-password` → `SAUCE_PASSWORD`),
since Key Vault names can't contain underscores. Unset the URL → `secrets.env` is
used (the local-dev fallback). Grant the agent identity `get` + `list` on the
vault's secrets.

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

The bundled `features/web/busterblock/` suite is a full worked example organised
by capability — see the README for how to start BusterBlock and run it.

---

## 4. Run it & read the output

```bash
noodle run                                              # all features
noodle run features/web/busterblock/login.feature       # one file
noodle run features/web/busterblock/                    # one folder
noodle run --tag smoke                        # only @smoke scenarios
noodle run --headless                         # no visible browser
noodle run --headed                           # force visible (overrides .env)
noodle run --browser firefox                  # firefox | webkit
noodle run --retries 2                        # re-run a failed scenario up to 2x
noodle run --log-level WARNING                 # quieter output
noodle list                                   # discovered scenarios, no browser
noodle validate                               # parse + check [variables], no browser
```

### Bundled example suites

The repo ships ready-to-run examples under `features/`. One of them drives a
**local** test app, so know what each needs before `noodle run` (no arg) runs
them all:

| Suite | Hits | Needs |
|-------|------|-------|
| `features/web/busterblock/` | the bundled **BusterBlock** app (primary example) | the local app running (below) |
| `features/api/` | `api.restful-api.dev` public REST sandbox | internet |
| `features/terminal/` | canvas terminal (OCR bridge) | `pip install -e ".[visual]"` + tesseract |

**BusterBlock** (`test-app/`) is a self-contained Node/Express VHS-rental
site. The `features/web/busterblock/` suite is organised by framework capability
(one file per capability, tagged for `--tag` filtering). Start it first:

```bash
cd test-app && npm install && npm start   # serves http://localhost:3333
```

Then run all BusterBlock tests or a single capability file:

```bash
noodle run features/web/busterblock/ --headless
noodle run features/web/busterblock/login.feature --headless
noodle run features/web/busterblock/ --tag @smoke --headless
```

Full capability map and credential setup: **[README → BusterBlock](../README.md#busterblock--the-bundled-test-app)**.

**What to expect:**

- Pass/fail printed per scenario.
- On failure: `screenshots/FAILED_<step>.png` (annotated) **+ `traces/<scenario>.zip`** (full Playwright trace — `playwright show-trace traces/<scenario>.zip`).
- If a locator self-healed: `healing.jsonl` + `healing-report.txt` with `pom.yaml` suggestions.
- With `[reporting]` installed: Allure JSON written to `allure-results/` automatically.

### Flaky tests — retries & quarantine

Failed scenarios are retried once by default (`NOODLE_RETRIES`, or `--retries`).
Retries fire **only on failure**, so green scenarios cost nothing.

| Tag | Effect |
|-----|--------|
| `@no_retry` | Never retry this scenario (e.g. a known-failing assertion you're asserting *does* fail) |
| `@quarantine` | Still runs, but its failure is **non-blocking** — the build stays green. `noodle run` exits 0 if every failure this run is quarantined. |

Use `@quarantine` to keep a newly-flaky test visible in reports without blocking
the pipeline while you fix it.

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

1. **Make CI strict** — `@strict` tag or `NOODLE_STRICT_LOCATOR=true`. The step
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
5. Vision LLM (only if NOODLE_MODEL is set; else the step fails)
```

Full picture, including the LLM boundary: [Architecture → Resolution hierarchy](architecture.md#4-the-resolution-hierarchy).

### Shadow DOM, SVG & containers

- **Shadow DOM** — Playwright's `css`/`role`/`text`/`id`/`testid` engines pierce *open* shadow DOM automatically, so web-component pages mostly "just work." **Avoid `xpath` POM selectors on shadow-DOM pages — XPath does not cross shadow boundaries.** *Closed* shadow DOM is reachable only by the vision LLM.
- **SVG** — real DOM, so it's targetable. An SVG with `<title>` or `role="img"` + `aria-label` resolves by name; otherwise treat it like an icon-only button (a `css`/`testid` POM entry).
- **Containers** — scope with a row/section step (below) or a scoped `pom.yaml` page-block; don't bake container paths into the sentence.

---

## 6. Built-in step reference

50+ patterns work out of the box. Subject is stripped automatically.

### Navigation
```gherkin
Given User is on "https://example.com"
When User navigates to "https://example.com/cart"
When User goes to "https://example.com/checkout"
When User opens "https://example.com"
Given User is on the "results" page          # pin a POM page (SPAs)
When User goes back                           # browser history
When User goes forward
When User reloads the page                    # or: refreshes the page
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
When User selects "Action" in the genre filter  # "in" or "from"
When User submits the login form                 # clicks the form's submit control
```

### Clicks, keyboard & hover
```gherkin
When User clicks the login button
When User clicks "Submit"
When User clicks the "Proceed to Checkout" link
When User presses the confirm button          # a click
When User taps "Menu"
When User double-clicks "Jaws"                 # dblclick
When User right-clicks "File"                  # context-menu click
When User presses Enter                        # a keyboard key
When User hovers over the "Account" menu
```

### Tabs & windows
```gherkin
When User clicks "Preview"                     # opens a new tab
Then a new tab should open                      # asserts + focuses the new tab
And User should see "Details" in the new tab    # any step + " in the new tab"
When User switches to the previous tab          # new / previous / original / first
When User closes the tab
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
And User should see 3 "result" items                 # count (visible only)
```

> Count assertions count **visible** occurrences — sr-only/aria duplicates and
> tooltip text are excluded, so "should see 3 X" reflects what a user actually
> sees on screen.

### Visual regression — deterministic (no LLM)
Pixel diff against a stored baseline. First run captures `baselines/<name>.png`;
later runs fail if more than `NOODLE_PIXEL_THRESHOLD` (default 1%) of pixels
changed, saving `screenshots/DIFF_<name>.png` as evidence.
```gherkin
Then the screen should match the baseline
Then the "checkout" screen should match the baseline
```

### Semantic / visual — LLM (requires `NOODLE_MODEL`)
```gherkin
Then the checkout form should show a success state
And the screen should look the same as before
And the "header" screen should look the same as before ignoring the navigation
```

### Network mocking
Intercept requests via Playwright routing — decouple a test from a flaky/slow/
absent backend, or silence third-party noise.
```gherkin
When User mocks "**/api/cart" with status 200 and body '{"items":[]}'
When User mocks "**/api/checkout" with status 500
When User blocks requests to "**/analytics/**"
```

### API setup / teardown
Hit an endpoint directly (Playwright's request context — shares browser cookies),
e.g. to seed or clean data without driving the UI. Fails on a non-2xx response.
```gherkin
Given User calls POST "https://api.test/seed" with body '{"user":"bob"}'
And   User calls GET "https://api.test/reset"
```

### Test-data fixtures
Load a YAML/JSON mapping into the run-scoped variable store, then reference the
keys as `` `backtick` `` captures.
```gherkin
Given User loads test data from "fixtures/users.yaml"
When  User enters "`username`" in the username field
```

### Running scripts & commands
Invoke any external script (py/js/jar/sh/…) or shell command as a step — seed a
DB, run a jar, call a CLI tool. Interpreter inferred from the extension; a
non-zero exit **fails the step**. stdout is captured into `` `SCRIPT_OUTPUT` ``
(and any var you name), so a later step can assert on it. `[VAR]` refs in the
path/args/command are substituted from config first. Timeout:
`NOODLE_SCRIPT_TIMEOUT` (default 60s).
```gherkin
Given the script "scripts/seed_db.py" runs
And   `SCRIPT_OUTPUT` should contain "seeded 42 rows"
Given User runs the script "tool.jar" with "--env staging" storing the output as `RESULT`
Given User runs the command "java -jar tool.jar [BUSTERBLOCK]"
```
> Feature files are trusted code (like step definitions) — `run the command` uses
> a shell. Don't drive these steps from untrusted input. Full guide: README →
> "Run a script from a step".

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

The principle: **the app computes, the test observes.** Noodle Test Framework stores the app's
output and asserts on it — it never re-implements the app's arithmetic. Variables
reset between scenarios (tests stay independent).

---

## 8. Reports

Requires `[reporting]` installed and `allure` on your PATH.

```bash
noodle run features/             # 1. produces allure-results/
noodle report generate           # 2. allure-results/ → allure-report/ (HTML)
noodle report open               # 3. build + open in a browser
```

> ⚠️ You can't double-click `allure-report/index.html` — it loads data over XHR,
> which browsers block on `file://`. It must be served over HTTP (the commands
> above do that).

| Goal | Command |
|------|---------|
| Build static HTML only (CI artifact) | `noodle report generate` → `allure-report/` |
| Build + open on a local server | `noodle report open` |
| One-shot from results (no saved dir) | `allure serve allure-results` |
| Host an already-built report (no Allure CLI) | `python -m http.server 8000 --directory allure-report` |

Keep trends across runs by carrying the history folder forward:

```bash
cp -r allure-report/history allure-results/history 2>/dev/null || true
noodle run features/
noodle report generate           # now shows trends
```

**What you see:** overview (pass/fail/skip + trend), suites (feature → scenario →
step), each failed step with error + annotated screenshot, timeline. For *how*
the report is built, see [Architecture → Where the report comes from](architecture.md#6-where-the-report-comes-from).

### Failure traces (Playwright)

Every **failed** scenario also captures `traces/<scenario>.zip` — a full
Playwright trace with DOM snapshots, network log, console, and a frame-by-frame
timeline. It's discarded on pass (green runs cost no disk). Open it:

```bash
playwright show-trace traces/<scenario>.zip
```

In CI it's published as a `Traces-*` pipeline artifact (on failure only). This is
the headline debugging edge over Selenium/Selenide — time-travel through the run
instead of guessing from a log.

### Healing telemetry

When the locator layer resolves something by a non-primary path (scroll/partial-
text self-heal, POM disambiguation, vision-LLM locate), it's recorded. At end of
run, if anything healed, Noodle Test Framework writes `healing.jsonl` (one event per line) and
`healing-report.txt` with a suggested `pom.yaml` entry per healed locator — turn a
flaky-by-naming locator into a one-line deterministic fix.

### Agentic RCA — automatic failure root-cause

Telemetry tells you *what* healed; RCA tells you *why a failure happened*. Enable
it with a vision model plus the opt-in flag:

```bash
# .env
NOODLE_MODEL=openai/gpt-4o     # vision-capable
NOODLE_RCA=true
```

On **each failed step**, Noodle Test Framework sends the failure screenshot + step text +
error to the model and gets back a structured verdict. It's logged to the console
and attached to the Allure result as the `rca_category` label, so you can filter
the report by root cause:

| `rca_category` | Meaning |
|----------------|---------|
| `app-regression` | The UI changed or a feature is broken |
| `locator-rot` | The element's label or structure changed |
| `environment-flap` | Network, timeout, or infra issue |
| `test-data` | Missing, stale, or wrong seed data |
| `test-script` | The step or assertion itself is wrong |

```
🔍 RCA [environment-flap] (medium): the page never finished loading before the assertion
💡 Suggested fix: add a "wait until ... is visible" step or raise NOODLE_TIMEOUT
```

RCA is **best-effort**: it never changes a test's pass/fail and never raises, and
it fires only on failure (one model call per failed step — green runs cost
nothing). Off unless both `NOODLE_MODEL` and `NOODLE_RCA` are set. It pairs
with [failure traces](#failure-traces-playwright): the trace shows the *what*, RCA
suggests the *why*.

---

## 9. Recording a test

Rather click through your app than write Gherkin?

```bash
noodle record --output features/myapp/login.feature --name "Login Flow"
```

A browser opens. Perform the flow. Close it. Noodle Test Framework writes the `.feature` file.
Sensitive values (emails, card numbers, passwords) are auto-detected and replaced
with `[VARIABLE]` placeholders — the real values go in `.env`.

---

## 10. The visual / desktop agent

For UIs with no accessible DOM (desktop apps, Electron, Citrix, legacy web):

```bash
uv pip install -e ".[visual]"
brew install tesseract        # macOS  (apt install tesseract-ocr on Linux)
```

Tag the scenario `@visual` and store reference images where the run can reach
them (e.g. an `assets/` folder; the path in the step is relative to the run dir):

```gherkin
@visual
Scenario: Upload via file picker
  When I click image "upload_button.png"
  Then I should see text "File picker" on screen
  And I type [FILE_PATH]
  And I press key "enter"
```

It finds targets by OpenCV template match (with DPI-scale variants) → Tesseract
OCR → optional vision LLM (only if `NOODLE_VISION_MODEL` is set). Web and visual
steps can mix in one scenario; the orchestrator switches agents per step.

---

## 11. CI — Azure DevOps

Drop-in pipeline files are in the project root: `azure-pipelines.yml` (Linux) and
`azure-pipelines-windows.yml` (Windows).

1. Create a variable group `noodle-secrets` with your credentials (`BASE_URL`, `MY_EMAIL`, …).
2. Link the pipeline YAML.

Recommended CI defaults: `NOODLE_HEADLESS=true` and `NOODLE_STRICT_LOCATOR=true`.

What you get:

| Pipeline step | Shows up as |
|---------------|-------------|
| `PublishTestResults@2` (JUnit `allure-results/junit.xml`) | **Run → Tests tab** — native pass/fail dashboard, trends, per-test history |
| `PublishPipelineArtifact@1` (`allure-report`) | **Run → Artifacts → TestReport** — the Allure HTML as a downloadable zip |
| `PublishPipelineArtifact@1` (`traces`, on failure) | **Run → Artifacts → Traces-*** — Playwright traces for failed scenarios |

The Tests tab is a real dashboard for free. (A *hosted, browsable* Allure
dashboard inside Azure DevOps is not built — the HTML is a downloadable artifact.
The lightest path if you want it is the Allure Azure DevOps marketplace
extension.)

### Parallel execution (sharding)

behave is single-process, so Noodle Test Framework parallelizes by **sharding feature folders
across agents**. The pipeline uses a matrix — one agent per folder — and each shard
publishes its own `junit.xml`; the Tests tab aggregates them into one run:

```yaml
jobs:
  - job: tests
    strategy:
      maxParallel: 4
      matrix:
        busterblock:  { featurePath: 'features/web/busterblock/' }
        api:          { featurePath: 'features/api/' }
    steps:
      - script: noodle run $(featurePath) --headless
      # ... PublishTestResults / artifacts per shard
```

Add a matrix row per feature folder to scale out. Because a run rewrites
`allure-results/`, each shard must have its own workspace — which separate agents
do automatically. (No in-process worker pool; add agents, not threads.)

#### Data isolation across shards

Separate agents get separate *workspaces*, **not** separate *backends*. Two
shards that seed the same test server race: if both call
`POST [BUSTERBLOCK]/api/test/reset` ([preconditions](architecture.md#2-the-component-map)),
one shard's reset wipes the other's state mid-run. Two ways to keep shards
independent:

1. **Backend per shard** (cleanest) — give each shard its own server instance /
   database via the variable group, e.g. set `BUSTERBLOCK` to a per-shard URL in
   the matrix:

   ```yaml
   matrix:
     busterblock_1: { featurePath: 'features/web/busterblock/', BUSTERBLOCK: 'http://bb-1:3333' }
     busterblock_2: { featurePath: 'features/web/busterblock/', BUSTERBLOCK: 'http://bb-2:3333' }
   ```

2. **Namespaced fixtures** — if the backend supports it, seed into a per-shard
   slot instead of a global reset (e.g. key test data by the shard's job name) so
   no two shards touch the same records. This needs the app to support scoped
   resets; the bundled BusterBlock uses a single global store, so prefer option 1
   for it.

The safe default: shard so that no two folders hit the same backend, or run each
against its own instance.

### Secrets via Key Vault

Instead of putting credentials in the variable group, set `NOODLE_KEYVAULT_URL`
and grant the pipeline's service connection / managed identity `get` + `list` on
the vault. Install the extra (`pip install -e ".[azure]"`, included in `[all]`)
and Noodle Test Framework loads the vault at startup. See [Configure → Secrets](#secrets--azure-key-vault).

---

## 12. VS Code extension

Syntax highlighting, `[variable]` colouring, step-validation squiggles, and
`@tag` autocomplete.

```bash
uv pip install -e ".[lsp]"
cd vscode-extension && npm install && cd ..
ln -s $(pwd)/vscode-extension ~/.vscode/extensions/noodle-0.1.0
```

Fully quit VS Code (`Cmd+Q`, not just close the window), then reopen.

**Disable the Cucumber extension for this workspace** — both activate on
`.feature` files and conflict: `Cmd+Shift+X` → search "Cucumber" → right-click
`alexkrechik.cucumberautocomplete` → **Disable (Workspace)** → reload window.

Unknown steps get a yellow squiggle (the LLM may handle them at runtime). Tune it
in `.vscode/settings.json`:

```json
{ "noodle.unknownStepSeverity": "none" }   // "warning" (default) | "information" | "none"
```

---

## 13. Testing the framework itself

Noodle Test Framework's own suite runs with **no browser, no LLM, and no display**.

```bash
make test                               # == python -m pytest unit_tests/ -v
python -m pytest unit_tests/test_lsp.py -v   # a single file
```

**Expected: 314 passed, 0 failed.** Coverage spans CLI hardening, hooks
lifecycle, step patterns (incl. tables and shared-state), visual patterns,
OpenCV matcher (mocked), Allure writer, JUnit output, screenshot annotation,
recorder + sensitive redaction, LSP validation, page-scoped POM lookup, locator
ambiguity detection, and the enterprise additions — deterministic pixel diff,
quarantine exit-code scan, healing telemetry, Key Vault merge, the
mock/API/test-data steps, **data preconditions/teardowns, the script/command
runner, and the custom hook registry**.

---

## 14. Custom hooks

Custom hooks let you inject cross-cutting behaviour — timing, session tracking,
extra logging, tag-conditional setup — without touching your `.feature` files or
the framework internals. They mirror Cucumber's `Before`/`After` hooks.

### How to register a hook

Create any `*.py` file in `features/steps/` and use the `@hook` decorator:

```python
# features/steps/custom_hooks.py
import time, uuid
from noodle.hooks import hook
from noodle.log import logger

@hook("before_scenario")
def assign_session(context, scenario):
    context.session_id = str(uuid.uuid4())[:8]
    context._start = time.monotonic()

@hook("after_scenario")
def log_timing(context, scenario):
    elapsed = time.monotonic() - getattr(context, "_start", 0)
    status = "PASSED" if "passed" in str(scenario.status) else "FAILED"
    logger.info(f"\n  🪝 [{context.session_id}] {scenario.name} — {status} ({elapsed:.1f}s)")
    if "audit" in scenario.effective_tags:
        logger.info(f"\n  📋 AUDIT: {scenario.feature.name} / {scenario.name}")
```

behave auto-loads every `*.py` in `features/steps/`, so the hooks register
before any scenario runs. The `@hook` decorator is the only API you need.

### Supported events

| Event | Fires | Arguments |
|---|---|---|
| `before_all` | once, before the suite | `(context,)` |
| `before_feature` | once per feature file | `(context, feature)` |
| `before_scenario` | before each scenario | `(context, scenario)` |
| `after_step` | after each step | `(context, step)` |
| `after_scenario` | after each scenario | `(context, scenario)` |
| `after_all` | once, after the suite | `(context,)` |

Alternatively, call `register(event, fn)` directly (no decorator):

```python
from noodle.hooks import register
register("after_all", lambda ctx: print("suite done"))
```

### Execution order within each event

- **`before_*`** — framework setup runs first (browser is already open), then your hook. `context.page` is available.
- **`after_scenario`** — your hook runs first (page is still open), then data teardown, then browser close.
- **`after_all`** — your hook runs first, then the Allure/JUnit report is generated.
- Multiple hooks for the same event fire in registration order (first registered, first called).

### `before_all` — one timing constraint

`before_all` fires before behave loads step files, so a `@hook("before_all")`
placed in a file under `features/steps/` will **not** run — the file hasn't
been imported yet. Register `before_all` hooks in `features/environment.py`
instead:

```python
# features/environment.py
from noodle.hooks import before_all, ..., register

def my_before_all(context):
    context.suite_start = time.monotonic()

register("before_all", my_before_all)
```

All other events are safe to register from step files.

### Demo

`features/web/busterblock/hooks.feature` shows hooks in action against
BusterBlock. The `@audit` tag triggers an extra log line from the
`after_scenario` hook — no change to the feature file required:

```gherkin
@smoke @audit
Scenario: Catalog is visible and the run is audit-logged
  Then User should see "VHS Catalog"
  And User should see "Jaws"
```

Terminal output when `custom_hooks.py` is loaded:

```
  🪝 [a3f1bc2e] Catalog is visible and the run is audit-logged — PASSED (1.2s)
  📋 AUDIT: Hooks demo — cross-cutting behaviour via custom hooks / Catalog is visible and the run is audit-logged
```

### Tag-conditional hooks

Hooks receive the full `scenario` object, so any tag-based branching is plain
Python — no special syntax:

```python
@hook("before_scenario")
def maybe_seed(context, scenario):
    if "needs_admin" in scenario.effective_tags:
        context.admin_token = fetch_admin_token()
```

---

## 15. Writing a custom step

### How Noodle Test Framework resolves a step

Every step goes through two tiers:

1. **Pattern match** — `noodle/resolver/patterns.py` is tried first. A regex
   match returns an action dict immediately; no model is invoked.
2. **LLM fallback** — if no pattern matches *and* `NOODLE_MODEL` is set, the
   step text is sent to the configured model. Without `NOODLE_MODEL` the run
   fails with a clear "add a pattern" message.

The VS Code extension (LSP) shows an inline warning on any step that would fall
through to tier 2:

```
No built-in pattern matched — LLM will resolve at runtime.  [llm-fallback]
```

### What to do when you see that warning

**Option A — add a pattern (preferred)**

Open `noodle/resolver/patterns.py` and append an entry to `PATTERNS`:

```python
# My new verb
(r'^verifies? (?:that )?(.+?) (?:is|are) displayed?$',
                                               'assert_visible', lambda m: {'text': _q(m.group(1))}),
```

The tuple is `(regex, action_type, param_extractor)`. Patterns are matched
top-to-bottom; first match wins. Regex is anchored (`^…$`) and
case-insensitive.

Pick the closest existing `action_type` — you rarely need a new one. The full
list is in `noodle/resolver/step_resolver.py::VALID_TYPES`.

After adding the pattern, save the file. The LSP re-validates open `.feature`
files immediately and the warning disappears. No restart needed.

**Option B — accept LLM fallback**

If the step is intentionally vague (e.g. exploratory tests, legacy steps you
haven't cleaned up yet), you can silence the warning by adding `# llm-ok` at
the end of the step line:

```gherkin
When User authenticates on the sample application  # llm-ok
```

The LSP skips validation for lines marked `# llm-ok`. The step still falls
through to the LLM at runtime — the comment is only a suppression directive for
the editor warning.

> Only use `# llm-ok` for steps that you have consciously decided to leave
> LLM-resolved. A pattern in `patterns.py` is always faster (no model round
> trip) and more deterministic.

### Pattern authoring tips

| Goal | Technique |
|------|-----------|
| Optional words ("the", "a") | `(?:the\s+)?` |
| Singular or plural verb | `verifies?` |
| Capture a quoted string | `'([^']+)'` or `["\'](.+?)["\']` |
| Strip surrounding quotes | wrap with `_q(m.group(n))` |
| Accept a backtick variable | `[\[` + `` ` `` + `]([^\]` + `` ` `` + `]+)[\]` + `` ` `` + `]` (see `set_var` pattern) |
| Action targets a variable already substituted | variables are expanded *before* `resolve()` is called, so the pattern sees the final value |

### Testing your pattern

```bash
python3 -c "
from noodle.resolver.patterns import match, normalize_subject
step = 'verifies that the cart is displayed'
print(match(normalize_subject(step)))
"
```

A `None` result means the pattern didn't match. Check anchoring and quoting.

### Checklist before you push

- [ ] Pattern added to `noodle/resolver/patterns.py`
- [ ] `VALID_TYPES` in `step_resolver.py` updated if you added a new `action_type`
- [ ] Runner (`orchestrator/runner.py`) handles the new action type in `execute_step`
- [ ] LSP warning gone in VS Code
- [ ] Quick smoke: `python3 -c "from noodle.resolver.patterns import match, normalize_subject; print(match(normalize_subject('your step text')))"` returns the expected action

---

## 16. Using an LLM — setup, providers, and modes

This section is written for someone who has never used an AI model or agent before.
No prior knowledge assumed.

### What is an LLM and why would I use one here?

An **LLM** (Large Language Model) is the same technology behind ChatGPT and Claude.
It can read plain English and interpret it.

Noodle Test Framework uses an LLM in two specific situations:

1. **A step phrase has no matching pattern.** Noodle Test Framework has 50+ built-in step
   patterns (`clicks the X button`, `enters Y in the Z field`, etc.). If you write
   a step that doesn't match any of them, the LLM can read your sentence and figure
   out what action to run. Without an LLM, the test would simply fail with a "no
   pattern matched" error.

2. **An element can't be found on the page.** If Noodle Test Framework can't locate a button or
   field by its label, the LLM can look at a screenshot and find it visually.
   Without an LLM, the test would fail with a "could not find element" error.

**You do not need an LLM to use Noodle Test Framework.** The default setup is fully local and
deterministic — no AI calls, no cost, no internet. Most test suites work perfectly
without it.

---

### Default behaviour — no LLM

Out of the box, with no configuration, Noodle Test Framework:

- Uses regex patterns to understand steps (fast, free, deterministic)
- Uses Playwright's accessibility tree to find elements on the page
- **Never makes any AI or LLM calls**
- Fails loudly (with a screenshot) if a step or element can't be resolved locally

This is the recommended default for CI pipelines and regression suites.

---

### How to enable an LLM — the two things you set

You need to set exactly two things:

| What | Which file | Variable |
|------|-----------|---------|
| Which LLM to use | `.env` | `NOODLE_MODEL` |
| Your API key (for cloud providers) | `secrets.env` | Provider-specific (e.g. `ANTHROPIC_API_KEY`) |

That's it. No code changes. No restarts.

> **Why two different files?**
> `.env` is committed to git — it's safe for settings but not secrets.
> `secrets.env` is gitignored — it's where passwords and API keys go.
> Putting your API key in `.env` would commit it to version control, which is a
> security risk. Always put keys in `secrets.env`.

---

### Step-by-step: pick a provider and turn it on

#### Option A — Free: Google Gemini (recommended for getting started)

Gemini has a free tier that requires no credit card. It is vision-capable, meaning
it can both interpret steps AND find elements on screen by looking at screenshots.

1. Go to [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) and create a free API key.

2. Open `secrets.env` and add:
   ```bash
   GEMINI_API_KEY=your-key-here
   ```

3. Open `.env` and add:
   ```bash
   NOODLE_MODEL=gemini/gemini-1.5-flash
   ```

4. Install the LLM extra (once):
   ```bash
   uv pip install -e ".[llm]"
   ```

5. Run your tests as normal. Noodle Test Framework will now use Gemini as a fallback for
   steps and elements it can't resolve locally.

---

#### Option B — Free and fast: Groq (text only — no screenshots)

Groq is a free hosted service that runs open-source models at high speed.
It is **text-only** — it can interpret step phrases but cannot look at screenshots
to find elements. Good for step fallback, not for visual location.

1. Create a free account at [https://console.groq.com](https://console.groq.com) and generate an API key.

2. Open `secrets.env` and add:
   ```bash
   GROQ_API_KEY=your-key-here
   ```

3. Open `.env` and add:
   ```bash
   NOODLE_MODEL=groq/llama-3.1-8b-instant
   ```

4. Install the LLM extra (once):
   ```bash
   uv pip install -e ".[llm]"
   ```

---

#### Option C — Paid: Anthropic Claude (best quality, vision-capable)

Claude is a paid service but has low per-call cost and is vision-capable.

1. Create an account at [https://console.anthropic.com](https://console.anthropic.com), add a payment method, and create an API key.

2. Open `secrets.env` and add:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```

3. Open `.env` and add:
   ```bash
   NOODLE_MODEL=anthropic/claude-sonnet-4-6
   ```

4. Install the LLM extra (once):
   ```bash
   uv pip install -e ".[llm]"
   ```

---

#### Option D — Local: Ollama (no internet, no account, no cost)

Ollama runs a model on your own machine. Nothing leaves your computer.
Requires a machine with a reasonable amount of RAM (8 GB+ recommended).

1. Install Ollama from [https://ollama.com](https://ollama.com).

2. Download a model (run this once in a terminal):
   ```bash
   ollama pull llama3          # text only
   ollama pull llava           # vision-capable (also installs llama3)
   ```

3. Open `.env` and add (no API key needed, no `secrets.env` change):
   ```bash
   NOODLE_MODEL=ollama/llava        # vision-capable
   NOODLE_LLM_URL=http://localhost:11434
   ```

4. Make sure Ollama is running before you run tests (`ollama serve` or the desktop app).

---

### Provider comparison

| Provider | Cost | Vision? | Internet needed? | Best for |
|----------|------|---------|-----------------|---------|
| **Google Gemini** | Free tier | ✅ | Yes | Getting started, no cost |
| **Groq** | Free tier | ❌ | Yes | Fast step fallback only |
| **Anthropic Claude** | Pay per use | ✅ | Yes | Best quality |
| **OpenAI GPT** | Pay per use | ✅ gpt-4o | Yes | Familiar option |
| **Ollama (local)** | Free | ✅ with llava | No | Air-gapped, private data |
| **Foundry Local** | Free | model-dependent | No | Locked-down corporate networks |

**"Vision-capable"** means the model can look at a screenshot. Noodle Test Framework uses this
when an element can't be found by its label — it takes a screenshot, sends it to
the model, and asks "where is the Login button?". Without vision capability, only
step-text fallback works (the model reads words but not images).

---

### The mode toggle — `auto` vs `full`

`NOODLE_LLM_MODE` controls when the LLM is called. Edit this in `.env`.

#### `auto` (default — LLM as backup only)

```bash
# .env
NOODLE_LLM_MODE=auto     # this is the default; you can leave this line out entirely
```

Noodle Test Framework tries to resolve everything locally first:
- Step text → matched against 50+ built-in patterns (fast, free)
- If no pattern matches → asks the LLM
- Element location → scanned by Playwright's accessibility tree (fast, free)
- If element not found → asks the LLM (vision)

Most steps never touch the LLM at all. The LLM is only the last resort.
**Recommended for CI and regression suites.**

#### `full` (LLM resolves every single step)

```bash
# .env
NOODLE_LLM_MODE=full
```

Noodle Test Framework skips all pattern matching and accessibility scanning. Every step and
every element location goes directly to the LLM. This is slower and costs more
per test run, but it lets you write completely free-form test steps without
worrying about whether they match a pattern.

**Requires `NOODLE_MODEL` to be set.** `full` mode with no model is an error.

**Requires a vision-capable model** for element location (Google Gemini, Claude,
OpenAI gpt-4o, Ollama llava). With a text-only model (Groq, llama3) in `full`
mode, Noodle Test Framework will warn you and fall back to the accessibility tree for elements.

**Recommended for:** exploratory testing, legacy app automation, writing tests
without learning the step vocabulary first.

---

### Quick reference — what goes where

```
.env                          ← edit this for model and mode settings (committed to git)
  NOODLE_MODEL=...
  NOODLE_LLM_MODE=...
  NOODLE_LLM_URL=...        ← only for Ollama / Foundry Local / self-hosted

secrets.env                   ← edit this for API keys (gitignored — never committed)
  ANTHROPIC_API_KEY=...
  GEMINI_API_KEY=...
  GROQ_API_KEY=...
  OPENAI_API_KEY=...
```

### Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `No pattern matched` error with no model set | LLM not enabled | Add `NOODLE_MODEL` to `.env` |
| `NOODLE_LLM_MODE=full but NOODLE_MODEL is not set` | Full mode needs a model | Add `NOODLE_MODEL` to `.env` |
| `LLM support requires: pip install noodle[llm]` | Extra not installed | Run `uv pip install -e ".[llm]"` |
| `AuthenticationError` or `401` | Wrong or missing API key | Check `secrets.env` for the right key name |
| Vision-locate warning: `is NOODLE_MODEL vision-capable?` | Text-only model used with full mode | Switch to a vision-capable model (see table above) or use `auto` mode |
| Ollama: `ConnectionRefused` | Ollama not running | Run `ollama serve` in a terminal first |
</content>
