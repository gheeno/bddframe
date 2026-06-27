# Tech Stack — Libraries & Technologies

Every library and tool BDDFrame uses, the version it's pinned to, and why it's
here. Versions are the **declared minimums** from `pyproject.toml` /
`package.json` (the lock isn't committed), so installed builds may be newer.

---

## Language & runtime

| Tech | Version | Purpose |
|------|---------|---------|
| Python | `>=3.11` | The framework language. 3.11 is the floor (uses `tomllib`, modern typing). |
| uv | latest | Dependency manager / runner for the whole project. Replaces `pip` (which had install issues on the corporate network). |
| Node.js + npm | (for the extension only) | Builds and runs the VS Code extension. Not needed to run tests. |

---

## Core dependencies (always installed)

| Library | Version | Purpose |
|---------|---------|---------|
| [behave](https://behave.readthedocs.io/) | `>=1.2.6` | BDD runner. Parses `.feature` Gherkin files and drives each step. Runs **synchronously** — the reason Playwright's sync API is used. |
| [playwright](https://playwright.dev/python/) | `>=1.40.0` | Browser automation (the Web Agent). **Sync API** (`playwright.sync_api`). Drives Chromium / Firefox / WebKit. |
| [typer](https://typer.tiangolo.com/) | `>=0.9.0` | The `bddframe` CLI (run, record, etc.). |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | `>=1.0.0` | Loads `.env` (credentials, `BDDFRAME_*` config) into the environment. |
| [pillow](https://python-pillow.org/) | `>=10.0.0` | Image handling for screenshots and annotation. |
| [pyyaml](https://pyyaml.org/) | `>=6.0` | Parses `pom.yaml` (the Page Object Model selector files). |

---

## Optional extras (install only what you need)

Installed via `uv` extras, e.g. `uv pip install -e ".[llm]"` or `".[all]"`.

### `[llm]` — LLM fallback

| Library | Version | Purpose |
|---------|---------|---------|
| [litellm](https://github.com/BerriAI/litellm) | `>=1.0.0` | One interface to any model. bddframe's `ask` / `ask_vision` route through it. Speaks OpenAI-compatible endpoints, so it talks to Ollama, OpenAI, **and Foundry Local** unchanged. |

### `[lsp]` — VS Code language features

| Library | Version | Purpose |
|---------|---------|---------|
| [pygls](https://github.com/openlawlibrary/pygls) | `>=1.3.0` | Language Server Protocol implementation powering step validation/autocomplete. |
| [lsprotocol](https://github.com/microsoft/lsprotocol) | `>=2023.0.0` | LSP message type definitions used by pygls. |

### `[reporting]` — Allure reports

| Library | Version | Purpose |
|---------|---------|---------|
| [allure-python-commons](https://github.com/allure-framework/allure-python) | `>=2.13.0` | Emits Allure result JSON (rich HTML test reports). |

### `[visual]` — Visual / desktop agent

| Library | Version | Purpose |
|---------|---------|---------|
| [opencv-python](https://github.com/opencv/opencv-python) | `>=4.8.0` | Template matching — finds images/regions on screen for `@visual` steps. |
| [pytesseract](https://github.com/madmaze/pytesseract) | `>=0.3.10` | OCR — reads text from screenshots. Wraps the Tesseract binary (see externals). |
| [pyautogui](https://github.com/asweigart/pyautogui) | `>=0.9.54` | Desktop control — mouse/keyboard for non-browser automation. |
| [mss](https://github.com/BoboTiG/python-mss) | `>=9.0.1` | Fast cross-platform screen capture. |

---

## Dev & test tooling

| Tool | Purpose |
|------|---------|
| [pytest](https://pytest.org/) | Unit/integration tests in `tests/`. `make test` runs them (no browser needed). |
| Makefile | Shortcuts: `make test`, `make vsix`, `make install-ext`, `make clean`. |

---

## External binaries & services (not pip/uv installed)

These install through OS package managers or run as separate processes — the
distinction that tripped up `pip` on the corporate network.

| Thing | Install via | Purpose |
|-------|-------------|---------|
| Playwright browsers | `playwright install` | The actual Chromium/Firefox/WebKit binaries Playwright drives. |
| [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) | `brew` / `apt` / `winget` | OCR engine that `pytesseract` calls. Required for `@visual` text reading. |
| [Allure CLI](https://allurereport.org/) | `brew` / scoop / npm | Renders the Allure result JSON into an HTML report. |
| [Foundry Local](https://learn.microsoft.com/azure/foundry-local/) | `winget` / `brew` | Local model runtime (OpenAI-compatible). Runs `qwen2.5-7b` on a network where Ollama/Hugging Face are blocked. See [phase-10](phase-10-foundry-local-agent.md). |
| Ollama (alternative) | ollama.com | Local model runtime — the previous default. **Blocked on the corporate network**, hence the Foundry Local move. |

---

## VS Code extension (`vscode-extension/`)

| Tech | Version | Purpose |
|------|---------|---------|
| VS Code engine | `^1.80.0` | Minimum editor version the extension targets. |
| [vscode-languageclient](https://github.com/microsoft/vscode-languageserver-node) | `^9.0.1` | Client that connects the editor to the Python LSP server (`pygls`). |
| @vscode/vsce | (global) | Packages the extension into a `.vsix`. |
| TextMate grammar | — | `syntaxes/bddframe.tmLanguage.json` — syntax highlighting for `.feature` files. |

---

## CI/CD

| Tech | Purpose |
|------|---------|
| Azure Pipelines | `azure-pipelines.yml` (Linux) + `azure-pipelines-windows.yml` (Windows) run the suite and publish JUnit XML / Allure results. |
| JUnit XML | Test result format Azure DevOps ingests for test reporting. |

---

## How the LLM-relevant pieces fit (for the Foundry Local work)

`behave` → `bddframe` resolver → (on no-match) `litellm` → an OpenAI-compatible
endpoint. That endpoint can be Ollama, hosted OpenAI, or **Foundry Local** —
all the same to `litellm`, which is why running `qwen2.5-7b` locally needed
**zero code changes**, only `.env` config. See [llm.md](llm.md) and
[phase-10-foundry-local-agent.md](phase-10-foundry-local-agent.md).
