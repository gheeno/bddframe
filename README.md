# BDDFrame

**QAs write a `.feature` file in plain sentences. BDDFrame does the rest.**

No selectors. No Page Object classes. No step definitions. No code.

---

## What a QA writes

```gherkin
Feature: Guest Checkout

  @web @smoke
  Scenario: Customer completes a purchase with a valid card
    Given User is on "https://staging.myshop.com"
    When User enters [MY_EMAIL] in the email field
    And User enters [MY_CARD_NUMBER] in the card details
    And User clicks the Place Order button
    Then User should see "Thank you for your order"
    And the screen should look the same as before
```

That is the only file the QA touches. No Python. No YAML. No XPath.

---

## How it works

1. **`behave` parses** the `.feature` file into steps
2. **Step resolver** matches each step against built-in patterns (no LLM cost)
3. **Web agent** finds elements by what they *are* (label, role, text) — not by CSS selector
4. **Self-healing** kicks in when an element isn't found: scroll, partial match, then vision LLM
5. **LLM fallback** interprets steps that don't match any pattern (opt-in via `BDDFRAME_MODEL`)
6. **Allure report** shows pass/fail with annotated screenshots of exactly what went wrong

---

## Stack (all open source)

| Layer | Tool | License |
|-------|------|---------|
| BDD parsing | `behave` | BSD |
| LLM gateway | `LiteLLM` | MIT |
| Local LLM | `Ollama` + `llama3` / `llava` | MIT |
| Web automation | `Playwright` | Apache 2.0 |
| Visual/desktop | `OpenCV` + `PyAutoGUI` | Apache 2.0 / BSD |
| Mobile | `Appium` | Apache 2.0 |
| Reporting | `Allure` | Apache 2.0 |
| Screenshot annotation | `Pillow` | HPND |

---

## Quick start

```bash
pip install -e ".[all]"
playwright install chromium

# Run all features
bddframe run

# Run a specific feature file (any path convention works)
bddframe run features/saucedemo/login.feature
bddframe run login.feature

# Run by tag
bddframe run --tag smoke

# Run headless (no browser window)
bddframe run --headless

# Run headed (browser visible — overrides .env and --headless)
bddframe run --headed

# Validate feature files without launching a browser
bddframe validate
```

---

## Variable substitution

`[MY_EMAIL]` in a step maps to `MY_EMAIL` in `.env` or CI pipeline variables. Square brackets are the universal convention — lowercase with spaces also works (`[my email]` → `MY_EMAIL`).

```bash
# .env  (copy from .env.example — gitignored)
MY_EMAIL=test@example.com
SAUCE_USERNAME=standard_user
BASE_URL=https://staging.myshop.com
```

---

## Browser tags

Tags on a `Scenario` (or `Feature` to apply to all scenarios) control how the browser runs:

| Tag | Effect |
|-----|--------|
| `@web` | Chromium (default) |
| `@web @firefox` | Firefox |
| `@web @webkit` | Safari engine |
| `@headless` | No visible browser window |
| `@headed` | Force browser visible — overrides `--headless` and `.env` |
| `@web @mobile @iphone` | iPhone 13 emulation |
| `@web @mobile @android` | Pixel 5 emulation |
| `@record_video` | Record `.webm`, saved to `videos/` |
| `@slow` | 500 ms delay between actions (debug) |

Tag priority (highest wins): `@headed` > `@headless` > `--headed` > `--headless` > `.env`

```gherkin
@headless
Feature: Regression Suite        ← all scenarios run headless

  @web @smoke
  Scenario: Standard login        ← headless (inherited)

  @web @headed
  Scenario: Debug this one        ← headed, overrides the Feature tag
    ...
```

---

## Assertions

### Structural — fast, no LLM

```gherkin
Then User should see "Products"
Then User should not see "Error"
Then User should have url containing "inventory"
And the page title should contain "Swag Labs"
```

### Semantic — vision LLM (requires `BDDFRAME_MODEL` in `.env`)

```gherkin
Then the checkout form should show a success state
Then the header should display the user's name
```

### Visual baseline — semantic diff (requires `BDDFRAME_MODEL`)

```gherkin
And the screen should look the same as before
And the "checkout" screen should look the same as before ignoring the header
```

First run captures a semantic description of the page. Subsequent runs compare against it — tolerates timestamps, avatars, and dynamic badges.

---

## Custom Extension Install

The `vscode-extension/` folder provides syntax highlighting, step validation, `[variable]` colouring and `@tag` autocomplete for `.feature` files.

**Prerequisites**

```bash
pip install -e ".[lsp]"
cd vscode-extension && npm install && cd ..
```

**Install**

```bash
ln -s /Users/gheeno/Projects/bddframe/vscode-extension \
      ~/.vscode/extensions/bddframe-0.1.0
```

Fully quit VS Code (`Cmd+Q` — not just close the window), then reopen it.

**Disable the Cucumber extension for this workspace**

The BDDFrame extension replaces `alexkrechik.cucumberautocomplete`. With both active they conflict on `.feature` files.

1. `Cmd+Shift+X` → search "Cucumber"
2. Right-click `alexkrechik.cucumberautocomplete` → **Disable (Workspace)**
3. `Cmd+Shift+P` → **Developer: Reload Window**

**Suppress unknown step warnings** (optional)

```json
// .vscode/settings.json
{
  "bddframe.unknownStepSeverity": "none"
}
```

Options: `"warning"` (default), `"information"` (Problems panel only), `"none"` (silent).

---

## Docs

- [Phase 1 — Foundation](docs/phase-01-foundation.md)
- [Phase 2 — Web Agent](docs/phase-02-web-agent.md)
- [Phase 3 — CLI & Hooks Hardening](docs/phase-03-hardening.md)
- [Phase 4 — Visual / Desktop Agent](docs/phase-04-visual-agent.md)
- [Phase 5 — Reporting](docs/phase-05-reporting.md)
- [Phase 6 — CLI, Recorder & Azure DevOps](docs/phase-06-cli-devops.md)
- [Phase 7 — Syntax Highlighting](docs/phase-07-syntax-highlighting.md)
