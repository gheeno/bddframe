# BDDFrame — Quick Start Guide

**Who this is for:** Someone brand new. Zero knowledge of AI, testing, or this framework required.  
**How to use it:** Follow top to bottom, in order. Do not skip sections.

---

## What is this framework?

BDDFrame lets you write tests in plain English sentences — no code, no selectors, no setup per page.

```gherkin
Scenario: User logs in
  Given User is on "https://www.saucedemo.com"
  When User enters "standard_user" in the username field
  And User enters "secret_sauce" in the password field
  And User clicks the login button
  Then User should see "Products"
```

That is a complete, real, working test. The framework reads plain sentences, opens a browser, performs the actions, and checks the result.

**Optionally**, you can turn on a local AI model (LLM) to handle steps that do not match any built-in pattern. That is covered in Part 5 and is not required to run most tests.

---

## Part 1 — Install Everything (one time only)

### What you need before starting

| Tool | Why | Install |
|---|---|---|
| Python 3.11+ | runs the framework | `brew install python@3.11` |
| uv | fast Python package manager | `curl -Ls https://astral.sh/uv/install.sh \| sh` |
| Node.js 18+ | runs the BusterBlock test app | `brew install node` |
| Allure CLI | generates HTML test reports | `brew install allure` |
| Ollama | runs AI models locally **(optional — LLM section only)** | `brew install ollama` |

Verify everything is installed:

```bash
python3 --version      # should say 3.11 or higher
node --version         # should say 18 or higher
allure --version
ollama --version       # only if you installed it
```

### Clone and install the framework

```bash
git clone https://github.com/gheeno/bddframe.git
cd bddframe

# Install everything (framework + LLM + reports + visual tools)
uv pip install -e ".[all]"

# Install the browser (Chromium — used by all web tests)
playwright install chromium
```

---

## Part 2 — Configure (one time only)

### Step 1 — create your secrets file

```bash
cp secrets.env.example secrets.env
```

The default credentials in `secrets.env.example` already work for the bundled test app (BusterBlock) and the public SauceDemo site. You do not need to change anything for the tests in this guide.

### Step 2 — check your .env file

Open `.env`. It should look like this (already there by default):

```bash
BDDFRAME_HEADLESS=false
BDDFRAME_BROWSER=chromium
BDDFRAME_TIMEOUT=10000
```

Leave this as-is for now. You will add LLM settings in Part 5 if you want them.

---

## Part 3 — Start the Test App

BusterBlock is a local VHS rental website bundled with the framework.  
Most tests in `features/web/busterblock/` run against it.  
**You must keep it running in a terminal for those tests to work.**

**Terminal A — keep this open the whole time:**

```bash
cd test-app
npm install          # first time only — downloads dependencies
npm start            # starts the site at http://localhost:3333
```

You should see: `Server running at http://localhost:3333`

Open `http://localhost:3333` in your browser to confirm it is running.  
Login: `reel_ryan` / `Popcorn1!`

---

## Part 4 — Run All the Tests

Open a **new terminal** (keep Terminal A running). All commands below go in this terminal.

```bash
cd bddframe
source .venv/bin/activate    # activate the Python environment
```

---

### 4.1 — Run the full BusterBlock suite

BusterBlock tests cover every framework capability: login, clicks, forms, navigation, assertions, waits, scroll, hover, API steps, variables, scenario outlines, POM fallback, custom scripts, custom hooks, and preconditions.

```bash
bddframe run features/web/busterblock/ --headless
```

Expected: all non-LLM tests pass. The LLM tests (`llm_fallback.feature`, `pure_llm.feature`) are skipped unless a model is configured — that is fine for now.

To run just one capability file:

```bash
bddframe run features/web/busterblock/login.feature --headless
bddframe run features/web/busterblock/assertions.feature --headless
bddframe run features/web/busterblock/navigation.feature --headless
```

To run by tag:

```bash
bddframe run features/web/busterblock/ --tag @smoke --headless
```

---

### 4.2 — Run the SauceDemo suite

SauceDemo is a public website — no local server needed.

```bash
bddframe run features/saucedemo/ --headless
```

These tests cover login (pass, locked-out user, empty credentials), checkout, and product browsing. They hit `https://www.saucedemo.com`.

---

### 4.3 — Run the Canadian Tire suite

Canadian Tire is a real public website. Tests use POM files (page object maps) to locate elements that have no accessible label.

```bash
bddframe run features/canadiantire/ --headless
```

These hit `https://www.canadiantire.ca`. They need internet. They take longer because they wait for a real retailer site to load.

---

### 4.4 — Run the API suite

These tests drive a public REST API — no browser, no local server.

```bash
bddframe run features/api/ --headless
```

Tests cover GET, POST, PUT, DELETE, and assertions on JSON responses. They hit `https://api.restful-api.dev`.

---

