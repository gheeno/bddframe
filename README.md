# BDDFrame

**QAs write a `.feature` file in plain sentences. BDDFrame does the rest.**

No selectors. No Page Object classes. No step definitions. No code.

```gherkin
@web @smoke
Scenario: Valid user can log in
  Given User is on "[SAUCEDEMO]"
  When User enters [SAUCE_USERNAME] in the username field
  And User enters [SAUCE_PASSWORD] in the password field
  And User clicks the login button
  Then User should see "Products"
```

`[SAUCEDEMO]` is a base URL from `environments.yaml`; `[SAUCE_USERNAME]` is a
secret from `secrets.env` (or Azure Key Vault). See [Configure](#configure).

That's the whole test — no Python, no `By.id`, no glue.

---

## Contents

1. [How it works](#how-it-works)
2. [Install](#install)
3. [Configure](#configure)
4. [Run the bundled test app (BusterBlock)](#run-the-bundled-test-app-busterblock)
5. [Write & run a test](#write--run-a-test)
6. [Preconditions & teardowns](#preconditions--teardowns)
7. [Run a script from a step](#run-a-script-from-a-step)
8. [Reports — what to expect](#reports--what-to-expect)
9. [The LLM — when it triggers](#the-llm--when-it-triggers)
10. [Docs](#docs)

---

## How it works

```mermaid
flowchart TD
    QA["QA Analyst\nwrites .feature file\nin plain sentences"]
    REC["bddframe record\ncaptures browser actions"]
    CFG["environments.yaml (base URLs)\nsecrets.env / Azure Key Vault (secrets)"]

    QA -->|hand-write| F["checkout.feature\nGherkin"]
    REC -->|auto-generates| F
    CFG -.->|[VAR] substitution| F

    F --> P["behave\nparses steps + retries flaky ones"]
    P --> SR["Step Resolver\n50+ built-in patterns\nno LLM cost"]

    SR -->|pattern matched| ROT{"Orchestrator\nroutes by tag"}
    SR -->|no match| LLM["LLM fallback\nopt-in via BDDFRAME_MODEL\nnever called if a pattern matches"]
    LLM --> ROT

    ROT -->|web tag| W["Web Agent\nPlaywright\nfinds elements by label / role / text"]
    ROT -->|visual tag| V["Visual Agent\nOpenCV + PyAutoGUI\ntemplate matching + OCR"]

    W --> C["Result Collector\npass / fail + screenshot"]
    V --> C

    C --> REP["Allure + JUnit XML\nannotated screenshots\ntrace.zip on failure\nhealing telemetry"]
    REP --> AZ["Azure DevOps\nTests tab · sharded across agents"]

    style QA       fill:#4a4a6a,color:#e8e8ff,stroke:#7a7aaa
    style REC      fill:#4a4a6a,color:#e8e8ff,stroke:#7a7aaa
    style CFG      fill:#4a4a6a,color:#e8e8ff,stroke:#7a7aaa
    style F        fill:#2d4a3e,color:#b8f5d8,stroke:#4aaa80
    style SR       fill:#3a3a3a,color:#d0d0d0,stroke:#666
    style LLM      fill:#4a3a2a,color:#f5d8b8,stroke:#aa804a,stroke-dasharray:4 4
    style ROT      fill:#3a3a3a,color:#d0d0d0,stroke:#666
    style W        fill:#1e3a5f,color:#b8d8f5,stroke:#4a80aa
    style V        fill:#1e3a5f,color:#b8d8f5,stroke:#4a80aa
    style REP      fill:#1e3a5f,color:#b8d8f5,stroke:#4a80aa
    style AZ       fill:#1e3a5f,color:#b8d8f5,stroke:#4a80aa
```

1. `behave` parses the `.feature` file into steps (and retries flaky scenarios — see [Run](#write--run-a-test)).
2. The resolver matches each step against 50+ built-in patterns — **no LLM call**.
3. The orchestrator routes by scenario tag (`@web`, `@visual`).
4. The web agent finds elements by what they *are* (visible label, ARIA role, text) — no CSS selectors. Ambiguous? It consults `pom.yaml`, then warns (or fails under strict mode) rather than guessing. Self-heals are recorded to a `healing.jsonl` telemetry log.
5. On failure: an annotated screenshot **and a Playwright `trace.zip`** (open with `playwright show-trace`) are captured and embedded in the Allure report.

> **There is no LLM by default.** With no `BDDFRAME_MODEL` set, BDDFrame is fully
> local (patterns + Playwright + POM + OpenCV) and anything it can't resolve fails
> loudly. LLM layers switch on only when you opt in — see [The LLM](#the-llm--when-it-triggers).

Full deep dive (study it like Selenium/Appium/Selenide): **[docs/architecture.md](docs/architecture.md)**.

---

## Install

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/) (the repo ships
`uv.lock`; plain `pip` works too).

```bash
git clone https://github.com/gheeno/bddframe.git
cd bddframe

uv pip install -e ".[all]"      # or: pip install -e ".[all]"
playwright install chromium
```

Core only? `uv pip install -e .`. Or pick extras: `llm`, `reporting`, `visual`,
`lsp`. For Allure reports also install the CLI: `brew install allure`
([other platforms](https://allurereport.org/docs/install/)).

---

## Configure

Config lives in **three files** by purpose, so secrets never sit next to base
URLs and CI can swap them independently:

| File | Holds | Committed? |
|------|-------|------------|
| `environments.yaml` | base URLs per environment (`[SAUCEDEMO]`, `[STAGING]`) | ✅ yes |
| `secrets.env` | credentials / tokens (`[SAUCE_USERNAME]`) — or [Azure Key Vault](docs/guide.md#secrets--azure-key-vault) | ❌ gitignored |
| `.env` | browser & run settings (no secrets) | ✅ yes |

```bash
cp .env.example .env                 # run/browser settings
cp secrets.env.example secrets.env   # then fill in your credentials
```

```yaml
# environments.yaml — base URLs (referenced as [SAUCEDEMO] in features)
saucedemo: https://www.saucedemo.com
staging:   https://staging.example.com
```

```bash
# .env — settings only, NO secrets
BDDFRAME_BROWSER=chromium        # chromium | firefox | webkit
BDDFRAME_HEADLESS=false          # true in CI
BDDFRAME_STRICT_LOCATOR=false    # true = ambiguous locators FAIL (recommended in CI)
BDDFRAME_RETRIES=1               # re-run a failed scenario N extra times
```

Any `[variable]` in a feature maps to the matching key (uppercased, spaces →
underscores): `[sauce username]` → `SAUCE_USERNAME`. Resolution order, highest
wins: **Key Vault** (if `BDDFRAME_KEYVAULT_URL` set) → **shell / CI variables** →
`.env` → `secrets.env` → `environments.yaml`.

Full setup — LLM vars, Key Vault, all toggles — is in the **[Guide](docs/guide.md#2-configure)**.

---

## Run the bundled test app (BusterBlock)

`test-app-vhs-vault/` is **BusterBlock.ca** — a self-contained VHS-rental site
(Node/Express, in-memory data) that the `features/busterblock/` tests run
against. Run it locally so those features have something to hit:

```bash
cd test-app-vhs-vault
npm install            # first time only
npm start              # serves http://localhost:3333
```

You should see `🎬  BusterBlock.ca  →  http://localhost:3333`. Leave it running
in one terminal; run tests in another:

```bash
bddframe run features/busterblock/login.feature
```

`http://localhost:3333` is wired to the `[BUSTERBLOCK]` reference via
`environments.yaml`; the demo login (`reel_ryan` / `Popcorn1!`) is in
`secrets.env.example` as `BB_USER` / `BB_PASS`. Data is in-memory and reloads on
restart — see the [test seam](#preconditions--teardowns) for seeding it per test.

---

## Write & run a test

Feature files live in `features/`, one subfolder per app. The bundled
`features/saucedemo/checkout.feature` is a complete end-to-end purchase. Run it:

```bash
bddframe run features/saucedemo/checkout.feature
```

Common commands:

```bash
bddframe run                          # all features
bddframe run features/saucedemo/      # a folder
bddframe run --tag smoke              # only @smoke
bddframe run --headless               # no visible browser
bddframe run --browser firefox        # chromium | firefox | webkit
bddframe run --retries 2              # re-run a failed scenario up to 2x (flaky guard)
bddframe run --log-level WARNING      # quieter output (DEBUG|INFO|WARNING|ERROR)
bddframe list                         # discovered scenarios (no browser)
bddframe validate                     # check syntax + [variables] (no browser)
bddframe record --output features/myapp/login.feature --name "Login Flow"
```

**Flaky-test handling:** failed scenarios are retried once by default
(`BDDFRAME_RETRIES`, only fires on failure). Tag a scenario `@no_retry` to opt
out, or `@quarantine` to keep it running but **non-blocking** — quarantined
failures don't fail the build.

### Parallel / sharded runs

BDDFrame parallelizes by **sharding feature folders across agents** (behave
itself is single-process, so each shard is a separate process with its own
workspace and `allure-results/`). In Azure DevOps a matrix runs one folder per
agent and the Tests tab aggregates them — see
[`azure-pipelines.yml`](azure-pipelines.yml) and the
[Guide → CI](docs/guide.md#11-ci--azure-devops). Because a run rewrites
`allure-results/`, don't run two shards against the same working directory; give
each its own checkout (what the CI matrix does automatically).

`bddframe record` opens a browser, watches you click through a flow, and writes
the `.feature` file (sensitive values auto-redacted to `[VARIABLE]`).

The full step reference, browser tags, `pom.yaml`, and shared-state syntax are in
the **[Guide](docs/guide.md)**.

---

## Preconditions & teardowns

Like a JDBC `@Before`/`@After` in Java: instead of clicking the UI into the state
you need, **seed the data directly, run the test, then clean up**. Tag a scenario
`@precondition:NAME` — its `setup:` calls run before the scenario, its `teardown:`
calls run after (**even if the scenario fails**).

Fixtures live in `preconditions.yaml` next to the feature. Each line is
`METHOD URL [JSON-body]`; `[BUSTERBLOCK]` resolves from `environments.yaml`:

```yaml
# features/busterblock/preconditions.yaml
jaws_out_of_stock:
  setup:
    - POST [BUSTERBLOCK]/api/test/reset
    - 'PATCH [BUSTERBLOCK]/api/test/stock {"movieId": 1, "stock": 0}'
  teardown:
    - POST [BUSTERBLOCK]/api/test/reset
```

```gherkin
# features/busterblock/preconditions.feature
@web
Feature: Preconditions — seed BusterBlock data before the UI test

  @smoke @precondition:jaws_out_of_stock
  Scenario: A movie seeded out of stock shows "Out" in the catalog
    # Precondition forced Jaws to stock 0 before this ran — no UI did that.
    ...
    Then the cell in row "Jaws" column "Stock" should be "Out"
```

**The test seam.** BusterBlock has no SQL DB — its "database" is in-memory state
in `server.js`. Test-only endpoints expose it for seeding (gated by `BB_TEST_API`,
on by default; set `BB_TEST_API=0` to disable):

| Endpoint | Body | Does |
|----------|------|------|
| `POST /api/test/reset` | — | empty carts + orders, restore all stock (the universal teardown) |
| `PATCH /api/test/stock` | `{movieId, stock}` | force a movie's stock (e.g. 0) |
| `POST /api/test/seed-cart` | `{username, items}` | pre-fill a user's cart |

Run the worked example (BusterBlock must be running):

```bash
bddframe run features/busterblock/preconditions.feature
```

Design rationale and the phase plan: **[docs/preconditions-plan.md](docs/preconditions-plan.md)**.

---

## Run a script from a step

When a test needs something the browser can't do — seed a database, run a Java
jar, call a shell tool — invoke **any external script or command as a step**. No
glue code: the interpreter is inferred from the file extension, and a non-zero
exit **fails the step** (so a broken setup script fails the test loudly).

```gherkin
Given the script "scripts/seed_db.py" runs
And `SCRIPT_OUTPUT` should contain "seeded 42 rows"
When User is on "[BUSTERBLOCK]"
Then the cell in row "Jaws" column "Stock" should be "Out"
```

**Phrasings:**

| Step | Runs |
|------|------|
| `the script "path/x.py" runs` (or `… executes`) | infer interpreter, no args |
| `run the script "x.jar" with "--env staging"` | with arguments |
| `run the script "x.py" with "[BUSTERBLOCK]" storing the output as` `` `RESULT` `` | capture stdout into a named var |
| `run the command "java -jar tool.jar [BUSTERBLOCK]"` | arbitrary shell command |

**Interpreter inference** (by extension): `.py` → the venv Python · `.js`/`.mjs`
→ `node` · `.jar` → `java -jar` · `.sh` → `bash` · `.rb` → `ruby` · `.pl` →
`perl` · anything else → run the file directly (must be executable). `[VAR]`
references in the path/args/command are substituted from config first, so a
script can be handed `[BUSTERBLOCK]`.

**Using the result.** stdout is captured into `` `SCRIPT_OUTPUT` `` (and any var
you name with `storing the output as`), so a later step can assert on it:
`` `SCRIPT_OUTPUT` should contain "…" ``. Timeout is `BDDFRAME_SCRIPT_TIMEOUT`
(default 60s).

> **Trust boundary:** feature files are trusted code, like step definitions —
> `run the command` uses a shell. Don't drive these steps from untrusted input.

Worked example (BusterBlock must be running) — a Python script forces a movie out
of stock, then the UI is asserted:

```bash
bddframe run features/busterblock/run_script.feature
```

---

## Reports — what to expect

Per run:

- Pass/fail printed per scenario.
- On failure: `screenshots/FAILED_<step>.png` (annotated) **+ `traces/<scenario>.zip`** — a full Playwright trace (DOM snapshots, network, timeline). Open it with `playwright show-trace traces/<scenario>.zip`.
- If any locator self-healed: `healing.jsonl` + a `healing-report.txt` with `pom.yaml` suggestions to make it deterministic.
- With `[reporting]`: Allure JSON written to `allure-results/` automatically.

```bash
bddframe report generate     # allure-results/ → allure-report/ (HTML)
bddframe report open         # build + open in a browser
```

> You can't double-click `allure-report/index.html` — it loads data over XHR,
> blocked on `file://`. The commands above serve it over HTTP.

The report shows: overview (pass/fail/skip + trend), suites (feature → scenario →
step), each failed step with error + annotated screenshot, and a timeline. In CI
the JUnit XML at `allure-results/junit.xml` drives the Azure DevOps **Tests tab**.
See the **[Guide → Reports](docs/guide.md#8-reports)** and
**[CI](docs/guide.md#11-ci--azure-devops)**.

---

## Enterprise & CI

Built for running at scale in Azure DevOps. Each item links to the detail:

| Capability | How |
|------------|-----|
| **Parallel execution** | Feature-folder sharding across CI agents — [Guide → CI](docs/guide.md#11-ci--azure-devops) |
| **Flaky-test retries** | `--retries` / `BDDFRAME_RETRIES`; `@no_retry`, `@quarantine` (non-blocking) |
| **Failure traces** | Playwright `trace.zip` per failed scenario, published as a CI artifact |
| **Deterministic visual diff** | `the screen should match the baseline` — pixel diff via Pillow, no LLM |
| **Secrets in Azure Key Vault** | `BDDFRAME_KEYVAULT_URL` + `pip install -e ".[azure]"` — [Guide → Secrets](docs/guide.md#secrets--azure-key-vault) |
| **Self-heal telemetry** | `healing.jsonl` + `pom.yaml` suggestions for every healed locator |
| **Reproducible runner** | `Dockerfile` (browsers preinstalled) + `.devcontainer/` |

```bash
# Run the whole suite in the reproducible container
docker build -t bddframe . && docker run --rm bddframe
```

The full gap analysis and what was built is in
**[docs/enterprise-plan.md](docs/enterprise-plan.md)**.

---

## The LLM — when it triggers

**Off by default.** No env var → no model call; the framework is fully local and
deterministic, and an unresolvable step **fails with a screenshot**. When enabled,
the LLM is only ever a *fallback* — it never runs if a local layer already
resolved the step.

BDDFrame is **model-agnostic** via [LiteLLM](https://github.com/BerriAI/litellm) —
point it at Ollama, hosted OpenAI, or [Foundry Local](https://learn.microsoft.com/azure/foundry-local/)
with one env var:

```bash
uv pip install -e ".[llm]"
# .env — pick one:
BDDFRAME_MODEL=ollama/llama3            # local, free
BDDFRAME_LLM_URL=http://localhost:11434
# BDDFRAME_MODEL=openai/gpt-4o-mini ; BDDFRAME_LLM_URL=https://api.openai.com/v1 ; OPENAI_API_KEY=sk-...
```

**The four triggers** — each is a local layer missing *and* the env var being set:

| # | When the local layer misses | Gate |
|---|------------------------------|------|
| 1 | No regex pattern matches the sentence | `BDDFRAME_MODEL` |
| 2 | Web element not found by accessibility + `pom.yaml` | `BDDFRAME_MODEL` |
| 3 | Semantic / visual-baseline assertion (always uses the model) | `BDDFRAME_MODEL` |
| 4 | `@visual` image not found by OpenCV/OCR | `BDDFRAME_VISION_MODEL` |

Vision features (triggers 2–4) need a vision-capable model (`openai/gpt-4o`,
`ollama/llava`).

**The sample test that invokes the LLM:** `features/fallback-demo/llm_fallback.feature`.
Every step resolves locally except one —

```gherkin
When User submits the login form     # verb "submit" is in no pattern → Trigger 1 → model
```

— so the resolver hands it to the model, which returns a click action. With
`BDDFRAME_MODEL` unset, that step fails by design. Run it:

```bash
bddframe run features/fallback-demo/llm_fallback.feature --headed
```

Full detail (client module, prompts, diagrams): **[docs/architecture.md → The LLM layer](docs/architecture.md#5-the-llm-layer)**.

---

## Run BDDFrame's own tests

```bash
make test            # == python -m pytest unit_tests/ -v
```

**Expected: 212 passed, 0 failed** — no browser, no LLM, no display required.

---

## Docs

| Doc | For |
|-----|-----|
| **[Guide](docs/guide.md)** | New & veteran testers — install → write → run → `pom.yaml` → shared state → reports → CI → editor. |
| **[Architecture](docs/architecture.md)** | The tech, end to end — mental model, component map, resolution hierarchy, the LLM layer, tech stack (Mermaid throughout). |
| **[Design History](docs/design-history.md)** | The rationale trail behind every capability (the 12 build phases, condensed). |
| **[Enterprise Plan](docs/enterprise-plan.md)** | Enterprise-grade gap analysis + what was built (parallelism, retries, traces, Key Vault, healing telemetry, Docker). |
| **[Preconditions Plan](docs/preconditions-plan.md)** | The phase plan + rationale for tag-driven data preconditions & teardowns (the JDBC-fixture analog). |
| **[docs/](docs/README.md)** | Documentation index. |
</content>
