# Peer Review — BDDFrame (2026-06-28)

Reviewer: external/independent. Branch: BFRAME_0018. Status: **all 7 items implemented on this branch** (see the summary table; 0018-3 uses Pillow `histogram()` rather than the numpy swap originally sketched — lazier, no new dep).

This is a cold read of the full codebase after Phases A–D landed. Items are
ranked by severity × enterprise impact. Nothing here touches the locator
strategy (the moat) or the CI pipeline (correct as-is).

---

## What's solid — don't touch

- **Locator strategy** (`locator.py`): 9 accessibility strategies, strict/lenient,
  row/section/iframe scoping, POM escape hatch. This is the structural advantage
  over Selenium. Don't add CSS/XPath shortcuts here.
- **Healing telemetry** (`healing.py`): heals AND surfaces the fix. Better than
  Healenium's silent repair.
- **Tracing on failure**: DOM snapshots + network + timeline, save-on-fail,
  Azure Artifacts. The single biggest debug edge over Selenium.
- **Retry + quarantine + gated exit**: CI-mature, no further changes needed.
- **Preconditions, network mocking, API calls, script runner, test data**: complete.
- **212 unit tests** covering the hard paths: keep this discipline on new code.

---

## Gaps — ranked

### P0 — Correctness risk in CI

**BFRAME_0018-1: LLM step resolver has no output validation**

File: `bddframe/resolver/step_resolver.py:28` (`_llm_resolve`)

Current behaviour: one `ask()` call → `json.loads` → dispatch. If the model
returns a syntactically valid JSON with the wrong `type` (e.g. `"click"` when
the step meant `"assert_visible"`), the test silently executes the wrong action
and may pass. No retry, no schema validation, no confidence check.

Fix:
```python
VALID_TYPES = frozenset({
    "navigate", "click", "fill", "hover", "press_key", "clear", "select",
    "check", "uncheck", "assert_visible", "assert_hidden", "assert_url",
    "assert_value", "assert_state", "assert_attribute", "assert_count",
    "store_text", "scroll", "screenshot", "wait_load", "wait_visible",
    "wait_hidden", "set_var", "store_attribute", "assert_compare",
})

action = json.loads(raw.strip())
if action.get("type") not in VALID_TYPES:
    raise AssertionError(
        f"LLM returned unknown action type '{action.get('type')}' for: \"{step_text}\"\n"
        f"Response: {raw}"
    )
```

Also add one retry on `JSONDecodeError` before raising — models occasionally
return a leading explanation sentence before the JSON.

---

**BFRAME_0018-2: `_vision_locate` CSS selector prompt is too loose**

File: `bddframe/agents/web/locator.py:108` (`_vision_locate`)

Current: asks the LLM for a CSS selector. LLMs hallucinate selectors. The
`strip('`')` only strips single backtick delimiters — a markdown-fenced response
(```` ```css\n.foo\n``` ````) passes through broken and will throw in
`page.locator(css)`.

Fix 1 — Tighten the strip:
```python
import re as _re
css = _re.sub(r'^```[a-z]*\n?|```$', '', ask_vision(...).strip()).strip()
```

Fix 2 — Structured prompt with a null path:
```
Return a JSON object: {"selector": "<css>"} if you can identify the element,
or {"selector": null} if you cannot. No other text.
```
Then `json.loads` the response and return `None` when `selector` is null.
This eliminates the silent wrong-element risk.

---

### P1 — Performance (bites at CI scale)

**BFRAME_0018-3: `pixel_baseline` is a pure-Python pixel loop**

File: `bddframe/agents/web/actions.py:_pixel_diff_ratio`

Full-page 1920×1080 = 2M pixel comparisons in a Python `sum()` loop. In a
sharded matrix with several scenarios each running a pixel baseline, this is
the slowest step in the run. `numpy` is installed transitively (Playwright +
Pillow pull it in on most platforms).

Drop-in swap (~3 lines, same function signature):
```python
import numpy as np

def _pixel_diff_ratio(base, current, tol: int = 30):
    base = base.convert("RGB")
    current = current.convert("RGB")
    if base.size != current.size:
        return None
    diff = np.abs(np.array(base, dtype=np.int16) - np.array(current, dtype=np.int16))
    changed = int(np.any(diff > tol, axis=2).sum())
    total = base.size[0] * base.size[1]
    return changed / total if total else 0.0
```

The existing `ponytail:` comment already calls this out — this is the upgrade.

---

### P1 — Reliability

**BFRAME_0018-4: `wait_for` uses a manual 250ms polling loop**

File: `bddframe/agents/web/locator.py:wait_for` (~line 60)

Current: Python `while time.monotonic() < deadline` + `page.wait_for_timeout(250)`.
This has a race window: element appears between polls, deadline check passes,
Python context switches, next `is_visible()` call races with the element
disappearing (animation end). Low probability but real.

Playwright's `.wait_for(state="visible", timeout=ms)` uses MutationObserver
internally — no race window, no polling interval to tune.

