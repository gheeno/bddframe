# Noodle Test Framework

**QAs write a `.feature` file in plain sentences. Noodle Test Framework does the rest.**

No selectors. No Page Object classes. No step definitions. No code.

```gherkin
@web @smoke
Scenario: Valid user can log in
  Given User is on "[SAUCEDEMO]"
  When User enters [SAUCE_USERNAME] in the username field
  And User clicks the login button
  Then User should see "Products"
```

`[SAUCEDEMO]` resolves from `environments.yaml`. `[SAUCE_USERNAME]` from `secrets.env`.

---

## How it works

Each step travels through a local pipeline. The LLM is **off by default** — it only enters when you opt in.

```
Feature file
    │
    ▼
Step Resolver (50+ built-in patterns)
    │
    ├─ match found ──────────────────────► Web Agent (Playwright) ──► Report
    │
    └─ no match
          │
          ├─ LLM off (default) ──────────► FAIL loudly with screenshot
          │
          ├─ LLM auto (fallback) ────────► LLM ──► Web Agent ──────► Report
          │
          └─ LLM full (all steps) ───────► LLM ──► Web Agent ──────► Report
```

| Mode | `NOODLE_LLM_MODE` | `NOODLE_MODEL` | Behaviour |
|------|---------------------|-----------------|-----------|
| **Off** *(default)* | *(unset)* | *(unset)* | Patterns only. Unresolved step fails loudly. Fully local, zero cost. |
| **Fallback** | `auto` | set | Patterns first; LLM only when no pattern matches. |
| **Full LLM** | `full` | set | Every step goes to the LLM; patterns skipped. |

