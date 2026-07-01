# BFRAME_0034 — Agent + Engine Architecture

## Goal

Allow users to interact with BFRAME through a terminal agent for test creation and execution,
while keeping the framework as a pip-installable engine whose test files, config, and POMs
live entirely outside the BFRAME repo. CI/CD pipelines use the engine directly; the agent is
a developer convenience layer on top.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  User's Workspace  (lives anywhere, outside BFRAME repo)         │
│                                                                  │
│  ~/my-tests/                                                     │
│  ├── noodle.yaml        ← workspace config                     │
│  ├── .env                 ← secrets / env vars                   │
│  ├── features/            ← .feature files                       │
│  └── pageobjects/         ← *_pom.yaml files                     │
└──────────────────────────────────────────────────────────────────┘
           ▲                            ▲
           │ reads                      │ writes
           │                            │
┌──────────┴──────────┐    ┌────────────┴──────────────────────────┐
│   BFRAME Engine      │    │   noodle-agent  (new)               │
│  (pip install        │◄───│                                        │
│   noodle)          │    │  Interactive REPL in terminal          │
│                      │    │  Intent Parser (rule-based, free)     │
│  noodle run        │    │  └── Ollama fallback (opt-in, local)  │
│  noodle validate   │    │                                        │
│  noodle init       │    │  Actions:                             │
│  noodle report     │    │  • create test for <url/description>  │
│  noodle list       │    │  • run [tag/feature/all]              │
└──────────┬──────────┘    │  • list / what tests do we have       │
           │                │  • summary / what failed              │
           │                └───────────────────────────────────────┘
           ▼
┌──────────────────────┐
│  CI/CD Pipeline      │
│  (no agent needed)   │
│                      │
│  pip install noodle│
│  noodle run        │
│    --workspace ./tests│
└──────────────────────┘
```

---

## What already exists vs. what's needed

| Capability                             | Status  | Notes                                          |
|----------------------------------------|---------|------------------------------------------------|
| pip-installable package                | ✅ done  | hatchling + pyproject.toml                     |
| `noodle run <path>` CLI              | ✅ done  | accepts any path already                       |
| `litellm` optional dep                 | ✅ done  | `pip install noodle[llm]`                    |
| LLM client module (`noodle/llm/`)    | ✅ done  |                                                |
| External workspace isolation           | ⚠️ partial | CLI accepts paths; no `noodle.yaml` config or `init` command yet |
| `noodle-agent` REPL                  | ❌ missing |                                               |
| Test generation (feature + POM scaffold)| ❌ missing |                                              |
| Plain-English report summary           | ❌ missing |                                               |

---

## Phases

### Phase 1 — Workspace isolation (engine mode)

**Goal:** Feature files, `.env`, POM YAML live in any directory the user owns.
BFRAME is a library you install; your test workspace is separate.

**Changes:**

1. `noodle init [path]` command — scaffolds a workspace outside the BFRAME repo:
   ```
   my-tests/
   ├── noodle.yaml
   ├── .env
   ├── features/
   │   └── .gitkeep
   └── pageobjects/
       └── .gitkeep
   ```

2. `noodle.yaml` — workspace config file:
   ```yaml
   features_dir: ./features
   pageobjects_dir: ./pageobjects
   env_file: ./.env
   reports_dir: ./reports
   browser: chromium
   headless: false
   ```

3. `noodle run` — reads `noodle.yaml` from CWD when no path is given.

**CI/CD usage (unchanged in principle):**
```bash
pip install noodle
noodle run --workspace ./tests        # reads tests/noodle.yaml
# or existing form still works:
noodle run ./tests/features/login.feature
```

**Upgrade path for users:** `pip install --upgrade noodle` — they never touch framework code.

---

### Phase 2 — Rule-based agent shell (zero LLM cost)

**Goal:** `noodle-agent` REPL maps natural language to engine commands.
No paid API, no Ollama required.

**New entry point** in `pyproject.toml`:
```
noodle-agent = "noodle.agent.repl:main"
```

**Usage:**
```
$ noodle-agent --workspace ~/my-tests

