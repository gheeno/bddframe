# BDDFrame — Getting Started

A complete guide covering what was built, how to install it, and how to write and run your first test against any website.

---

## What was built

BDDFrame is a no-code browser test framework. A QA writes plain-English `.feature` files. The framework handles everything else: finding elements on the page, running the browser, taking screenshots on failure, and producing reports.

### The seven phases, shipped

| Phase | What it does | Key files |
|-------|-------------|-----------|
| 1 — Foundation | behave scaffolding, variable substitution, step resolver | `bddframe/resolver/`, `features/environment.py` |
| 2 — Web Agent | Playwright browser control, self-healing locator, POM YAML, browser tags | `bddframe/agents/web/`, `bddframe/hooks.py` |
| 3 — Hardening | 6 correctness bugs fixed: env passthrough, flag conflicts, browser validation, path resolution, cleanup leaks | `bddframe/cli.py`, `bddframe/hooks.py` |
| 4 — Visual Agent | OpenCV template matching, Tesseract OCR, PyAutoGUI — automate desktop / non-DOM UIs | `bddframe/agents/visual/` |
| 5 — Reporting | Allure JSON per step, annotated failure screenshots (Pillow), JUnit XML for Azure DevOps | `bddframe/reporting/` |
| 6 — Recorder & DevOps | `bddframe record` watches your browser actions and writes the `.feature` file for you; Azure DevOps pipeline YAML included | `bddframe/recorder/`, `azure-pipelines.yml` |
| 7 — Editor (VS Code) | Syntax highlighting, `[variable]` colouring, step validation squiggles, tag autocomplete via pygls LSP | `bddframe/lsp/`, `vscode-extension/` |

**Test coverage**: 125 tests, all passing, none require a real browser.

---

## Installation

### Prerequisites

- Python 3.11 or later
- `pip`
- A Chromium install (handled by Playwright)

### Install

```bash
# Clone the repo
git clone https://github.com/gheeno/bddframe.git
cd bddframe

# Install the package (core deps only — no LLM, no OpenCV)
pip install -e .
playwright install chromium

# OR install everything at once
pip install -e ".[all]"
playwright install chromium
```

### Optional extras

Install only what you need:

```bash
pip install -e ".[llm]"        # LLM step fallback + semantic assertions (needs Ollama or OpenAI)
pip install -e ".[visual]"     # Desktop / visual agent (OpenCV, Tesseract, PyAutoGUI)
pip install -e ".[reporting]"  # Allure reports + JUnit XML
pip install -e ".[lsp]"        # VS Code language server
pip install -e ".[all]"        # Everything above
```

---

## Project layout

```
bddframe/           ← Python package
  cli.py            ← bddframe command
  hooks.py          ← behave lifecycle hooks
  agents/web/       ← Playwright web automation
  agents/visual/    ← OpenCV / PyAutoGUI desktop agent
  recorder/         ← Record tests by watching a browser
  reporting/        ← Allure + JUnit output
  resolver/         ← Step pattern matching
  lsp/              ← VS Code language server

features/           ← Your tests live here
  saucedemo/
    login.feature   ← Example tests
    products.feature
    pom.yaml        ← Element aliases for this feature folder
  pom.yaml          ← Global element aliases
  steps/            ← Auto-wired — do not add to these
  environment.py    ← Hooks entry point — do not modify

.env                ← Credentials and settings (gitignored)
.env.example        ← Template — copy this to .env
```

---

## Quick start — test a website in 5 minutes

### Step 1 — Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` and fill in your values. For the built-in saucedemo demo:

```
SAUCE_USERNAME=standard_user
SAUCE_PASSWORD=secret_sauce
BDDFRAME_HEADLESS=false
```

Any `[variable]` reference in a `.feature` file maps to the matching environment variable (uppercased, spaces → underscores). `[my email]` → `MY_EMAIL`.

### Step 2 — Write a feature file

Create `features/myapp/login.feature`:

```gherkin
Feature: Login

  @web @smoke
  Scenario: Valid user logs in

    Given User is on "https://yourapp.com/login"
    When User enters [MY_EMAIL] in the email field
    And User enters [MY_PASSWORD] in the password field
    And User clicks the login button
    Then User should see "Dashboard"
    And User should have url containing "dashboard"
```

