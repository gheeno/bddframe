# The LLM in BDDFrame

What model is used, what triggers it, the class that handles it, and where it
sits relative to the local engines (Playwright accessibility, OpenCV). For the
full step-resolution order see [resolution-hierarchy.md](resolution-hierarchy.md);
this page is LLM-specific.

> **Off by default.** No env var → no LLM. The framework runs fully local and a
> step it can't resolve fails with a screenshot. The LLM is opt-in, and even
> when on it is only a *fallback* — it never runs if a local layer already
> resolved the step.

---

## What kind of LLM

BDDFrame is **model-agnostic** — it talks to whatever [LiteLLM](https://github.com/BerriAI/litellm)
supports, through one provider/model string. You pick the model; the framework
does not hard-code a vendor.

| Setting | Env var | Default |
|---------|---------|---------|
| Model id (LiteLLM format) | `BDDFRAME_MODEL` | `ollama/llama3` for the text path; **unset** for vision |
| API base URL | `BDDFRAME_LLM_URL` | `http://localhost:11434` (local Ollama) |
| Desktop/visual model | `BDDFRAME_VISION_MODEL` | unset |

Examples of valid `BDDFRAME_MODEL` values: `ollama/llama3`, `ollama/llava`
(vision), `openai/gpt-4o`, `openai/gpt-4o-mini`. Features that send a screenshot
(vision-locate, semantic assertions) need a **vision-capable** model.

Install the dependency (LiteLLM is the only LLM dep):

```bash
pip install -e ".[llm]"     # adds litellm>=1.0.0
```

---

## The class / module that handles it

One thin module: **`bddframe/llm/client.py`**. Two functions, no class hierarchy —
it just normalises every call onto LiteLLM:

| Function | Purpose | Reads |
|----------|---------|-------|
| `ask(prompt) -> str` | text completion (step interpretation) | `BDDFRAME_MODEL`, `BDDFRAME_LLM_URL` |
| `ask_vision(prompt, image_b64) -> str` | text + screenshot (locate / assert) | `BDDFRAME_MODEL`, `BDDFRAME_LLM_URL` |

`litellm` is imported lazily inside `_litellm()`, so the framework imports and
runs with no LLM extra installed — you only hit the import error if you actually
trigger an LLM path without `pip install -e ".[llm]"`.

Everything else *calls* this module; nothing else talks to a model directly.

---

## The four triggers

Each is a local layer failing, plus the matching env var being set. If the env
var is unset, the step fails locally instead — the LLM is never called.

| # | Trigger (local layer missed) | Caller | Function | Gate |
|---|------------------------------|--------|----------|------|
| 1 | No regex pattern matched the step sentence | `resolver/step_resolver.py:_llm_resolve` | `ask` | `BDDFRAME_MODEL` |
| 2 | Web element not found by accessibility + POM | `agents/web/locator.py:_vision_locate` | `ask_vision` | `BDDFRAME_MODEL` |
| 3 | Semantic / visual-baseline assertion | `agents/web/actions.py:assert_semantic`, `visual_baseline` | `ask_vision` | `BDDFRAME_MODEL` |
| 4 | `@visual` image not found by OpenCV/OCR | `agents/visual/vision_locate.py:locate_by_description` | `ask_vision` | `BDDFRAME_VISION_MODEL` |

Note the split: triggers 1–3 (web path) gate on `BDDFRAME_MODEL`; trigger 4
(desktop `@visual` path) gates on `BDDFRAME_VISION_MODEL`.

---

## What the orchestration does

The orchestrators do **not** call the LLM themselves — they drive the local
flow and the LLM is reached only inside the layers they invoke.

- **`orchestrator/runner.py:execute_step`** (web): substitutes `[vars]` → calls
  `resolver.resolve()` (which may hit trigger 1) → dispatches to an `actions.*`
  function (assertions may hit trigger 3; element actions go through
  `locator.find`, which may hit trigger 2).
- **`orchestrator/visual_runner.py`** (`@visual`): matches a visual pattern →
  dispatches to the OpenCV/OCR agent, whose `_locate_image` falls back to
  trigger 4.

So orchestration = route + run local engines; the LLM is a leaf-level fallback
those engines reach, never the entry point.

---

## Where the LLM sits relative to OpenCV / Playwright

```mermaid
flowchart TD
    STEP["Gherkin step"] --> RES["Resolver: 40+ regex patterns<br/>LOCAL"]
    RES -->|matched| ROUTE{"Orchestrator<br/>route by tag"}
    RES -->|no match| T1["ask() — LLM step fallback<br/>trigger 1 · BDDFRAME_MODEL"]
    T1 --> ROUTE

    ROUTE -->|web| PW["Playwright accessibility tree<br/>role / label / text · LOCAL"]
    ROUTE -->|@visual| CV["OpenCV template match + OCR<br/>LOCAL"]

    PW -->|found| ACT["run web action"]
    PW -->|not found| POM["POM YAML<br/>LOCAL"]
    POM -->|found| ACT
    POM -->|not found| T2["ask_vision() — vision locate<br/>trigger 2 · BDDFRAME_MODEL"]
    T2 --> ACT

    CV -->|found| VACT["run visual action"]
    CV -->|not found| T4["ask_vision() — locate by description<br/>trigger 4 · BDDFRAME_VISION_MODEL"]
    T4 --> VACT

    ACT --> ASSERT{"assertion?"}
    ASSERT -->|structural: text/url/title| LOCALA["DOM check · LOCAL"]
    ASSERT -->|semantic / baseline| T3["ask_vision() — semantic assert<br/>trigger 3 · BDDFRAME_MODEL"]

    T1 -.calls.-> CLIENT["bddframe/llm/client.py<br/>ask · ask_vision → LiteLLM"]
    T2 -.calls.-> CLIENT
    T3 -.calls.-> CLIENT
    T4 -.calls.-> CLIENT

    style RES fill:#1e3a5f,color:#b8d8f5,stroke:#4a80aa
    style PW fill:#1e3a5f,color:#b8d8f5,stroke:#4a80aa
    style CV fill:#1e3a5f,color:#b8d8f5,stroke:#4a80aa
    style POM fill:#1e3a5f,color:#b8d8f5,stroke:#4a80aa
    style LOCALA fill:#1e3a5f,color:#b8d8f5,stroke:#4a80aa
    style T1 fill:#4a3a2a,color:#f5d8b8,stroke:#aa804a,stroke-dasharray:4 4
    style T2 fill:#4a3a2a,color:#f5d8b8,stroke:#aa804a,stroke-dasharray:4 4
    style T3 fill:#4a3a2a,color:#f5d8b8,stroke:#aa804a,stroke-dasharray:4 4
    style T4 fill:#4a3a2a,color:#f5d8b8,stroke:#aa804a,stroke-dasharray:4 4
    style CLIENT fill:#3a2a4a,color:#e8d8f5,stroke:#8a6aaa
```

Blue = local (never costs an LLM call). Orange dashed = the four LLM fallbacks,
all funnelling into `client.py`. The LLM is always *downstream* of OpenCV and
Playwright — it only runs when the local engine on that branch came up empty and
the env var is set.

---

## Configuration recap

```bash
# Local, free (Ollama) — text fallback only
BDDFRAME_MODEL=ollama/llama3
BDDFRAME_LLM_URL=http://localhost:11434

# Vision features (web locate + semantic assertions) need a vision model
BDDFRAME_MODEL=ollama/llava          # or openai/gpt-4o

# Desktop @visual image fallback
BDDFRAME_VISION_MODEL=ollama/llava
```

Leave them all unset for a deterministic, zero-cost, fully-local run — the
recommended CI baseline.
