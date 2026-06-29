# BDDFrame — Where to Find What

Quick navigation for settings, files, and resources. If you're looking for a specific config value, output file, or doc section, start here.

---

## Configuration files

| What you're configuring | File | Notes |
|------------------------|------|-------|
| Base URLs (`[SAUCEDEMO]`, `[STAGING]`) | `environments.yaml` | Committed. One key per environment. |
| Browser, headless, retries, LLM mode | `.env` | Committed. No secrets here. |
| Credentials, API keys | `secrets.env` | **Gitignored.** Copy from `secrets.env.example`. |
| Element aliases when labels fail | `pom.yaml` | Colocated next to the feature file. |
| Precondition / teardown HTTP calls | `preconditions.yaml` | Colocated next to the feature file. |
| Azure Key Vault connection | `.env` (`BDDFRAME_KEYVAULT_URL`) + `secrets.env` | Requires `.[azure]` extra. |

---

## Environment variables

### Run and browser settings — `.env`

| Variable | Default | What it does |
|----------|---------|-------------|
| `BDDFRAME_BROWSER` | `chromium` | `chromium` \| `firefox` \| `webkit` |
| `BDDFRAME_HEADLESS` | `false` | `true` for CI |
| `BDDFRAME_STRICT_LOCATOR` | `false` | `true` = ambiguous locators fail (recommended in CI) |
| `BDDFRAME_RETRIES` | `1` | Re-run a failed scenario N extra times |
| `BDDFRAME_PARALLEL_PROCESSES` | *(unset)* | Number of parallel workers (requires `.[parallel]` extra) |
| `BDDFRAME_SCRIPT_TIMEOUT` | `60` | Timeout in seconds for `run the script` steps |
| `BDDFRAME_LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |

### LLM settings — `.env` (model name) + `secrets.env` (API key)

| Variable | Where | What it does |
|----------|-------|-------------|
| `BDDFRAME_MODEL` | `.env` | Enable LLM. E.g. `anthropic/claude-haiku-4-5-20251001`, `gemini/gemini-1.5-flash` |
| `BDDFRAME_LLM_MODE` | `.env` | `auto` (fallback) \| `full` (every step). Default: `auto` when model is set. |
| `BDDFRAME_LLM_URL` | `.env` | Override LLM endpoint (Ollama, Foundry Local) |
| `BDDFRAME_VISION_MODEL` | `.env` | Separate model for visual / `@visual` steps |
| `BDDFRAME_RCA` | `.env` | `true` = classify failure root cause after each failed step |
| `ANTHROPIC_API_KEY` | `secrets.env` | Claude API key |
| `GEMINI_API_KEY` | `secrets.env` | Gemini API key |
| `GROQ_API_KEY` | `secrets.env` | Groq API key |
| `OPENAI_API_KEY` | `secrets.env` | OpenAI API key |

### Secrets and credentials — `secrets.env`

| Variable | What it does |
|----------|-------------|
| `BB_USER` / `BB_PASS` | BusterBlock demo credentials |
| `SAUCE_USERNAME` / `SAUCE_PASSWORD` | SauceDemo credentials |
| `BDDFRAME_KEYVAULT_URL` | Azure Key Vault URL (if using Key Vault) |
| Any `[VAR]` in a feature | Matching key in `secrets.env`, shell env, or Key Vault |

Variable resolution order (highest wins): **Key Vault → shell/CI → `.env` → `secrets.env` → `environments.yaml`**

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
| POM aliases | `pom.yaml` next to the feature file |
| Precondition fixtures | `preconditions.yaml` next to the feature file |
| Utility scripts (CI discovery, seeding) | `scripts/` |
| Unit tests | `unit_tests/` |
| BusterBlock test app source | `test-app-vhs-vault/` |
| CI pipeline (Azure DevOps) | `azure-pipelines.yml`, `azure-pipelines-windows.yml` |
| Docker image | `Dockerfile` |

---

## Output files

| Output | Where | How to open |
|--------|-------|------------|
| Allure raw results | `allure-results/` | Input for `bddframe report generate` |
| Allure HTML report | `allure-report/` | `bddframe report open` (needs HTTP, not `file://`) |
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
| Where do I set which browser to use? | `BDDFRAME_BROWSER` in `.env` |
| Where do I enable the LLM? | `BDDFRAME_MODEL` in `.env` + API key in `secrets.env` |
| Where do I add a POM alias for a hard-to-find element? | `pom.yaml` next to your feature file |
| Where do I add a data precondition / teardown? | `preconditions.yaml` next to your feature file |
| Where do I add a custom step? | `features/steps/` — any `.py` file with `@when`/`@then` decorators |
| Where do I put a CSV or JSON fixture file? | `features/<suite>/resources/` |
| Where is the full step reference? | `docs/steps_dictionary.md` |
| Where do I find failure details? | `screenshots/` for images, `traces/` for Playwright traces, `allure-report/` for the full report |