That is all you write. No Python. No selectors. No page objects.

### Step 3 — Run it

```bash
# Run all features
bddframe run

# Run a specific file
bddframe run features/myapp/login.feature

# Run only @smoke scenarios
bddframe run --tag smoke

# Run headless (no visible browser)
bddframe run --headless

# Run with a visible browser (overrides .env)
bddframe run --headed
```

### Step 4 — Read the output

- Failures print a screenshot path immediately: `screenshots/FAILED_<step_name>.png`
- If you have `pip install -e ".[reporting]"`: full Allure report in `allure-report/`
- JUnit XML at `allure-results/junit.xml` for Azure DevOps

---

## How element finding works (no selectors needed)

When a step says `User clicks the login button`, the web agent tries these strategies in order:

1. **Accessibility tree** — role / label / placeholder / text. A *unique* match is used immediately.
2. **Ambiguous** (the label matches 2+ elements) — consult `pom.yaml` for a scoped selector; with none, warn and use the first match (or **fail** under `@strict` / `BDDFRAME_STRICT_LOCATOR`).
3. **Self-heal** — scroll and retry, then first-word partial match.
4. **POM YAML** — page-scoped block → `shared:` → flat keys.
5. **Vision LLM** — only if `BDDFRAME_MODEL` is set; otherwise the step fails with a screenshot.

For most modern web apps, strategy 1 handles everything. You only need POM YAML for elements that have no accessible text (icon buttons, legacy apps) or that are ambiguous. The full picture — including where an LLM does vs does not take over — is in **[Resolution Hierarchy](resolution-hierarchy.md)**.

---

## POM YAML — element aliases (optional)

If an element has no readable text, define an alias in `pom.yaml`:

```yaml
# features/myapp/pom.yaml  (applies to myapp/ feature files only)

burger menu:
  id: react-burger-menu-btn

shopping cart:
  css: ".shopping_cart_link"

search box:
  testid: search-input
```

```yaml
# features/pom.yaml  (applies to ALL feature files)

cookie accept button:
  id: onetrust-accept-btn-handler
```

Then use the alias name in your steps:

```gherkin
When User clicks the burger menu
When User clicks the shopping cart
```

Supported selector types: `css`, `xpath`, `id`, `testid`, `text`, `role`.

---

## Built-in step patterns

These patterns work out of the box. Subject (`User`, `I`, `The user`) is stripped automatically.

### Navigation
```gherkin
Given User is on "https://example.com"
When User navigates to "https://example.com/cart"
When User goes to "https://example.com/checkout"
```

### Filling forms
```gherkin
When User enters "value" in the email field
When User enters [MY_EMAIL] in the email field
When User fills in the username with "admin"
When User clears the search field
```

### Clicking
```gherkin
When User clicks the login button
When User clicks "Submit"
When User clicks the "Proceed to Checkout" link
When User presses the confirm button
```

### Selections and checkboxes
```gherkin
When User selects "Medium" from the size dropdown
When User checks the "Remember me" checkbox
When User unchecks the newsletter checkbox
```

### Waiting
```gherkin
And User waits for the page to load
And User waits until "Order confirmed" appears
And User waits 2 seconds
```

### Scrolling
```gherkin
When User scrolls down
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

---

## Browser and display tags

Add tags to a `Scenario` or `Feature` to control the browser:

| Tag | Effect |
|-----|--------|
| `@web` | Chromium (default) |
| `@headless` | No visible browser window |
| `@headed` | Force visible browser — overrides `--headless` and `.env` |
| `@firefox` | Use Firefox |
| `@webkit` | Use Safari engine |
| `@mobile @iphone` | iPhone 13 emulation |
| `@mobile @android` | Pixel 5 emulation |
| `@slow` | 500 ms delay between actions (debugging) |
| `@record_video` | Record `.webm` to `videos/` |

**Tag priority (highest wins):** `@headed` > `@headless` > `--headed` > `--headless` > `.env`

```gherkin
@headless
Feature: Regression Suite       ← all scenarios headless

  @web @smoke
  Scenario: Standard login       ← headless (inherited)

  @web @headed
  Scenario: Debug this one       ← headed, overrides Feature tag