> Full detail on LLM setup, providers, and modes → **[docs/guide.md § LLM](docs/guide.md#16-using-an-llm--setup-providers-and-modes)**

---

## LLM augmentation

Noodle Test Framework is **model-agnostic** via [LiteLLM](https://github.com/BerriAI/litellm) — you point it at any provider with two lines of config. Cloud or local, the framework works the same way.

### Cloud providers (one API key required)

Install the LLM extra, set a model, add your key:

```bash
uv pip install -e ".[llm]"
```

```bash
# .env — committed, no secrets
NOODLE_MODEL=anthropic/claude-haiku-4-5-20251001
```

```bash
# secrets.env — gitignored
ANTHROPIC_API_KEY=your-key-here
```

Swap the model string for any supported provider:

| Provider | Model string | Key variable |
|----------|-------------|-------------|
| Anthropic Claude | `anthropic/claude-haiku-4-5-20251001` | `ANTHROPIC_API_KEY` |
| Google Gemini | `gemini/gemini-1.5-flash` | `GEMINI_API_KEY` |
| OpenAI | `openai/gpt-4o-mini` | `OPENAI_API_KEY` |
| Groq | `groq/llama-3.1-8b-instant` | `GROQ_API_KEY` |

### Local models with Ollama (free, no account, nothing leaves your machine)

Ollama runs any model locally — useful for private data, air-gapped environments, or just keeping costs at zero.

```bash
# 1. Install Ollama
brew install ollama        # or download from https://ollama.com

# 2. Pull a vision-capable model (can see screenshots to locate elements)
ollama pull llava

# 3. Start the server (keep this running in a separate terminal)
ollama serve
```

```bash
# .env
NOODLE_MODEL=ollama/llava
NOODLE_LLM_URL=http://localhost:11434
```

No key needed. Run your tests as normal — the model runs on your machine.

> **Vision vs text-only models.** Vision-capable models (llava, claude, gpt-4o, gemini) can look at a screenshot to locate elements. Text-only models (Groq, llama3) can interpret step phrases but fall back to the accessibility tree for element location. Ollama's `llava` is the recommended free local choice for full capability.

**Full provider guide, Foundry Local setup, and mode reference → [docs/guide.md §16](docs/guide.md#16-using-an-llm--setup-providers-and-modes)**

---

## Tech stack

| Library / Tool | Version | Role |
|----------------|---------|------|
| Python | ≥ 3.11 | Runtime |
| behave | ≥ 1.2.6 | BDD runner |
| Playwright | ≥ 1.40.0 | Browser automation |
| Pillow | ≥ 10.0.0 | Screenshot annotation |
| PyYAML | ≥ 6.0 | Config and POM parsing |
| python-dotenv | ≥ 1.0.0 | `.env` / `secrets.env` loading |
| Typer | ≥ 0.9.0 | `noodle` CLI |
| LiteLLM *(optional)* | ≥ 1.0.0 | LLM provider abstraction (Claude, Gemini, OpenAI, Ollama…) |
| allure-python-commons *(optional)* | ≥ 2.13.0 | Allure report generation |
| OpenCV *(optional)* | ≥ 4.8.0 | Visual / canvas testing |
| pytesseract *(optional)* | ≥ 0.3.10 | OCR for terminal / canvas scenarios |
| PyAutoGUI *(optional)* | ≥ 0.9.54 | Visual agent mouse / keyboard |
| BehaveX *(optional)* | ≥ 4.0.0 | Local parallel execution |
| azure-identity *(optional)* | ≥ 1.15.0 | Azure Key Vault auth |
| azure-keyvault-secrets *(optional)* | ≥ 4.7.0 | Azure Key Vault secret fetch |
| Allure CLI | latest | `noodle report generate/open` |
| Node.js | ≥ 18 | BusterBlock test app |

---

## Quick setup

### 1. Install

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/)

```bash
git clone https://github.com/gheeno/noodle.git
cd noodle

uv pip install -e ".[all]"      # or: pip install -e ".[all]"
playwright install chromium
```

For Allure reports (required for `noodle report`):

```bash
brew install allure              # macOS
# other platforms → https://allurereport.org/docs/install/
```

### 2. Configure

```bash
cp secrets.env.example secrets.env   # fill in your credentials
```

Three config files, each with a clear role:

| File | What goes here | Committed? |
|------|---------------|------------|
| `environments.yaml` | Base URLs (`[SAUCEDEMO]`, `[STAGING]`) | ✅ yes |
| `.env` | Browser and run settings — no secrets | ✅ yes |
| `secrets.env` | Credentials, API keys | ❌ gitignored |

See **[docs/glossary.md](docs/glossary.md)** for a full map of every env var and where it lives.

Each app-under-test (e.g. `features/web/busterblock/`) can keep its own
`environment/` folder with a package-scoped `.env`/`secrets.env`/
`environments.yaml` instead of using the root files — see
**[docs/feature-packages.md](docs/feature-packages.md)**.

### 3. Run tests

```bash
noodle run features/                                      # all tests
noodle run features/web/busterblock/ --headless           # a folder
noodle run features/web/busterblock/login.feature         # one file
noodle run features/web/busterblock/ --tag smoke          # by tag
```

### 4. Generate the report

```bash
noodle report generate
```

Reads `allure-results/` and writes `allure-report/` (HTML).

### 5. View the report

```bash
noodle report open
```

> Don't open `allure-report/index.html` directly — it needs HTTP. This command serves it.

---

## BusterBlock — the bundled test app

`test-app/` is **BusterBlock.ca**, a self-contained VHS-rental site (Node/Express, in-memory). All `features/web/busterblock/` tests run against it.

**Terminal 1 — start the app:**

```bash
cd test-app
npm install          # first time only
npm start            # → http://localhost:3333
```

**Terminal 2 — run the tests:**

```bash
noodle run features/web/busterblock/ --headless
```

The `[BUSTERBLOCK]` base URL is already committed at
`features/web/busterblock/environment/environments.yaml`. Copy the package's
credentials once:

```bash
cp features/web/busterblock/environment/secrets.env.example \
   features/web/busterblock/environment/secrets.env
```

Default values (`BB_USER=reel_ryan`, `BB_PASS=Popcorn1!`) already work against
the bundled app.

Run a specific capability:

```bash
noodle run features/web/busterblock/login.feature --headless
noodle run features/web/busterblock/ --tag @smoke
```

To run the LLM fallback demo (requires an API key):

```bash
NOODLE_MODEL=anthropic/claude-haiku-4-5-20251001 \
noodle run features/web/busterblock/llm_fallback.feature --no-capture
```

---

## Docs

| Doc | What's in it |
|-----|-------------|
| [docs/guide.md](docs/guide.md) | Complete how-to: write tests, pom.yaml, shared state, CI, LLM setup |
| [docs/feature-packages.md](docs/feature-packages.md) | Per-app packaging: `environment/`, `resources/`, resolution order, in-repo vs external workspace |
| [docs/glossary.md](docs/glossary.md) | Where to find everything — env vars, YAML files, outputs, resources |
| [docs/steps_dictionary.md](docs/steps_dictionary.md) | All built-in step patterns with examples |
| [docs/architecture.md](docs/architecture.md) | Deep dive: components, resolution hierarchy, the LLM layer |
| [docs/design-history.md](docs/design-history.md) | Rationale behind each capability |
