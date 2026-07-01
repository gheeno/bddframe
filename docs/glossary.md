# Noodle Test Framework — Where to Find What

Quick navigation for settings, files, and resources. If you're looking for a specific config value, output file, or doc section, start here.

---

## Configuration files

| What you're configuring | File | Notes |
|------------------------|------|-------|
| Base URLs (`[SAUCEDEMO]`, `[STAGING]`) | `environments.yaml` | Committed. One key per environment. |
| Browser, headless, retries, LLM mode | `.env` | Committed. No secrets here. |
| Credentials, API keys | `secrets.env` | **Gitignored.** Copy from `secrets.env.example`. |
| Per-app env/secrets/URLs | `features/<app>/environment/` | Optional — overrides the root files for that app only. See [feature-packages.md](feature-packages.md). |
| Element aliases when labels fail | `pom.yaml` | Colocated next to the feature file. |
| Precondition / teardown HTTP calls | `preconditions.yaml` | Colocated next to the feature file. |
| Azure Key Vault connection | `.env` (`NOODLE_KEYVAULT_URL`) + `secrets.env` | Requires `.[azure]` extra. |

---

## Environment variables

### Run and browser settings — `.env`

| Variable | Default | What it does |
|----------|---------|-------------|
| `NOODLE_BROWSER` | `chromium` | `chromium` \| `firefox` \| `webkit` |
| `NOODLE_HEADLESS` | `false` | `true` for CI |
| `NOODLE_STRICT_LOCATOR` | `false` | `true` = ambiguous locators fail (recommended in CI) |
| `NOODLE_RETRIES` | `1` | Re-run a failed scenario N extra times |
| `NOODLE_PARALLEL_PROCESSES` | *(unset)* | Number of parallel workers (requires `.[parallel]` extra) |
| `NOODLE_SCRIPT_TIMEOUT` | `60` | Timeout in seconds for `run the script` steps |
| `NOODLE_LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |

### LLM settings — `.env` (model name) + `secrets.env` (API key)

| Variable | Where | What it does |
|----------|-------|-------------|
| `NOODLE_MODEL` | `.env` | Enable LLM. E.g. `anthropic/claude-haiku-4-5-20251001`, `gemini/gemini-1.5-flash` |
| `NOODLE_LLM_MODE` | `.env` | `auto` (fallback) \| `full` (every step). Default: `auto` when model is set. |
| `NOODLE_LLM_URL` | `.env` | Override LLM endpoint (Ollama, Foundry Local) |
| `NOODLE_VISION_MODEL` | `.env` | Separate model for visual / `@visual` steps |
| `NOODLE_RCA` | `.env` | `true` = classify failure root cause after each failed step |
| `ANTHROPIC_API_KEY` | `secrets.env` | Claude API key |
| `GEMINI_API_KEY` | `secrets.env` | Gemini API key |
| `GROQ_API_KEY` | `secrets.env` | Groq API key |
| `OPENAI_API_KEY` | `secrets.env` | OpenAI API key |

### Secrets and credentials — `secrets.env`

| Variable | What it does |
|----------|-------------|
| `BB_USER` / `BB_PASS` | BusterBlock credentials — `features/web/busterblock/environment/secrets.env` |
| `SAUCE_USERNAME` / `SAUCE_PASSWORD` | SauceDemo credentials |
| `NOODLE_KEYVAULT_URL` | Azure Key Vault URL (if using Key Vault) |
| Any `[VAR]` in a feature | Matching key in `secrets.env`, shell env, Key Vault, or the feature's own `environment/secrets.env` |

Variable resolution order (highest wins): **Key Vault → shell/CI → root `.env` → root `secrets.env` → `<app>/environment/.env` → `<app>/environment/secrets.env` → `environments.yaml`**. See [feature-packages.md](feature-packages.md) for the per-app cascade.

---

## Source files and directories

| What you're looking for | Where |
|------------------------|-------|
| Feature files (tests) | `features/` |
| BusterBlock test suite | `features/web/busterblock/` |
| SauceDemo tests | `features/web/saucedemo/` |
| API tests | `features/api/` |
| Terminal / canvas tests | `features/terminal/` |
| Custom step definitions | `features/steps/` |
| Resource files (CSV, JSON payloads) | `features/<suite>/resources/` |
| Per-app env/secrets/base URL | `features/<suite>/environment/` |
| POM aliases | `pom.yaml` next to the feature file |
| Precondition fixtures | `preconditions.yaml` next to the feature file |
| Utility scripts (CI discovery, seeding) | `scripts/` |
| Unit tests | `unit_tests/` |
| BusterBlock test app source | `test-app/` |
| CI pipeline (Azure DevOps) | `azure-pipelines.yml`, `azure-pipelines-windows.yml` |
| Docker image | `Dockerfile` |

---

## Output files

| Output | Where | How to open |
|--------|-------|------------|
| Allure raw results | `allure-results/` | Input for `noodle report generate` |
| Allure HTML report | `allure-report/` | `noodle report open` (needs HTTP, not `file://`) |
| JUnit XML (CI) | `allure-results/junit.xml` | Azure DevOps Tests tab |
| Failure screenshots | `screenshots/` | Open directly |
| Playwright traces | `traces/` | `playwright show-trace traces/<name>.zip` |
| Healing telemetry | `healing.jsonl` | JSON Lines, one entry per healed locator |
| Healing report | `healing-report.txt` | Plain text with `pom.yaml` suggestions |

---

## Documentation

| Doc | What's in it |
|-----|-------------|
| `README.md` | Overview, tech stack, quick setup, BusterBlock |
| `docs/guide.md` | Complete how-to: write tests, pom.yaml, shared state, CI, LLM setup |
| `docs/feature-packages.md` | Per-app packaging: `environment/`, resolution order, in-repo vs external workspace |
| `docs/steps_dictionary.md` | All built-in step patterns with phrasings and examples |
| `docs/architecture.md` | Deep dive: components, resolution hierarchy, the LLM layer |
| `docs/design-history.md` | Rationale behind each capability |
| `plans/` | Implementation plans, phase reviews, future roadmap |

---

## Common "where is…" questions

| Question | Answer |
|----------|--------|
| Where do I put a base URL? | `environments.yaml` — referenced as `[KEY]` in features |
| Where do I put a password or API key? | `secrets.env` — gitignored, never committed |
| Where do I set which browser to use? | `NOODLE_BROWSER` in `.env` |
| Where do I enable the LLM? | `NOODLE_MODEL` in `.env` + API key in `secrets.env` |
| Where do I add a POM alias for a hard-to-find element? | `pom.yaml` next to your feature file |
| Where do I add a data precondition / teardown? | `preconditions.yaml` next to your feature file |
| Where do I add a custom step? | `features/steps/` — any `.py` file with `@when`/`@then` decorators |
| Where do I put a CSV or JSON fixture file? | `features/<suite>/resources/` |
| Where is the full step reference? | `docs/steps_dictionary.md` |
| Where do I find failure details? | `screenshots/` for images, `traces/` for Playwright traces, `allure-report/` for the full report |
