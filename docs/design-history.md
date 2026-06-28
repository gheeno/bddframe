# BDDFrame — Design History

The chronological record of how each capability was designed and built, condensed
from the original twelve phase documents. For how the framework works *today*, read
**[Architecture](architecture.md)** and the **[Guide](guide.md)** — those are kept
current; this page is the rationale trail behind them.

> Early phases (1–2) were written as forward-looking plans and use some names that
> changed during implementation (e.g. an early "LangGraph orchestrator" and a
> `parser/feature_loader.py` became the simpler `orchestrator/runner.py` +
> `resolver/`). Where a phase says "Plan", treat it as intent, not current code.
> The shipped surface is whatever Architecture/Guide and the `tests/` suite show.

| Phase | Topic | Status |
|-------|-------|--------|
| 1 | Foundation — parse, resolve, route | Done |
| 2 | Web agent — Playwright, intent locators, assertions | Done |
| 3 | CLI & hooks hardening — 6 correctness bugs | Done |
| 4 | Visual / desktop agent — OpenCV, OCR, PyAutoGUI | Done |
| 5 | Reporting — Allure JSON, JUnit XML, annotated shots | Done |
| 6 | CLI, recorder & Azure DevOps | Done |
| 7 | Syntax highlighting & editor (LSP) | Done |
| 8 | Test-development guide — feature/POM authoring | Done (guide) |
| 9 | Element disambiguation — ambiguity + page-scoped POM | Done (9.1–9.3; 9.4 deferred) |
| 10 | Foundry Local — local model on a locked-down network | Plan / research |
| 11 | Step-coverage expansion — keyboard, tables, asserts | Done (11.1–11.3; 11.4 deferred) |
| 12 | Step dependencies & shared state | Done (12.1–12.2; 12.3 deferred) |

---

## Phase 1 — Foundation

**Goal:** read a `.feature` file, understand each step, route it to the right agent.

- **behave** parses Gherkin; BDDFrame drives the steps through one catch-all (no per-step glue).
- **Variable substitution** — `[my email]` → `os.getenv("MY_EMAIL")`, before the step resolves. Missing vars stay literal + warn (handy for exploratory runs).
- **Two-tier resolver** — Tier 1 is regex pattern matching (most steps, no cost); Tier 2 hands the sentence to the LLM only on a miss.
- **LiteLLM** is the single model gateway — swap models with one env var.

The orchestrator was originally sketched as a LangGraph state machine; it shipped
as the straightforward `orchestrator/runner.py`. The two-tier resolver and
LiteLLM gateway carried through unchanged.

## Phase 2 — Web Agent

**Goal:** run web steps with Playwright; find elements by *what they are*, not by selector.

- **Intent locator chain** (`agents/web/locator.py`): `getByRole` → `getByLabel` → `getByText` → `getByPlaceholder` → `getByTitle`, stopping at the first hit. Step 6 (vision LLM) only fires when all five miss.
- **Assertions** split into **structural** (DOM text/url/title — never an LLM) and **semantic** (vision LLM judges a screenshot, and stores its reasoning as evidence).
- **Visual baseline** — `the screen should look the same as before` stores a *semantic description*, not pixels, so timestamps/avatars don't cause false diffs.
- **Self-healing** — re-scan, scroll, partial-text retry, then LLM as last resort; healing events are logged.
- Browser/engine/emulation selected by tags (`@firefox`, `@webkit`, `@mobile @iphone`, `@slow`, `@record_video`).

## Phase 3 — CLI & Hooks Hardening

**Goal:** close six correctness bugs found reviewing Phase 2, each with a concrete failure scenario.

1. **`BDDFRAME_HEADLESS` passthrough** — normalise any truthy value (`1`/`yes`/`on`) to canonical `true`/`false` so headless CI isn't silently downgraded to headed.
2. **`--headed` + `--headless` together** — now a hard error instead of a silent winner.
3. **`@headed` + `@headless` on one scenario** — emits a warning (priority `@headed` wins, but the conflict is surfaced).
4. **`BDDFRAME_BROWSER` validation** — bad values (`chrome`, `safari`) give a clear "unsupported browser" error, not a cryptic `AttributeError`.
5. **Hardcoded `features/` base** — the behave root is now derived from the passed path (nearest ancestor with `steps/` or `environment.py`), so non-standard layouts work.
6. **Cleanup leak** — per-resource `try/except` with guards in `after_scenario`, so a failed close no longer orphans Playwright processes.