For the non-POM text path, swap to:
```python
page.get_by_text(text, exact=False).first.wait_for(state="visible", timeout=timeout_ms)
```

Keep the POM path as-is (it already uses `.wait_for`). The 30-match cap in
`wait_for` is fine — `get_by_text(...).first` picks the first DOM match, which
is what we want while waiting (the real element and its sr-only twin become
visible together).

---

### P2 — Enterprise readiness

**BFRAME_0018-5: No test data isolation between parallel shards**

When two matrix shards POST to the same test backend simultaneously
(e.g. `POST /api/test/reset` in preconditions), they race. One shard's setup
tears down the other's state mid-scenario.

Short-term: document this constraint — shards that share a backend must not
overlap in precondition usage. Add a note to `docs/architecture.md`.

Long-term: add a `namespace` key to `preconditions.yaml` so each shard seeds
into a tenant/dataset slot (`movieId=shard_index`) rather than a shared reset.
Requires the test app to support namespaced fixtures.

---

**BFRAME_0018-6: `assert_count` counts text occurrences, not element instances**

File: `bddframe/agents/web/actions.py:assert_count`

`page.get_by_text(locator_text).count()` counts every DOM node whose text
contains the string — including aria-label duplicates, sr-only copies, and
tooltip text. "Should see 3 'Add to Cart'" may return 6.

More accurate approach for element counts: resolve via `_try_strategies` and
count the resulting locator, or default to `get_by_role` with a `name` filter.
This only matters when tests use numeric assertions on text that appears in
multiple DOM roles.

---

## The next frontier — Agentic RCA

**BFRAME_0018-7: Agentic failure reviewer (not yet built)**

This was named in the project goals but does not exist. Current state:
- `healing.py` writes static telemetry (not agentic)
- `assert_semantic` checks a claim (not a reviewer)
- `_vision_locate` finds an element (not a diagnostician)

What "agentic RCA" means in practice: after a step failure, send the failure
screenshot + step name + error message + healing log to a vision LLM that
classifies the root cause and suggests a resolution.

The bones are all there. Sketch:

```python
# in hooks.after_step, on failure:
if os.getenv("BDDFRAME_MODEL") and os.getenv("BDDFRAME_RCA"):
    _run_rca(context, step, raw_path)

def _run_rca(context, step, screenshot_path):
    from bddframe.llm.client import ask_vision
    import base64, json as _json

    b64 = base64.b64encode(Path(screenshot_path).read_bytes()).decode()
    prompt = f"""A BDD test step failed. Classify the root cause and suggest a fix.

Step: "{step.name}"
Error: "{step.error_message}"

Root cause categories:
  A) App regression — the UI changed or a feature is broken
  B) Locator rot — the element label or structure changed
  C) Environment flap — network, timeout, or infra issue
  D) Test data issue — missing or wrong seed data
  E) Test script issue — the step or assertion is wrong

Reply with JSON only:
{{"category": "A|B|C|D|E", "confidence": "high|medium|low", "reason": "one sentence", "suggested_fix": "one sentence"}}
"""
    try:
        raw = ask_vision(prompt=prompt, image_b64=b64)
        rca = _json.loads(raw.strip())
        logger.info(f"\n  🔍 RCA: [{rca['category']}] {rca['reason']} (confidence: {rca['confidence']})")
        logger.info(f"\n  💡 Suggested fix: {rca['suggested_fix']}")
        # Attach to Allure result as a label for filtering
        ar = _allure_result(context)
        if ar is not None:
            ar._result.labels.append({"name": "rca_category", "value": rca["category"]})
    except Exception:
        pass  # RCA is best-effort, never blocks the run
```

Gate it behind `BDDFRAME_RCA=true` — opt-in because it costs one LLM call per
failure. The Allure label attachment means you can filter by RCA category in the
report (`rca_category:B` → all locator rot failures in this run).

This is the feature that separates "self-healing framework" from "agentic test
framework". It's also the honest answer when asked "does this beat
Selenium+Healenium on RCA" — right now the answer is no; with this it's yes.

---

## Summary table

| ID | File | Severity | Effort |
|----|------|----------|--------|
| BFRAME_0018-1 | `resolver/step_resolver.py` | P0 correctness | 30 min |
| BFRAME_0018-2 | `agents/web/locator.py` | P0 correctness | 30 min |
| BFRAME_0018-3 | `agents/web/actions.py` | P1 perf | 15 min |
| BFRAME_0018-4 | `agents/web/locator.py` | P1 reliability | 20 min |
| BFRAME_0018-5 | `docs/architecture.md` | P2 doc + future | 1 hr (long-term) |
| BFRAME_0018-6 | `agents/web/actions.py` | P2 correctness | 30 min |
| BFRAME_0018-7 | `hooks.py` + new | P1 feature gap | 2–3 hr |

Items 1–4 are small, safe diffs with no architecture changes. Item 7 (RCA) is
the headline feature and the honest next chapter.
