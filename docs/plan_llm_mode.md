# BFRAME_0031 — Full LLM Mode Toggle

> **Status:** Implemented (BFRAME_0031). All SA conditions applied — see the
> "Implementation notes" section at the end.
> This plan covers adding a `BDDFRAME_LLM_MODE=full` toggle so the framework can
> bypass all local heuristics and delegate every step to a language model.

---

## Current state

Noodle Test Framework resolves a step through four sequential local layers before touching a model:

| Layer | Module | LLM condition |
|-------|--------|---------------|
| ① Pattern match (50+ regex) | `resolver/patterns.py` | Skipped only if no regex matches AND `BDDFRAME_MODEL` is set |
| ② Accessibility tree | `agents/web/locator.py` | Skipped only if element not found AND model set |
| ③ POM YAML lookup | `agents/web/pom.py` | Skipped only if still not found AND model set |
| ④ Playwright / stdlib action | `runner.py`, `rest_client.py` | Never — execution is always local |

The LLM is currently a **last-resort fallback**. There is no way today to say
"skip the heuristics entirely and let the model drive."

### What already works

- LiteLLM is the single LLM gateway — it already speaks Ollama, OpenAI, Anthropic,
  Google Vertex, Foundry Local, and every OpenAI-compatible endpoint with zero code
  changes.
- `step_resolver._llm_resolve()` exists and validates the model's JSON against
  `VALID_TYPES`.
- `locator.py` already calls `ask_vision()` as a last resort.

### Gaps that block "full LLM mode"

| Gap | Impact |
|-----|--------|
| No mode flag — patterns always run first | Can't skip to LLM |
| `_llm_resolve` prompt omits REST action types | REST steps fail LLM resolution |
| No locator bypass — accessibility always runs first | Slow in full-LLM mode; vision model called too late |
| Claude / Anthropic not documented as a provider | Users don't know it works |
| Free model options not documented | Users assume it requires a paid key |

---

## Proposed solution — four phases

### Phase 1 — `BDDFRAME_LLM_MODE` toggle (step resolver)

**The one-line env change that enables full LLM resolution.**

Add `BDDFRAME_LLM_MODE` to `.env`:

```bash
# auto (default) — patterns first, LLM only on no-match
BDDFRAME_LLM_MODE=auto

# full — every step goes straight to the LLM; patterns are skipped
BDDFRAME_LLM_MODE=full
```

**What changes:**

`noodle/resolver/step_resolver.py` — `resolve()` checks the flag:

```python
def resolve(step_text: str) -> dict:
    mode = os.getenv('BDDFRAME_LLM_MODE', 'auto').lower()
    if mode != 'full':
        # Current path: pattern match first
        normalized = normalize_subject(step_text)
        result = pattern_match(normalized)
        if result:
            action_type, params = result
            return {'type': action_type, **params}

    if os.getenv('BDDFRAME_MODEL'):
        return _llm_resolve(step_text)

    raise AssertionError(...)
```

**REST coverage fix (same phase):** `_llm_resolve`'s prompt currently lists only
web action types. Extend it to include all REST types (`rest_call`,
`rest_assert_status`, `rest_assert_body`, `rest_assert_header`,
`rest_extract_json`, `rest_set_header`, `rest_assert_body_table`,
`rest_assert_header_table`) so REST steps work in `full` mode without patterns.

**Files touched:** `step_resolver.py` only.

---

### Phase 2 — LLM-first locator strategy

**Lets the model find elements by description instead of by accessibility tree.**

When `BDDFRAME_LLM_MODE=full`, `locator.find()` skips the accessibility scan and
calls `ask_vision()` directly with the current screenshot. The existing vision-locate
path in `locator.py` does this today — it just needs to be promoted from last-resort
to first-attempt when the flag is set.

Safety net: if vision-locate returns `None` (model uncertain), fall back to the
accessibility tree anyway — the step never hard-fails just because the model was
unsure.

```
full mode locator order:
  1. ask_vision() → CSS selector
  2. If None → accessibility tree (safety net, not advertised)
```

```
auto mode (unchanged):
  1. Accessibility tree
  2. Self-heal + POM
  3. ask_vision()
```

**Files touched:** `agents/web/locator.py` only.

**Requires:** `BDDFRAME_MODEL` to be a vision-capable model (llava, gpt-4o,
anthropic/claude-sonnet-4-6, gemini/gemini-1.5-flash, etc.).

---

### Phase 3 — REST LLM mode

The stdlib `rest_client.py` **executes** requests — it is not replaced. The only
gap is that the step resolver must know how to turn a plain-English REST step into
a `rest_call` / `rest_assert_*` action dict when running in `full` mode.

Phase 1 already fixes the prompt. No additional code change is needed for REST.

