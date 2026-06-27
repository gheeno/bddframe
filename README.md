# BDDFrame

**QAs write a `.feature` file in plain sentences. BDDFrame does the rest.**

No selectors. No Page Object classes. No step definitions. No code.

---

## Table of contents

1. [How it works](#how-it-works)
2. [Installation](#installation)
3. [Setup — first-time config](#setup--first-time-config)
4. [Write a test](#write-a-test)
5. [Run the tests](#run-the-tests)
6. [View the Allure report](#view-the-allure-report)
7. [Run the unit test suite](#run-the-unit-test-suite)
8. [Browser tags reference](#browser-tags-reference)
9. [Built-in step patterns](#built-in-step-patterns)
10. [POM YAML — element aliases](#pom-yaml--element-aliases)
11. [Variable substitution](#variable-substitution)
12. [Optional — LLM step fallback](#optional--llm-step-fallback)
13. [VS Code extension](#vs-code-extension)
14. [CI — Azure DevOps](#ci--azure-devops)
15. [Docs](#docs)

---

## How it works

```
Your .feature file
      │
      ▼
  behave parses steps
      │
      ▼
  Step resolver — pattern match (no LLM cost)
      │                    │
      │              no match?
      │                    ▼
      │           LLM fallback (opt-in)
      ▼
  Web agent — finds elements by label / role / text
      │
      ▼
  Playwright drives the browser
      │
      ▼
  Allure report — screenshots, pass/fail, JUnit XML
```

1. `behave` parses the `.feature` file into steps
2. The step resolver matches each step against 40+ built-in patterns — no LLM call
3. The web agent locates elements by what they *are* (visible label, ARIA role, text) — no CSS selectors
4. On failure: screenshot is taken, annotated, and embedded in the Allure report
5. Optional: LLM fallback interprets steps that match no built-in pattern

---

## Installation

**Prerequisites:** Python 3.11+, pip

```bash
# Clone
git clone https://github.com/gheeno/bddframe.git
cd bddframe

# Install — core only (no LLM, no OpenCV)
pip install -e .
playwright install chromium

# OR install everything at once
pip install -e ".[all]"
playwright install chromium
```

**Optional extras** — install only what you need:

| Extra | What it adds | Command |
|-------|-------------|---------|
| `llm` | LLM step fallback + semantic assertions | `pip install -e ".[llm]"` |
| `reporting` | Allure reports + JUnit XML | `pip install -e ".[reporting]"` |
| `visual` | Desktop / visual agent (OpenCV, Tesseract, PyAutoGUI) | `pip install -e ".[visual]"` |
| `lsp` | VS Code language server | `pip install -e ".[lsp]"` |
| `all` | Everything above | `pip install -e ".[all]"` |

**Allure CLI** (for viewing reports):

```bash
brew install allure        # macOS
# or: https://allurereport.org/docs/install/
```

---

## Setup — first-time config

Copy the environment template and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and set the credentials for the site you want to test.
The included example uses [saucedemo.com](https://www.saucedemo.com) — a public demo site, credentials are safe to use:

```bash
# .env
SAUCE_USERNAME=standard_user
SAUCE_PASSWORD=secret_sauce
BASE_URL=https://www.saucedemo.com

BDDFRAME_BROWSER=chromium        # chromium | firefox | webkit
BDDFRAME_HEADLESS=false          # true = no visible browser window
BDDFRAME_TIMEOUT=10000           # ms to wait for elements
```

Any `[variable]` in a `.feature` file maps to the matching env var (uppercased, spaces → underscores).
`[sauce username]` → `SAUCE_USERNAME`.

---

## Write a test

Feature files live in `features/`. Create a subfolder per application or domain.

### Example — test your own website

Create `features/myapp/login.feature`:

```gherkin
Feature: Login

  @web @smoke
  Scenario: Valid user can log in

    Given User is on "https://yourapp.com/login"
    When User enters [MY_EMAIL] in the email field
    And User enters [MY_PASSWORD] in the password field
    And User clicks the login button
    Then User should see "Dashboard"
    And User should have url containing "dashboard"
```

Add to `.env`:

```
MY_EMAIL=you@example.com
MY_PASSWORD=yourpassword
```

That is all. No Python. No selectors. No step definitions.

### Included example — saucedemo checkout

`features/saucedemo/checkout.feature` is a complete end-to-end test that ships with BDDFrame:

```gherkin
@headless
Feature: Sauce Demo Checkout

  @web @smoke
  Scenario: User completes a purchase end to end

    Given User is on "https://www.saucedemo.com"
    When User enters [SAUCE_USERNAME] in the username field
    And User enters [SAUCE_PASSWORD] in the password field
    And User clicks the login button
    Then User should see "Products"

    When User clicks "Add to cart"
    Then User should see "1"

    When User clicks the shopping cart
    Then User should have url containing "cart"

    When User clicks "Checkout"
    And User enters "Jane" in the first name field
    And User enters "Doe" in the last name field
    And User enters "12345" in the zip code field
    And User clicks "Continue"
    And User clicks "Finish"
    Then User should see "Thank you for your order!"
```

Run it:

```bash
bddframe run features/saucedemo/checkout.feature
```

### Record a test instead of writing it

Watch your browser actions and let BDDFrame write the file for you:

```bash
bddframe record --output features/myapp/login.feature --name "Login Flow"
```

A browser opens. Click through the flow. Close the browser. The `.feature` file is written automatically.
Sensitive values (email, card number, password) are replaced with `[VARIABLE]` placeholders.

---

## Run the tests

```bash
# Run all features
bddframe run

# Run a specific file
bddframe run features/saucedemo/login.feature

# Run a specific folder
bddframe run features/saucedemo/

# Run only @smoke scenarios
bddframe run --tag smoke

# Run without a visible browser
bddframe run --headless

# Run with a visible browser (overrides .env)
bddframe run --headed

# Use Firefox or WebKit instead of Chromium
bddframe run --browser firefox
bddframe run --browser webkit

# List all discovered scenarios (no browser launched)
bddframe list

# Validate .feature syntax without running
bddframe validate
```

### What to expect

- Pass/fail printed to terminal per scenario
- Screenshot saved to `screenshots/FAILED_<step>.png` on any failure
- If `pip install -e ".[reporting]"` is installed: Allure JSON written to `allure-results/` automatically

---

## View the Allure report

**Requires:** `pip install -e ".[reporting]"` and `allure` on your PATH (`brew install allure`).

### After a run — open the report

```bash
bddframe report open
```

This runs `allure generate allure-results -o allure-report --clean` then `allure open allure-report` and opens a browser tab.

### Manual steps (same result)

```bash
allure generate allure-results -o allure-report --clean
allure open allure-report
```

### What you see in the report

| Section | Content |
|---------|---------|
| Overview | Pass / fail / skip counts, duration, trend chart |
| Suites | Each `.feature` file → each scenario → each step |
| Behaviours | Grouped by Feature name |
| Timeline | When each scenario ran |
| Failed step | Error message + annotated screenshot |
| Step list | Every step highlighted green (pass) or red (fail) |

### Regenerate from existing results

```bash
bddframe report generate
```

---

## Run the unit test suite

BDDFrame's own test suite runs with **no browser, no LLM, and no display** required.

```bash
# Run all tests
python -m pytest tests/ -v

# OR via Make
make test

# Run a specific test file
python -m pytest tests/test_cli_hardening.py -v
python -m pytest tests/test_hooks_hardening.py -v
python -m pytest tests/test_lsp.py -v
python -m pytest tests/test_reporting.py -v
python -m pytest tests/test_recorder.py -v
python -m pytest tests/test_visual_patterns.py -v
python -m pytest tests/test_visual_matcher.py -v
```

**Expected result:** 114 passed, 0 failed.

| Test file | What it covers | Tests |
|-----------|---------------|-------|
| `test_cli_hardening.py` | CLI flags, env var normalisation, browser validation, path resolution | 20 |
| `test_hooks_hardening.py` | Tag conflict warnings, browser validation, cleanup leak prevention | 10 |
| `test_lsp.py` | LSP step validation, KNOWN_TAGS, .env variable completions | 17 |
| `test_reporting.py` | Allure JSON writer, JUnit XML, screenshot annotation | 20 |
| `test_recorder.py` | Recorder navigation/fill/click events, sensitive value redaction | 20 |
| `test_visual_patterns.py` | Visual step pattern matching (18 patterns) | 22 |
| `test_visual_matcher.py` | OpenCV template matching (mocked — no screen access) | 5 |

---

## Browser tags reference

Add tags to a `Scenario` or `Feature` to control the browser. Feature-level tags apply to every scenario in that file.

| Tag | Effect |
|-----|--------|
| `@web` | Chromium (default) |
| `@headless` | No visible browser window |
| `@headed` | Force browser visible — overrides `--headless` and `.env` |
| `@firefox` | Use Firefox |
| `@webkit` | Use Safari engine (WebKit) |
| `@mobile @iphone` | iPhone 13 emulation |
| `@mobile @android` | Pixel 5 emulation |
| `@slow` | 500 ms delay between actions — useful for debugging |
| `@record_video` | Record `.webm` video to `videos/` |

**Priority (highest wins):** `@headed` > `@headless` > `--headed` > `--headless` > `.env`

```gherkin
@headless
Feature: Regression Suite        ← all scenarios run headless

  @web @smoke
  Scenario: Standard login        ← headless (inherited from Feature)

  @web @headed
  Scenario: Debug this one        ← headed, overrides the Feature tag
```

---

## Built-in step patterns

Subject (`User`, `I`, `The user`, `As a user`) is stripped automatically, so all variants work.

### Navigation
```gherkin
Given User is on "https://example.com"
When User navigates to "https://example.com/cart"
When User goes to "https://example.com/checkout"
When User opens "https://example.com"
```

### Forms
```gherkin
When User enters "value" in the email field
When User enters [MY_EMAIL] in the email field
When User fills in the username with "admin"
When User types "hello" into the search box
When User clears the search field
```

### Clicks
```gherkin
When User clicks the login button
When User clicks "Submit"
When User clicks the "Proceed to Checkout" link
When User presses the confirm button
When User taps "Menu"
```

### Dropdowns and checkboxes
```gherkin
When User selects "Medium" from the size dropdown
When User checks the "Remember me" checkbox
When User unchecks the newsletter checkbox
```

### Waiting
```gherkin
And User waits for the page to load
And User waits for the page to fully load
And User waits until "Order confirmed" appears
And User waits until "Spinner" disappears
And User waits 2 seconds
```

### Scrolling
```gherkin
When User scrolls down
When User scrolls up
When User scrolls to "Footer"
```

### Assertions
```gherkin
Then User should see "Products"
Then User should not see "Error"
Then User should have url containing "dashboard"
And the page title should contain "Swag Labs"
```

### Screenshots
```gherkin
And User takes a screenshot "after-login"
```

### Semantic / visual (requires `BDDFRAME_MODEL` in `.env`)
```gherkin
Then the checkout form should show a success state
And the screen should look the same as before
And the "header" screen should look the same as before ignoring the navigation
```

---

## POM YAML — element aliases

If an element has no readable text (icon buttons, legacy apps), define an alias in a `pom.yaml` file.

**Local POM** — `features/myapp/pom.yaml` (applies only to that folder):

```yaml
burger menu:
  id: react-burger-menu-btn

shopping cart:
  css: ".shopping_cart_link"

search box:
  testid: search-input
```

**Global POM** — `features/pom.yaml` (applies to all feature files):

```yaml
cookie accept button:
  id: onetrust-accept-btn-handler

navigation menu:
  role: navigation
```

Then use the alias name naturally in steps:

```gherkin
When User clicks the burger menu
When User clicks the shopping cart
```

Supported selector types: `css`, `xpath`, `id`, `testid`, `text`, `role`

---

## Variable substitution

Any `[variable name]` in a step maps to an environment variable. Lookup rules:
- Uppercased: `[my email]` → `MY_EMAIL`
- Spaces become underscores: `[sauce username]` → `SAUCE_USERNAME`
- Case-insensitive in the feature file

```gherkin
When User enters [MY_EMAIL] in the email field        ← reads MY_EMAIL from .env
When User enters [my email] in the email field        ← same thing
```

Variables are loaded from `.env` first, then from the shell environment (CI pipeline variables work without any changes).

---

## Optional — LLM step fallback

If a step doesn't match any built-in pattern, BDDFrame can ask an LLM to interpret it.
The LLM is **only called when no pattern matches** — most steps never hit it.

```bash
# .env — choose one:

# Local Ollama (free, runs on your machine)
BDDFRAME_MODEL=ollama/llama3
BDDFRAME_LLM_URL=http://localhost:11434

# Hosted OpenAI
BDDFRAME_MODEL=openai/gpt-4o-mini
BDDFRAME_LLM_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-...
```

Then install the LLM extra:

```bash
pip install -e ".[llm]"
```

**Semantic / vision assertions** also require a vision-capable model:

```bash
BDDFRAME_VISION_MODEL=ollama/llava       # local
BDDFRAME_VISION_MODEL=openai/gpt-4o     # hosted
```

---

## VS Code extension

Syntax highlighting, `[variable]` colouring, step validation squiggles, and `@tag` autocomplete.

```bash
pip install -e ".[lsp]"
cd vscode-extension && npm install && cd ..

# Symlink into VS Code extensions
ln -s $(pwd)/vscode-extension ~/.vscode/extensions/bddframe-0.1.0
```

Fully quit VS Code (`Cmd+Q` — not just close the window), then reopen.

**Disable the Cucumber extension for this workspace** — both activate on `.feature` files and conflict:

1. `Cmd+Shift+X` → search "Cucumber"
2. Right-click `alexkrechik.cucumberautocomplete` → **Disable (Workspace)**
3. `Cmd+Shift+P` → **Developer: Reload Window**

**Suppress unknown step warnings** (for steps handled by the LLM at runtime):

```json
// .vscode/settings.json
{
  "bddframe.unknownStepSeverity": "none"
}
```

Options: `"warning"` (default) · `"information"` · `"none"`

---

## CI — Azure DevOps

Drop-in pipeline files are in the project root:

**Linux** — `azure-pipelines.yml`
**Windows** — `azure-pipelines-windows.yml`

Create a variable group called `bddframe-secrets` in Azure DevOps with your credentials (`BASE_URL`, `MY_EMAIL`, etc.), link the pipeline YAML, done.

Tests run headless. Failures upload annotated screenshots as pipeline artifacts. Pass/fail counts appear in Azure Test Plans via the JUnit XML at `allure-results/junit.xml`.

---

## Docs

- [Getting Started](docs/getting-started.md) ← full walkthrough
- [Phase 1 — Foundation](docs/phase-01-foundation.md)
- [Phase 2 — Web Agent](docs/phase-02-web-agent.md)
- [Phase 3 — CLI & Hooks Hardening](docs/phase-03-hardening.md)
- [Phase 4 — Visual / Desktop Agent](docs/phase-04-visual-agent.md)
- [Phase 5 — Reporting](docs/phase-05-reporting.md)
- [Phase 6 — CLI, Recorder & Azure DevOps](docs/phase-06-cli-devops.md)
- [Phase 7 — Syntax Highlighting](docs/phase-07-syntax-highlighting.md)
