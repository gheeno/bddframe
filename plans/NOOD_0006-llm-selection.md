# NOOD_0006 — LLM Selection for Noodle Test Framework

> **Status:** Draft — recommendation only, no code changes yet.
> This plan identifies the best default local LLM, the best backup if the
> local LLM is down/offline, and the best cost-effective cloud LLM (Claude /
> Copilot / Gemini), for the three jobs the framework can hand to a model:
> writing new test cases, running tests / interacting with the agent, and
> reviewing report output. It also checks whether any LLM can spin up the
> app-under-test, and lists the gaps that exist independent of model choice.

---

## Current state (grounding)

Noodle's LLM layer is intentionally thin — one gateway module, two functions:

| Function | Purpose | Reads |
|---|---|---|
| `ask(prompt) -> str` | Step-JSON resolution (`resolver/step_resolver.py`) | `NOODLE_MODEL`, `NOODLE_LLM_URL` |
| `ask_vision(prompt, image_b64) -> str` | Locator fallback, semantic assertions, RCA | `NOODLE_MODEL`, `NOODLE_LLM_URL` |

Everything routes through **LiteLLM**, so any provider (Ollama, Anthropic,
Gemini, Groq, OpenAI, Foundry Local) works via one `<provider>/<model>` string
with zero code changes. The framework is local and deterministic by default —
**no `NOODLE_MODEL` set means no LLM call, ever** (`docs/architecture.md` §1,
§8). The LLM is a labelled fallback at four trigger points (`docs/architecture.md`
§5), not a default path.

Separately, `noodle-agent` (`QUICK_START_AGENTIC.md`) is a rule-based REPL for
test creation / running / summaries. It costs $0 by default and only touches
a model when `--llm ollama|claude|gemini` is passed, for two jobs: richer
`create test` generation and richer `summary` narratives.

---

## 1. Default local LLM

`NOODLE_MODEL` is a **single** value shared by both `ask()` (text) and
`ask_vision()` (vision) — there is no separate "text model" / "vision model"
knob for the web path (only the `@visual` desktop path gets its own
`NOODLE_VISION_MODEL`). So the "best default" depends on which of the two the
workspace actually exercises more:

| Workload | Recommended default | Why |
|---|---|---|
| Step resolution (JSON action dict, `step_resolver.py`) | `ollama/qwen2.5-coder:7b` (or `:14b` with more VRAM) | Tuned for structured/code output — matches the fence-stripped JSON contract `_parse_action()` expects. Cuts hallucinated `type`/param names that would otherwise trip the `VALID_TYPES` guard or crash `runner.py` with a confusing `KeyError` instead of a clean `AssertionError`. |
| Vision (locator fallback, semantic assert, `NOODLE_RCA`) | `ollama/qwen2.5vl:7b` | Strongest open-weight vision model Ollama currently serves well. Fallback if VRAM is tight: `ollama/llama3.2-vision`. |

**Recommendation:**
- Web/DOM-heavy suites (LLM rarely triggers, and only ever for step-JSON) →
  default `NOODLE_MODEL=ollama/qwen2.5-coder:7b`.
- Suites leaning on vision-locate / semantic assertions / RCA → default
  `NOODLE_MODEL=ollama/qwen2.5vl:7b` (it's a VL model, so plain-text JSON
  still works reasonably — you're trading some JSON-strictness for vision
  quality).

Sizing guidance: 7B ≈ 8GB VRAM, 14B ≈ 16GB, 32B ≈ 24GB+. Start at 7B; move up
only if step-JSON hallucination or locator misses show up in `healing.jsonl`.

---

## 2. Backup if the local LLM is down or offline

LiteLLM makes swapping providers a one-line `.env` change, but Noodle has
**no automatic failover** — nothing retries a different provider on a
connection error. Pick a backup deliberately, ahead of time:

| Tier | Model | Notes |
|---|---|---|
| Free | `gemini/gemini-2.0-flash` (or current Gemini Flash) | Already the framework's documented free/vision-capable fallback (`docs/architecture.md` config recap). |
| Paid, more reliable | `anthropic/claude-haiku-4-5` | $1/$5 per MTok, fast, vision-capable. Also brings GA structured-outputs support (`strict: true` tool schemas), which could eventually replace the regex/fence JSON-extraction in `_parse_action()` entirely. |

---

## 3. Cost-effective cloud LLM — Claude vs. Copilot vs. Gemini

