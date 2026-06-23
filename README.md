# BDDFrame

**QAs write a `.feature` file in plain sentences. BDDFrame does the rest.**

No selectors. No Page Object classes. No step definitions. No code.

---

## What a QA writes

```gherkin
Feature: Guest Checkout

  @web @smoke
  Scenario: Customer completes a purchase with a valid card

    Given I have 2 items in my cart
    When I go to checkout
    And I enter [my email] in the email field
    And I enter [my card number] in the card details
    And I place the order
    Then I should see a thank you message
    And the screen should look the same as before
```

That is the only file the QA touches. No Python. No YAML. No XPath.

---

## How it works

1. **`behave` parses** the `.feature` file into steps
2. **LangGraph orchestrator** routes each step to the right agent
3. **Web agent** finds elements by what they *are* (label, role, text) — not by CSS selector
4. **LLM interprets** ambiguous steps — no step definitions ever written
5. **Vision LLM asserts** things that can't be expressed in DOM terms ("looks the same as before")
6. **Allure report** shows pass/fail with annotated screenshots of exactly what went wrong

---

## Stack (all open source)

| Layer | Tool | License |
|-------|------|---------|
| BDD parsing | `behave` | BSD |
| Orchestration | `LangGraph` | Apache 2.0 |
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
pip install bddframe
playwright install chromium

bddframe run tests/checkout.feature
bddframe report open
```

Record a flow instead of writing from scratch:

```bash
bddframe record --output tests/checkout.feature
# browser opens → do the flow → close → .feature file generated
```

---

## Variable substitution

`[my email]` in a step maps to `MY_EMAIL` in `.env` or CI pipeline variables. No special syntax — square brackets are the universal convention.

```
# .env
MY_EMAIL=test@example.com
MY_CARD_NUMBER=4111111111111111
SHOP_URL=https://staging.myshop.com
```

---

## Custom Extension Install

The `vscode-extension/` folder is a VS Code extension that provides syntax highlighting, step validation, `[variable]` colouring and `@tag` autocomplete — specific to BDDFrame.

**Prerequisites**

```bash
# Install LSP dependencies
pip install -e ".[lsp]"

# Install extension npm dependencies (one-time)
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

Add to `.vscode/settings.json`:

```json
{
  "bddframe.unknownStepSeverity": "none"
}
```

Options: `"warning"` (default), `"information"` (Problems panel only), `"none"` (silent).

---

## Docs

- [Phase 1 — Foundation](docs/phase-01-foundation.md)
- [Phase 2 — Web Agent](docs/phase-02-web-agent.md)
- [Phase 3 — Visual / Desktop Agent](docs/phase-03-visual-agent.md)
- [Phase 4 — Reporting](docs/phase-04-reporting.md)
- [Phase 5 — CLI, Recorder & Azure DevOps](docs/phase-05-cli-devops.md)
- [Phase 6 — Syntax Highlighting](docs/phase-06-syntax-highlighting.md)