Covered by `tests/test_cli_hardening.py` and `tests/test_hooks_hardening.py`.

## Phase 4 — Visual / Desktop Agent

**Goal:** automate anything on screen that isn't a browser DOM — desktop, Electron, Citrix, legacy.

- Tag `@visual` routes to `agents/visual/`. Three locator types:
  1. **Image match** — OpenCV `matchTemplate` against a reference PNG in `tests/assets/`, with DPI-scale variants (0.8×–1.2×).
  2. **OCR** — `pytesseract` reads on-screen text (grayscale + contrast preprocessing).
  3. **Description** — vision LLM coordinate fallback, gated on `BDDFRAME_VISION_MODEL`.
- **PyAutoGUI** performs click/type/key/drag/scroll; **mss** captures the screen.
- Failed image matches produce an annotated screenshot (searched region, best candidate + score). Web and visual steps can mix in one scenario.

## Phase 5 — Reporting

**Goal:** after every run, a report that shows what happened, where it failed, and a screenshot with the failure circled — in a format Azure DevOps reads natively.

- `reporting/writer.py` emits **Allure JSON** per step as it runs.
- `reporting/annotate.py` draws failure annotations with **Pillow** (red box for not-found, highlight + ✗ for assertion failures).
- `reporting/junit.py` writes **JUnit XML** (stdlib `xml.etree`) — Azure DevOps shows pass/fail counts with no plugin.
- `reporting/builder.py` shells out to the **Allure CLI** to render the HTML; `bddframe report open` / `generate` wrap it. Semantic-assertion reasoning is attached as evidence.

## Phase 6 — CLI, Recorder & Azure DevOps

**Goal:** one command to run, one to record, drop-in pipeline YAML.

- **Recorder** (`recorder/recorder.py`) — `bddframe record` opens a visible browser, watches navigate/click/fill events via Playwright, and writes human-readable steps (not raw selectors). `recorder/sensitives.py` auto-redacts emails/cards/passwords to `[VARIABLE]`.
- **CLI** (`cli.py`, Typer): `run` (`--headless`/`--headed`/`--tag`/`--browser`), `validate`, `list`, `record`, `report open`/`generate`.
- **Azure pipelines** — Linux (`azure-pipelines.yml`, Xvfb for headed/visual) and Windows (`azure-pipelines-windows.yml`, native GUI) templates that publish JUnit + Allure.

## Phase 7 — Syntax Highlighting & Editor

**Goal:** great `.feature` editing in VS Code with minimal new code.

- A **TextMate grammar** (`vscode-extension/syntaxes/bddframe.tmLanguage.json`) colours Gherkin keywords, `@tags`, and BDDFrame-specific `[variables]` (gold).
- A **pygls** language server (`lsp/server.py`) reads `resolver/patterns.py` directly, so step validation always reflects the real patterns. Unknown steps are **warnings, not errors** (the LLM may resolve them at runtime).
- `@tag` autocomplete and `[variable]` completion sourced from the project `.env`.
- The standard Cucumber extension conflicts (both bind `.feature`); disable it per workspace.

## Phase 8 — Test-Development Guide

**Goal:** explain how a QA writes feature files and when to write `pom.yaml`, especially across multi-page flows.

The key insight: the framework is **stateless about pages** — it acts on whatever
is in the browser when each step runs, so a multi-page journey needs no special
config. `pom.yaml` is needed *only* when an element can't be found by its natural
label. This content now lives in the **[Guide](guide.md)**.

## Phase 9 — Element Disambiguation

**Goal:** guarantee the framework acts on the *intended* element, not just the first match.

Two failure modes were fixed:

- **9.1 Ambiguity detection** — the accessibility path no longer blindly returns `.first`. On 2+ matches it consults the POM for a scoped entry first; with none, **lenient** mode (default) warns + uses first, **strict** mode (`BDDFRAME_STRICT_LOCATOR` / `@strict`) fails with the full candidate list. *This is the linchpin* — most wrong-element bugs were "ambiguous but found" cases that never reached the POM before.
- **9.2 URL page-scoped POM** — optional `pages:` / `shared:` blocks; `pom.locate` reads `page.url` and consults the matching block, so the same key resolves to different selectors per page. Flat files still work unchanged.
- **9.3 Page pinning** — `Given User is on the "X" page` for SPAs where the URL never changes.
- **9.4** (per-page POM files) deferred — YAGNI until one file actually hurts.

Rejected: container-language-in-Gherkin (heavy parser, duplicates a one-line POM
entry) and mandatory page names in every step (punishes the 95% unambiguous case).

## Phase 10 — Foundry Local

**Goal:** run a local model on a corporate network where Hugging Face *and* Ollama are blocked. **Status: plan / research.**

**Verdict:** it works, *because* Foundry Local avoids both blocks — it pulls
models from the Azure Foundry Catalog (not HF), is a separate runtime (not
Ollama), and its runtime installs via `winget`/`brew` (not pip). It exposes an
**OpenAI-compatible** endpoint.

The lazy finding for BDDFrame itself: its LLM fallback already runs on LiteLLM,
which already speaks OpenAI-compatible endpoints — so unblocking it needs **no new
framework, only `.env`**:

```bash
BDDFRAME_MODEL=openai/qwen2.5-7b-instruct-generic-cpu   # exact id from `foundry model list`
BDDFRAME_LLM_URL=http://localhost:<port>/v1
OPENAI_API_KEY=not-needed                               # local service ignores it
```

The heavier `agent-framework` + `MCPStdioTool` work (a genuinely agentic
MCP-driven browser agent) is reserved for when one-shot `ask()` isn't enough —
kept in a separate `uv` subproject so it never bloats BDDFrame's core install.

## Phase 11 — Step-Coverage Expansion

**Goal:** grow from a happy-path engine into a full-interaction engine without breaking "sentences over syntax".

The constraint: a new capability is **three edits** — a regex (`patterns.py`), an
action (`actions.py` + `runner.py`), and the action name added to the LLM prompt's
valid-action list (`step_resolver.py`); first-person verbs also need `_FIRST_TO_THIRD`.

- **11.1 Tier A** — keyboard keys, hover, wait-disappears, element value/state/**attribute** asserts (attribute covers SVG), count asserts, and `store_text` (capture element text into a run-scoped var).
- **11.2 Tier B** — D365 tables: row/cell scoping (`click "Edit" in the row containing "X"`), bounded container scoping (`the "Save" button in the "Payment" section`), and iframe `switch_frame`. All accessibility-first, no XPath in the sentence.
- **11.3 Docs** — shadow-DOM (`css`/`role` pierce, `xpath` doesn't; closed → vision), SVG authoring, container scoping. Folded into the Guide.
- **11.4** (video, canvas-click) deferred — YAGNI; semantic vision already answers "what does the chart show".

## Phase 12 — Step Dependencies & Shared State

**Goal:** let a value produced in one step be used by a later step, in plain Gherkin, with no DI container or expression engine.

`context._vars` (per-scenario, reset each scenario) **is** the scenario-scoped
bean; `[VAR]`/`` `var` `` substitution **is** the injection. Two delimiters by
design: `` `name` `` reads the **run store** (values captured during the test),
`[name]` reads **`.env`** (secrets/config).

- **12.1** — `set_var` (seed a literal), `store_attribute` (capture an attribute); `store_text` already existed from 11.1.
- **12.2** — `assert_compare` (`greater than` / `less than` / `equal` / `contain` / `not equal`); numeric if both sides parse, else string. This was the actual gap — storing + substitution already carried the dependency.
- **12.3** (computed expected values) deferred *and discouraged* — computing the expected value with the app's own logic re-implements the app and proves nothing. The app computes; the test observes.

Rejected throughout: a Spring-style DI container (nothing to inject into), an
expression mini-language (`${A+B}` turns the feature file into code), and
cross-scenario globals (makes tests order-dependent).
</content>