What the model needs to produce (example):

```
Step:   "When performs a POST call at '/users' with body '{"name":"Alice"}'"
Action: {"type": "rest_call", "method": "POST", "path": "/users",
         "body": "{\"name\":\"Alice\"}", "var": null}
```

The execution path through `runner.py` → `rest_client.py` is unchanged.

**Files touched:** none beyond Phase 1 (prompt extension covers REST).

---

### Phase 4 — Provider documentation

LiteLLM already supports every provider below. This phase adds `.env.example`
entries and guide/architecture updates so users know what to put in their config.

#### Free / local options

| Provider | Model string | Notes |
|----------|--------------|-------|
| **Ollama** | `ollama/llama3` | Already documented. |
| **Ollama (vision)** | `ollama/llava` | Already documented. |
| **Foundry Local** | `openai/<model-id>` | Already documented. |
| **Google Gemini** | `gemini/gemini-1.5-flash` | Free tier. Set `GEMINI_API_KEY`. No `BDDFRAME_LLM_URL` needed. |
| **Groq** | `groq/llama-3.1-8b-instant` | Free tier. Set `GROQ_API_KEY`. Very fast. |

#### Paid / hosted options

| Provider | Model string | Notes |
|----------|--------------|-------|
| **OpenAI** | `openai/gpt-4o-mini` | Already documented. |
| **Anthropic Claude** | `anthropic/claude-sonnet-4-6` | Set `ANTHROPIC_API_KEY`. Vision-capable. |
| **Anthropic Claude (fast)** | `anthropic/claude-haiku-4-5-20251001` | Cheapest Claude. |

Example `.env` additions:

```bash
# Claude (Anthropic) — vision-capable, recommended for full mode
# BDDFRAME_MODEL=anthropic/claude-sonnet-4-6
# ANTHROPIC_API_KEY=sk-ant-...

# Gemini Flash — free tier, vision-capable
# BDDFRAME_MODEL=gemini/gemini-1.5-flash
# GEMINI_API_KEY=...

# Groq — free tier, text only (no vision)
# BDDFRAME_MODEL=groq/llama-3.1-8b-instant
# GROQ_API_KEY=...
```

---

## Architecture summary — mode comparison

```
auto (default, current):
  .feature step
       ↓
  Pattern match (50+ regex) ──────→ action dict
       ↓ no match
  LLM ask() ──────────────────────→ action dict
       ↓
  Playwright: accessibility → POM → ask_vision() → action

full (new toggle):
  .feature step
       ↓
  LLM ask() ──────────────────────→ action dict  (patterns skipped)
       ↓
  Playwright: ask_vision() → accessibility fallback → action
```

---

## What is NOT changing

- `rest_client.py` (stdlib HTTP) — unchanged; the LLM resolves steps, it does not
  make HTTP calls.
- `actions.py` — unchanged; the execution layer is always Playwright/stdlib.
- `catch_all.py` — unchanged; the `@visual` routing is not affected.
- The `auto` mode path — unchanged; existing tests run identically with no config.

---

## Risk assessment

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| LLM returns wrong action type | Medium | `VALID_TYPES` guard already in `_llm_resolve` |
| Vision model returns bad CSS selector | Medium | Locator safety-net fallback (Phase 2) |
| REST body with special chars fails LLM JSON | Medium | Existing `_parse_action` JSON-extraction handles fences/prose |
| Model cost spikes in full mode | High | Clearly document; recommend `auto` for CI |
| `full` mode slower (1 LLM call per step) | High | Expected trade-off; document latency |
| Free models (Groq/Gemini) rate-limited in CI | Medium | Document; use paid model for CI |

---

## Phase rollout summary

| Phase | What ships | Files | Est. size |
|-------|-----------|-------|-----------|
| 1 | `BDDFRAME_LLM_MODE=full` toggle + REST prompt extension | `step_resolver.py`, `.env.example` | ~30 lines |
| 2 | LLM-first locator in full mode | `locator.py` | ~15 lines |
| 4 | Provider docs (Claude, Gemini, Groq) | `.env.example`, `guide.md`, `architecture.md` | docs only |

> Phase 3 (REST) is folded into Phase 1 — the prompt extension is the only change
> REST needs; `rest_client.py` execution is untouched. It is not a separate phase.

---

## Reviewer notes (Solution Architect)

See the SA review below this document.

---

## Open questions

1. Should `full` mode also skip semantic assertions that always require the model?
   (They already require `BDDFRAME_MODEL`, so arguably no change is needed there.)
2. Should there be a per-scenario `@llm_mode_full` tag as an alternative to the
   global env toggle?
3. For REST in `full` mode: should the LLM also be allowed to set headers and
   extract JSON, or is that pattern-only for safety?

