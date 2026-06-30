# BDDFrame — Agentic Quick Start

**Who this is for:** Someone who wants to install BDDFrame as a tool and keep their
tests in their own folder — not inside the framework repo. Plus an interactive
terminal agent that turns plain English into test runs and new tests.

**The mental model:**

- **The engine** (`bddframe`) is a package you `pip install`. It never holds your tests.
- **Your workspace** is any folder you own. It holds your `.feature` files, page
  objects, `.env`, and a `bddframe.yaml` config.
- **The agent** (`bddframe-agent`) is a terminal chat on top of the engine. It's a
  convenience — CI/CD uses the engine directly and never needs the agent.

```
~/my-tests/                 ← your workspace (lives anywhere)
├── bddframe.yaml           ← config
├── .env                    ← settings (no secrets)
├── secrets.env             ← credentials (gitignored)   [you add this]
├── environments.yaml       ← base URLs                  [optional]
└── features/
    ├── environment.py      ← engine glue (auto-created)
    ├── steps/
    │   └── z_catch_all.py  ← engine glue (auto-created)
    ├── pageobjects/        ← *_pom.yaml selector files
    └── *.feature           ← your tests
```

---

## Part 1 — Install the engine (one time)

```bash
# From PyPI / a checkout — install the package itself, not the repo's tests
pip install -e ".[all]"        # or: pip install bddframe[all]
playwright install chromium
```

That's the only place framework code lives. Upgrades are `pip install --upgrade bddframe`
— you never touch the framework to get new features.

---

## Part 2 — Create a workspace

Pick any empty folder and scaffold it:

```bash
bddframe init ~/my-tests
cd ~/my-tests
```

This writes a **runnable** workspace:

```
Created:
  ~/my-tests/bddframe.yaml
  ~/my-tests/.env
  ~/my-tests/features/environment.py
  ~/my-tests/features/steps/z_catch_all.py
  ~/my-tests/features/pageobjects/.gitkeep
```

`environment.py` and `steps/z_catch_all.py` are tiny files that re-export the
installed engine — they're what lets `behave` discover BDDFrame's hooks and steps.
You don't edit them.

### `bddframe.yaml`

```yaml
features_dir: features
pageobjects_dir: features/pageobjects
env_file: .env
reports_dir: reports
browser: chromium          # chromium | firefox | webkit
headless: false            # true in CI
```

Paths are relative to the file. `browser`/`headless` are defaults; CLI flags
override them.

### Secrets & URLs (optional)

- **Credentials** → create `secrets.env` (gitignored). Referenced in features as
  `[SAUCE_PASSWORD]` etc.
- **Base URLs** → create `environments.yaml`. Top-level keys become `[KEY]`
  references, e.g. `saucedemo: https://www.saucedemo.com` → `[SAUCEDEMO]`.

Both are loaded automatically when the workspace runs. Skip them if your features
use literal URLs and values.

---

## Part 3 — The agent (interactive)

```bash
bddframe-agent --workspace ~/my-tests
# or just `bddframe-agent` if you're already in the workspace
```

```
bddframe-agent — workspace: /Users/you/my-tests  (rule-based, no LLM)
Type 'help' for commands, 'quit' to exit.

bddframe> create test for login at https://www.saucedemo.com
→ Wrote features/login.feature
→ Wrote features/pageobjects/login_pom.yaml
→ Run: bddframe run features/login.feature

bddframe> run login
bddframe> run smoke
bddframe> list
bddframe> summary
bddframe> quit
```

### What it understands

| You type | It does |
|---|---|
| `run` / `run all` | run every feature |
| `run <name>` | run the matching `.feature` file |
| `run <tag>` | no file matches → run that tag (e.g. `run smoke`) |
| `list` / `what tests` | list all scenarios |
| `create test for <desc> at <url>` | scaffold a feature + skeleton POM |
| `summary` / `what failed` | plain-English summary of the last run |
| `help` | command list |
| `quit` / `exit` | leave |

It's keyword matching, not a model — no API key, no cost, works offline.

### Generated tests are skeletons

`create test` picks the nearest template (login / search / generic), fills in the
URL, and leaves `<placeholders>` plus a POM with `<css selector>` stubs. Open the
files, replace the placeholders with real values and selectors, then run.

---

## Part 4 — The engine (direct / CI-CD)

Everything the agent does maps to a plain command. CI uses these directly:

```bash
bddframe run      --workspace ~/my-tests --headless        # all features
bddframe run      --workspace ~/my-tests --tag smoke
bddframe run      ~/my-tests/features/login.feature
bddframe list     --workspace ~/my-tests
bddframe validate --workspace ~/my-tests                   # parse-only, no browser
bddframe summary  --workspace ~/my-tests                   # after a run
```

`--workspace` (or `-w`) makes the engine run inside that folder, so it finds the
workspace's `.env` / `environments.yaml` and writes `allure-results` there. With no
`--workspace`, it uses the current directory. CLI flags (`--headless`, `--browser`,
`--tag`) override `bddframe.yaml`.

### Example CI step

```yaml
- run: pip install bddframe
- run: bddframe run --workspace ./tests --headless --tag smoke
```

No agent involved. The engine is the CI artifact; the agent is a developer convenience.

---

## Part 5 — Add an LLM (optional)

Both test generation and run summaries can be upgraded to a model. Same `--llm`
flag for both. Nothing else changes.

### Local & free — Ollama

```bash
ollama pull llama3.2
bddframe-agent --workspace ~/my-tests --llm ollama --model llama3.2
```

Now `create test ...` writes full Gherkin from your description, and `summary` gives
a root-cause narrative. Runs on your machine — no internet, no API cost.

### Paid — Claude / Gemini

```bash
export ANTHROPIC_API_KEY=sk-ant-...
bddframe-agent --workspace ~/my-tests --llm claude --model anthropic/claude-sonnet-4-6
```

```bash
export GEMINI_API_KEY=...
bddframe-agent --workspace ~/my-tests --llm gemini
```

The engine routes everything through `litellm`, so any provider it supports works
via `--model`. You bring your own key.

The summary command takes the same flag directly:

```bash
bddframe summary --workspace ~/my-tests --llm ollama
```

---

## Cost model

| Mode | Cost | What you get |
|---|---|---|
| Rule-based agent (default) | $0 | run, list, template scaffold, template summary |
| `--llm ollama` | $0 | natural-language generation, richer summaries (local) |
| `--llm claude` / `gemini` | your API key | complex generation, full prose output |

---

## Troubleshooting

- **`No steps directory in '.../features'`** — the workspace is missing the engine
  glue. Re-run `bddframe init <path>`; it creates `environment.py` + `steps/` without
  overwriting your existing files.
- **A generated test fails immediately** — it's a skeleton. Replace the
  `<placeholders>` in the `.feature` and the `<css selector>` stubs in
  `features/pageobjects/<name>_pom.yaml`.
- **`bddframe summary` shows 0 passed / 0 failed** — no results yet. Run something
  first; the summary reads `<workspace>/allure-results`.