### 4.5 — Run everything at once

```bash
bddframe run features/ --headless
```

This includes all suites above. BusterBlock must be running (Terminal A). Canadian Tire and API need internet. The LLM feature files are skipped if no model is configured.

---

### 4.6 — Run all unit tests

Unit tests check the framework's internal logic — no browser, no LLM, no internet needed.

```bash
python -m pytest unit_tests/ -v
```

Expected: all pass. These run in seconds.

To run a single unit test file:

```bash
python -m pytest unit_tests/test_llm_mode.py -v
python -m pytest unit_tests/test_phase_pattern_coverage.py -v
```

---

### 4.7 — Generate and view the HTML report

After any test run:

```bash
bddframe report generate    # builds the HTML report in allure-report/
bddframe report open        # opens it in your browser
```

> Do not open `allure-report/index.html` directly — it will appear blank. Always use `bddframe report open`.

---

## Part 5 — Run the LLM Tests (optional — AI-powered steps)

> **This section is optional.** The framework runs fully without it. You only need this if you want the AI fallback to handle steps that do not match any built-in pattern.

### What is happening here?

BDDFrame has 50+ built-in step patterns. When a step matches one, it is handled locally — fast, free, deterministic. When a step does **not** match any pattern, BDDFrame can send it to a local AI model to figure out what to do.

**Without an AI model:** an unmatched step fails loudly with "No pattern matched."  
**With an AI model (auto mode):** the framework falls back to the model only for unmatched steps.  
**With an AI model (full mode):** every step goes to the model — even the ones that would match a pattern.

---

### Step 1 — start Ollama and pull the model

In a new terminal:

```bash
ollama serve
```

Then pull `llama3.1:8b` — a fast, capable local model (~4.7 GB, one-time download):

```bash
ollama pull llama3.1:8b
```

Confirm it downloaded:

```bash
ollama list
# You should see: llama3.1:8b
```

Keep Ollama running. Do not close this terminal.