---

## Solution Architect Review

### Verdict

**APPROVED WITH CONDITIONS** — the architecture is sound and the footprint is small,
but three gaps must be closed before implementation begins. None require rethinking
the design; they are prompt-engineering, guard-clause, and config-clarity fixes.

---

### Strengths

- **Rollback is zero-cost.** `auto` is the default; existing runs are unaffected.
  Removing `BDDFRAME_LLM_MODE=full` from `.env` fully reverts behaviour.
- **Minimal diff.** Two files (`step_resolver.py`, `locator.py`) carry 95% of the
  code change. The execution layer (`runner.py`, `rest_client.py`, `actions.py`) is
  untouched — the LLM resolves intent, Playwright/stdlib still executes.
- **VALID_TYPES guard is already in place.** A hallucinated action type from the
  model raises a clear `AssertionError` before execution. This is the right safety
  contract and it holds in `full` mode without any extra work.
- **Vision-locate safety net (Phase 2) is the right call.** Falling back to the
  accessibility tree when the model returns `None` means `full` mode never produces
  a harder failure than `auto` mode on a locator miss.
- **LiteLLM is already the gateway.** Zero provider coupling in the code; Phase 4
  is genuinely documentation-only.

---

### Concerns

**[critical] `_llm_resolve` prompt is too sparse for REST action types.**
Adding the REST type names to the prompt is not enough. The model also needs the
parameter schema for each type. `rest_call` needs `method`, `path`, `body`, `var`.
`rest_assert_status` needs `expected` (integer). `rest_extract_json` needs `key`
and `var`. Without this, the model will hallucinate parameter names (e.g. `url`
instead of `path`, `status_code` instead of `expected`) and `runner.py` will crash
with a `KeyError` — not an `AssertionError` — which produces a confusing traceback
rather than a useful test failure.

Additionally, `rest_assert_body_table` and `rest_assert_header_table` take **zero
parameters** — they read `context.table` at runtime. Including them in the LLM
prompt risks the model returning `{"type": "rest_assert_body_table", "keys": [...]}`,
which `runner.py` ignores silently, then crashes when `context.table` is `None`
because no Gherkin data table was attached. These two types should be **excluded from
the LLM prompt entirely** and remain pattern-only; their matching pattern is
unambiguous (step ends with `:`).

**[major] Phase 2 has no guard for text-only models.**
`BDDFRAME_MODEL=groq/llama-3.1-8b-instant` is documented in Phase 4 as a valid
choice. Groq/Llama is text-only — `ask_vision()` will raise when it tries to send
an image. The current `_vision_locate` already wraps the call in `except Exception:
pass`, so it silently returns `None` and falls back to accessibility. But in
`full` mode, the intent is for the LLM to drive locating. Users who set `full` mode
with a text-only model will see `full` mode silently degrade to `auto` mode for all
element lookups with no log line explaining why. Add a `logger.warning` in
`_vision_locate` when the model is set but the `ask_vision` call fails, and add a
note in the docs: *"Phase 2 (LLM-first locator) requires a vision-capable model.
Text-only models silently fall back to the accessibility tree."*

**[major] `BDDFRAME_LLM_URL` is a footgun for cloud providers.**
`client.py` unconditionally passes `api_base=os.getenv("BDDFRAME_LLM_URL",
"http://localhost:11434")` to `litellm.completion`. That default Ollama base URL
will override Anthropic's and Gemini's real endpoints for any user who leaves
`BDDFRAME_LLM_URL` unset or set to Ollama. This already exists as a latent bug, but
Phase 4 expands the provider surface and will surface it. Fix: pass `api_base` only
when `BDDFRAME_LLM_URL` is explicitly set (i.e., `api_base=os.getenv("BDDFRAME_LLM_URL")
or None`). LiteLLM uses the provider's default URL when `api_base` is `None`.

**[minor] Phase 3 as a named phase creates dead weight.**
The plan correctly notes Phase 3 is absorbed by Phase 1. Remove Phase 3 from the
rollout table or relabel it as a note inside Phase 1. Keeping it as a named phase
will confuse the implementation PR.

**[minor] Model strings for Anthropic need the `anthropic/` prefix in LiteLLM.**
`claude-sonnet-4-6` without a provider prefix may or may not be inferred by
LiteLLM depending on version. The safe, explicit form is `anthropic/claude-sonnet-4-6`.
Verify against LiteLLM's provider docs before publishing `.env.example`.