noodle> run smoke tests
→ noodle run ./features --tag smoke

noodle> list all scenarios
→ noodle list ./features

noodle> run checkout
→ noodle run ./features/checkout.feature

noodle> what failed last time
→ [Phase 4 summary]

noodle> create test for login at https://saucedemo.com
→ [Phase 3 generator]
```

**Intent table (keyword matching, ~80 lines of code):**

| Keywords | Action |
|---|---|
| `run [all]` | `noodle run` |
| `run <name>` | match feature file or tag, run it |
| `list`, `what tests` | `noodle list` |
| `create test for <desc>` | Phase 3 generator |
| `summary`, `what failed`, `report` | Phase 4 summary |
| `help` | print help |

**Implementation:** pure Python REPL, no framework dependencies beyond what's already installed.
80% of agent interactions are covered by keyword matching alone.

---

### Phase 3 — Test generation

**Goal:** `create test for the login page at https://...` writes a `.feature` + skeleton POM YAML
into the user's workspace.

**Rule-based first (no LLM, no cost):**
- Parse URL + description keywords
- Pick nearest template: `login`, `search`, `form`, `checkout`, `navigation`
- Fill in URL, page name, placeholder steps
- Write to `features/<name>.feature` + `pageobjects/<name>_pom.yaml`

**Example output:**
```
noodle> create test for login at https://saucedemo.com

→ Writing features/login.feature ...
→ Writing pageobjects/login_pom.yaml ...
→ Done. Run: noodle run features/login.feature
```

**Ollama upgrade (opt-in, local, free):**
```bash
noodle-agent --workspace ~/my-tests --llm ollama --model llama3.2
```
- Routes through `litellm` (already a dep, zero new dependencies)
- Natural language description → full Gherkin via local model
- No internet, no API cost, runs on the user's machine

---

### Phase 4 — Plain-English report summary

**Goal:** After a run, output a human-readable summary alongside the Allure report.

**Template-based (no LLM):**
Read `allure-results/*.json` → emit:

```
Run summary — 2026-06-29
✅  8 passed
❌  2 failed
   • Checkout > Complete order     failed at: I click "Finish"
   • Login > Invalid credentials   failed at: I should see an error message
⏱️  Total: 42s

Allure report → ./reports/allure-report/index.html
```

This is useful standalone — no LLM needed.

**Ollama upgrade (opt-in):** Pass the structured JSON to local model for richer
root-cause narrative. Same `--llm ollama` flag as Phase 3.

---

### Phase 5 — Paid LLM opt-in (zero new code)

Users who want Claude/GPT for richer generation or analysis:
```bash
noodle-agent --llm claude --model claude-sonnet-4-6
```

`litellm` already handles routing. The flag is already wired by Phase 3. This phase is
just exposing what's there; the user brings their own API key.

---

## Cost model

| Mode                         | Cost             | Capability                                  |
|------------------------------|------------------|---------------------------------------------|
| Rule-based agent (default)   | $0               | Run, list, template-based scaffold          |
| + Ollama (opt-in)            | $0               | Natural language generation, richer summaries |
| + Paid LLM (opt-in)          | User's API key   | Complex generation, full prose output       |

---

## CI/CD path (no agent involved)

```yaml
# .github/workflows/test.yml or azure-pipelines.yml
- run: pip install noodle
- run: noodle run --workspace ./tests --headless --tag smoke
```

The agent is a developer convenience. The engine is the CI artifact. Fully decoupled.

---

## Implementation order

| Phase | Effort   | Delivers                                      |
|-------|----------|-----------------------------------------------|
| 1     | Small    | Framework usable as installable library       |
| 2     | Small    | Interactive test running via agent            |
| 3     | Medium   | Test creation from natural language           |
| 4     | Small    | Human-readable post-run summary               |
| 5     | Trivial  | Paid LLM opt-in (litellm already wired)       |

Phases 1 + 2 are the foundation. Phases 3 + 4 are the user-facing value.
Phase 5 is a flag, not a feature.