Noodle's LLM usage is a narrow **single-call** fallback (JSON-in/JSON-out, or
screenshot-in/verdict-out), not an agentic workload — so cost-per-call and
schema reliability matter more than raw model intelligence.

- **Claude Haiku 4.5** ($1/$5 per MTok) — the standout choice for the
  *runtime* fallback path: cheap, vision-capable, and its structured-outputs
  support is a better fit for `step_resolver`'s JSON contract than
  prompt-and-hope regex extraction.
- **Claude Sonnet 5** ($2/$10 intro pricing through 2026-08-31, $3/$15
  standard) — the right step-up for `noodle-agent --llm claude` when actually
  *authoring* `.feature`/POM files or narrating RCA/report summaries, where
  output quality matters more than per-call cost.
- **Gemini Flash** — cheapest/free option, already the framework's documented
  default free tier. Fine if cost is the only axis and schema rigor doesn't
  matter as much.
- **GitHub Copilot** — not a fit for the runtime LLM path at all. It has no
  completions endpoint LiteLLM can target for a per-step JSON fallback.
  Copilot's actual role here is IDE-side, via the VS Code extension + LSP
  Noodle already ships (`noodle/lsp/`), helping a human author `.feature`
  files — not the resolver loop.

**Bottom line:** Claude Haiku 4.5 for the runtime fallback path (`NOODLE_MODEL`),
Claude Sonnet 5 for test authoring / report narration (`noodle-agent --llm claude`).

---

## Capability check

| Task | Local LLM capable? |
|---|---|
| Writing new tests (`noodle-agent create test --llm ollama`) | Yes — `qwen2.5-coder` generates Gherkin fine. |
| Running tests / interacting with the agent | Doesn't need an LLM at all — `run`/`list`/`summary` are rule-based, $0, fully offline by design. |
| Reviewing report output (`summary --llm`, `NOODLE_RCA`) | Yes — bounded narrative/classification tasks suit a local model well. |
| **Spinning up the test-app** | **No framework support, local or cloud.** No environment-lifecycle primitive exists — only `run_command`/`run_script` (arbitrary shell, must be authored into a step) or `@precondition` (HTTP-only data seeding against an *already-running* app). An LLM could be told to emit a `run_command: docker compose up -d` step in full-LLM mode, but there is no readiness/health-check wait and no teardown-on-failure for a spun-up process. |

---

## Gaps and weaknesses (independent of model choice)

1. **One `NOODLE_MODEL` for both text and web-vision.** Can't independently
   pick "best at JSON" vs. "best at vision" for the same run without
   accepting a compromise model.
2. **No app-lifecycle primitive.** Starting/stopping the app-under-test is
   entirely DIY via `run_command`, with no readiness gate or guaranteed
   teardown — contrast with `@precondition`'s teardown-even-on-failure
   guarantee for data.
3. **JSON extraction, not schema enforcement.** `_parse_action()`
   (`step_resolver.py`) and `rca.parse()` both use fence-stripping/regex
   rather than provider-native structured outputs. Works, but is inherently
   more fragile than `strict: true` tool schemas (Claude) or JSON-mode.
4. **`NOODLE_LLM_MODE=full` has no cost/latency guard.** Every step becomes
   an LLM call with no batching and no caching of repeated identical step
   text across scenarios.
5. **No automatic failover.** LiteLLM makes switching providers trivial, but
   nothing in Noodle retries a different model on a local-model connection
   failure — that's entirely on the operator.
6. **RCA fails silently, with zero log line.** `noodle/rca.py:102` —
   `review()` wraps everything in `except Exception: return None` with no
   log. Compare `agents/web/locator.py`'s vision-locate, which logs a `⚠️`
   warning on failure (added in BFRAME_0031). A flaky or wrong local vision
   model degrades to "no RCA label" with no visibility trail at all.

---

## Open questions

1. Should `NOODLE_MODEL` be split into `NOODLE_MODEL` (text) and
   `NOODLE_MODEL_VISION` (web vision), mirroring the existing
   `NOODLE_VISION_MODEL` split for the `@visual` desktop path?
2. Is an app-lifecycle primitive (start/health-check/teardown) worth adding
   as a first-class step family, or is `run_command` + `@precondition`
   sufficient with better documentation?
3. Should `rca.review()` gain the same `⚠️` warning-on-failure logging that
   `locator._vision_locate()` already has?