**[minor] No test coverage planned for the new mode flag.**
The unit suite has `test_llm_openai_endpoint.py` and `test_phase_c.py`. Phase 1
adds a branching condition to `resolve()` — add at least two tests: one verifying
that `BDDFRAME_LLM_MODE=full` skips `pattern_match` (mock `_llm_resolve` and assert
it's called even when a pattern would have matched), and one verifying `auto` mode
is unchanged. These are mockable without a live model.

---

### Recommended changes before implementation

1. **`noodle/resolver/step_resolver.py` — expand `_llm_resolve` prompt.**
   For each REST type added to the prompt, include the expected parameter keys and
   types inline. Use the same terse format already used for web types:
   `rest_call -> method,path[,body,var]; rest_assert_status -> expected(int);
   rest_extract_json -> key,var; rest_assert_body -> needle;
   rest_assert_header -> name,value`. Exclude `rest_assert_body_table` and
   `rest_assert_header_table` from the prompt entirely.

2. **`noodle/llm/client.py` — fix `api_base` default.**
   Change `api_base=os.getenv("BDDFRAME_LLM_URL", "http://localhost:11434")` to
   `api_base=os.getenv("BDDFRAME_LLM_URL") or None` in both `ask()` and
   `ask_vision()`. This is a pre-existing bug that Phase 4 would actively expose.

3. **`noodle/agents/web/locator.py` — add warning log in `_vision_locate`.**
   Inside the `except Exception` block, add:
   `logger.warning(f"\n  ⚠️  vision-locate failed for '{text}': {e}")`.
   This surfaces degradation without changing behaviour.

4. **`docs/plan_llm_mode.md` — collapse Phase 3 into Phase 1, update Anthropic model
   string to `anthropic/claude-sonnet-4-6`.**

5. **`unit_tests/` — add two tests** for the mode flag before shipping Phase 1 (see
   Concerns above).

---

### Implementation order recommendation

The proposed order (1 → 2 → 4) is correct. One adjustment: **ship Phase 4 docs
alongside Phase 1**, not after. Merging a feature flag without the provider table
leaves users unable to configure a suitable model for `full` mode. Phase 2 can
follow in a separate commit once Phase 1 is verified working with at least one
cloud provider (recommend `anthropic/claude-sonnet-4-6` as the first smoke test —
it's vision-capable so it validates both step resolution and Phase 2 in one pass).

---

## Implementation notes (BFRAME_0031)

All four SA conditions were applied in the implementation:

| SA condition | Resolution |
|--------------|-----------|
| [critical] REST prompt needs param schemas; exclude `*_table` types | `_llm_resolve` prompt in `step_resolver.py` now lists every web + REST type with its param keys, names `path`/`expected` explicitly, and instructs the model to never emit a `*_table` type (those stay pattern-only). |
| [major] `api_base` Ollama footgun breaks cloud providers | `client.py` now has `_api_base()` returning `os.getenv("BDDFRAME_LLM_URL") or None`. Unset → LiteLLM resolves each provider's own endpoint. This is the change that lets **any** LiteLLM provider work, not just Ollama. |
| [major] Phase 2 silent degradation on text-only models | `_vision_locate` in `locator.py` now logs a `⚠️` warning when `ask_vision` raises (the typical cause: a text-only model rejecting an image), then falls back to accessibility. |
| [minor] Anthropic needs `anthropic/` prefix | All docs + `.env.example` use `anthropic/claude-sonnet-4-6`. |
| [minor] No test coverage for the flag | `unit_tests/test_llm_mode.py` — 6 tests covering auto vs full routing, REST routing in full mode, the no-model error, and `_api_base()` behaviour. |

### What "support ALL LLMs" means in practice

There is **no per-provider code**. LiteLLM is the single gateway and reads each
provider's API key from its conventional env var (`ANTHROPIC_API_KEY`,
`GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENAI_API_KEY`, …). To use a provider you set
two things and nothing else:

```bash
BDDFRAME_MODEL=<provider>/<model>     # e.g. anthropic/claude-sonnet-4-6
<PROVIDER>_API_KEY=...                 # the provider's key (cloud only)
```

`BDDFRAME_LLM_URL` is **only** for self-hosted/local endpoints (Ollama, Foundry
Local, an OpenAI-compatible proxy). Leaving it unset is now correct for every
cloud provider — the previous hardcoded localhost default was the one thing
blocking them.

### Files changed

- `noodle/llm/client.py` — `_api_base()` helper; both `ask`/`ask_vision` use it.
- `noodle/resolver/step_resolver.py` — `BDDFRAME_LLM_MODE` branch in `resolve()`; REST-aware prompt.
- `noodle/agents/web/locator.py` — `_is_full_llm()`; vision-first in full mode; warning log.
- `unit_tests/test_llm_mode.py` — new test file (6 tests).
- `.env.example`, `docs/guide.md`, `docs/architecture.md` — provider docs + mode toggle.

Full suite: **300 passed** (294 prior + 6 new in `test_llm_mode.py`).