```

---

## Recording a test (instead of writing it)

If you'd rather click through your app than write Gherkin:

```bash
bddframe record --output features/myapp/checkout.feature --name "Checkout Flow"
```

A browser opens. Perform the flow. Close the browser. BDDFrame writes the `.feature` file.

Sensitive values (emails, card numbers, passwords) are automatically replaced with `[VARIABLE]` placeholders. The real values go in `.env`.

---

## Validate without running

Check that all `.feature` files parse correctly and all `[variables]` are defined — without launching any browser:

```bash
bddframe validate
bddframe validate features/myapp/
```

---

## List all scenarios

```bash
bddframe list
bddframe list features/myapp/
```

---

## Optional: LLM step fallback

If a step doesn't match any built-in pattern, BDDFrame can ask an LLM to interpret it. Add to `.env`:

```
# Local Ollama (free)
BDDFRAME_MODEL=ollama/llama3
BDDFRAME_LLM_URL=http://localhost:11434

# OR hosted OpenAI
BDDFRAME_MODEL=openai/gpt-4o-mini
BDDFRAME_LLM_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-...
```

Then install: `pip install -e ".[llm]"`

The LLM is only called when no built-in pattern matches — most steps never hit it.

---

## Optional: Semantic / visual assertions (requires LLM)

```gherkin
Then the checkout form should show a success state
And the screen should look the same as before
And the "header" screen should look the same as before ignoring the navigation
```

Semantic assertions take a screenshot and ask a vision model whether the assertion is true. They require a vision-capable model:

```
BDDFRAME_VISION_MODEL=ollama/llava
# or
BDDFRAME_VISION_MODEL=openai/gpt-4o
```

---

## Optional: Visual / desktop agent

For apps with no accessible DOM (desktop apps, Electron, Citrix, legacy web):

```bash
pip install -e ".[visual]"
# Also: brew install tesseract   (macOS) or apt install tesseract-ocr (Linux)
```

Tag the scenario `@visual` and use visual steps:

```gherkin
@visual
Scenario: Upload via file picker

  When I click image "upload_button.png"
  Then I should see text "File picker" on screen
  And I type [FILE_PATH]
  And I press key "enter"
```

Store reference images in `tests/assets/`.

---

## Allure reports

Install: `pip install -e ".[reporting]"` and have `allure` on your PATH (`brew install allure` on macOS).

Reports are generated automatically after each run to `allure-report/`. Open the last report:

```bash
bddframe report open
```

Regenerate from existing results:

```bash
bddframe report generate
```

---

## VS Code extension

```bash
pip install -e ".[lsp]"
cd vscode-extension && npm install && cd ..
ln -s $(pwd)/vscode-extension ~/.vscode/extensions/bddframe-0.1.0
```

Fully quit VS Code (`Cmd+Q`), then reopen. You get:

- Gherkin keyword colouring
- `[variable]` highlighted in gold
- Yellow squiggle on steps the LLM will handle at runtime
- `@tag` autocomplete (all supported tags with descriptions)
- `[variable]` autocomplete from your `.env` file

---

## CI — Azure DevOps

Drop-in pipeline files are included at the project root:

- `azure-pipelines.yml` — Linux (Ubuntu, headless)
- `azure-pipelines-windows.yml` — Windows (no Xvfb needed)

Create a variable group called `bddframe-secrets` in Azure DevOps with your credentials (`BASE_URL`, `MY_EMAIL`, etc.), then link the pipeline YAML. Tests run headless, failures upload annotated screenshots as pipeline artifacts, and pass/fail counts appear in Azure Test Plans via the JUnit XML output.

---

## Testing BDDFrame itself

```bash
# Run the full test suite (no browser, no LLM, no display required)
python -m pytest tests/ -v

# Or via Make
make test
```

125 tests, all passing. Tests cover: CLI hardening, hooks lifecycle, step patterns, visual patterns, Allure writer, JUnit output, screenshot annotation, recorder, LSP validation, page-scoped POM lookup, and locator ambiguity detection.