> **Using a different model?** You can use any Ollama model (or any OpenAI-compatible provider). See the [Model Swap section](#swapping-the-model) below.

---

### Step 2 — point the framework at the model

Open `.env` and add these three lines:

```bash
BDDFRAME_LLM_MODE=auto
BDDFRAME_MODEL=ollama/llama3.1:8b
BDDFRAME_LLM_URL=http://localhost:11434
```

Your full `.env` should now look like:

```bash
BDDFRAME_HEADLESS=false
BDDFRAME_BROWSER=chromium
BDDFRAME_TIMEOUT=10000
BDDFRAME_LLM_MODE=auto
BDDFRAME_MODEL=ollama/llama3.1:8b
BDDFRAME_LLM_URL=http://localhost:11434
```

No API key. No account. Everything runs on your machine.

---

### Step 3 — run the LLM fallback test (auto mode)

`auto` mode: the framework tries its built-in patterns first. When a step has no matching pattern, it hands the step to the model.

Make sure BusterBlock is running (Terminal A), then:

```bash
bddframe run features/web/busterblock/llm_fallback.feature --no-capture
```

Watch the console output. When a step reaches the model you will see:

```
[LLM] no pattern matched — routing to model: ollama/llama3.1:8b
```

The steps `When User authenticates using the login button` and `Then User verifies the catalog is displayed` are intentionally written with verbs that do not match any built-in pattern (`authenticates`, `verifies`). Those two steps are what the model handles.

Expected: 2 scenarios pass.

---

### Step 4 — run the pure LLM test (full mode)

`full` mode: every step goes directly to the model, even the ones that would match a built-in pattern. The steps in this feature file are written in natural, free-form English — not the framework's structured vocabulary.

```bash
BDDFRAME_LLM_MODE=full \
bddframe run features/web/busterblock/pure_llm.feature --no-capture
```

The `BDDFRAME_LLM_MODE=full` here overrides the `auto` setting in `.env` for this one run only.

Expected: 2 scenarios pass. Every step — navigation, login, catalog check, cart interaction — is handled entirely by the model.

---

### Swapping the model

`BDDFRAME_MODEL` accepts any model string that LiteLLM understands. Change it in `.env`:

```bash
# Different Ollama model
BDDFRAME_MODEL=ollama/llama3.2
BDDFRAME_LLM_URL=http://localhost:11434

# Anthropic Claude (needs ANTHROPIC_API_KEY in secrets.env)
BDDFRAME_MODEL=claude-sonnet-4-6
# remove BDDFRAME_LLM_URL — not needed for cloud providers

# OpenAI (needs OPENAI_API_KEY in secrets.env)
BDDFRAME_MODEL=gpt-4o
# remove BDDFRAME_LLM_URL
```

For vision-based element location (fallback locator that reads screenshots), set a separate vision-capable model:

```bash
BDDFRAME_VISION_MODEL=ollama/llava
```

If `BDDFRAME_VISION_MODEL` is not set, the framework uses `BDDFRAME_MODEL` for vision tasks too.

---

## Part 6 — Write Your First Test

### Step 1 — create a feature file

Create a new file: `features/web/busterblock/my_first_test.feature`

```gherkin
@web @headless
Feature: My first test

  @smoke
  Scenario: I can log in and see the catalog
    Given User is on "[BUSTERBLOCK]"
    When User enters [BB_USER] in the username field
    And User enters [BB_PASS] in the password field
    And User clicks the login button
    Then User should see "VHS Catalog"
    And User should see "Jaws"
```

**What each part means:**

- `@web @headless` — run in a browser (Chromium), no visible window
- `[BUSTERBLOCK]` — resolves to `http://localhost:3333` from `environments.yaml`
- `[BB_USER]` / `[BB_PASS]` — resolves from `secrets.env` (`reel_ryan` / `Popcorn1!`)
- `Then User should see "VHS Catalog"` — asserts that text appears on the page

### Step 2 — run it

```bash
bddframe run features/web/busterblock/my_first_test.feature
```

You should see a Chromium window open, log in, and the test pass.

### Step 3 — try a step the LLM will handle (requires Part 5)

Add this scenario to the same file:

```gherkin
  @smoke
  Scenario: I log in using a phrase the AI interprets
    Given User is on "[BUSTERBLOCK]"
    When User enters [BB_USER] in the username field
    And User enters [BB_PASS] in the password field
    When User authenticates via the login button
    Then User should see "VHS Catalog"
```

`authenticates via` is not a built-in pattern. With `BDDFRAME_LLM_MODE=auto` and `BDDFRAME_MODEL=ollama/llama3.1:8b` set in `.env`, this step will be handed to the model.

```bash
bddframe run features/web/busterblock/my_first_test.feature --no-capture
```

### Step 4 — run your test by tag

```bash
bddframe run features/web/busterblock/my_first_test.feature --tag @smoke
```

---

## Quick Reference

### Run commands

```bash
# All BusterBlock tests
bddframe run features/web/busterblock/ --headless

# One feature file
bddframe run features/web/busterblock/login.feature --headless

# By tag
bddframe run features/web/busterblock/ --tag @smoke --headless

# SauceDemo (public site, no local server)
bddframe run features/saucedemo/ --headless

# Canadian Tire (real site, needs internet)
bddframe run features/canadiantire/ --headless

# API tests (REST, no browser)
bddframe run features/api/ --headless

# Everything
bddframe run features/ --headless

# Unit tests (no browser, no LLM)
python -m pytest unit_tests/ -v

# LLM fallback (auto mode — patterns first, AI on no-match)
bddframe run features/web/busterblock/llm_fallback.feature --no-capture

# Pure LLM (full mode — every step goes to AI)
BDDFRAME_LLM_MODE=full \
bddframe run features/web/busterblock/pure_llm.feature --no-capture
```

### Config files

| File | What it contains | Committed to git? |
|---|---|---|
| `.env` | browser settings, LLM model, run mode | Yes |
| `secrets.env` | passwords, API keys | **No — never commit this** |
| `environments.yaml` | base URLs (`[BUSTERBLOCK]`, `[SAUCEDEMO]`) | Yes |

### LLM mode toggle

| `BDDFRAME_LLM_MODE` in `.env` | Behaviour |
|---|---|
| *(not set)* | No AI. Unmatched step = immediate failure. |
| `auto` | Patterns first. AI only when no pattern matches. |
| `full` | Every step goes to AI. Patterns skipped. |

### Where results go after a run

| Output | Location |
|---|---|
| Allure report data | `allure-results/` |
| Failure screenshots | `screenshots/FAILED_<step>.png` |
| Failure traces | `traces/<scenario>.zip` |
| Locator heal suggestions | `healing-report.txt` |

---

## Troubleshooting

**`bddframe: command not found`**  
Activate the venv first: `source .venv/bin/activate`

**`litellm` not found / LLM import error**  
```bash
uv pip install -e ".[llm]"
```

**`ConnectionRefused` when running LLM tests**  
Ollama is not running. Start it: `ollama serve`

**Model is slow on first call**  
Normal. The model loads into memory on first use; subsequent calls are faster. `llama3.1:8b` on CPU takes ~10–20 s on first inference.

**BusterBlock tests fail with "connection refused"**  
Terminal A is not running the app. `cd test-app && npm start`

**`No pattern matched and no LLM configured`**  
You wrote a step that does not match a built-in pattern, and no model is set. Either use a built-in step phrase (see `docs/steps_dictionary.md`) or add `BDDFRAME_MODEL=ollama/llama3.1:8b` to `.env`.

**Allure report is blank when I open `index.html` directly**  
Use `bddframe report open` instead. The report uses HTTP — it cannot load from `file://`.
