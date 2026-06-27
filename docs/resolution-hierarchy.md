# Resolution Hierarchy — Who Handles Each Step

This is the single source of truth for **when the local agent runs the test and
when an LLM takes over**. The headline rule:

> **The LLM is off by default.** With no `BDDFRAME_MODEL` set, BDDFrame is 100%
> local — pattern matching, Playwright accessibility, POM YAML, OpenCV. Anything
> the local layers can't resolve simply **fails** (with a screenshot), it does
> not silently call out to a model. LLM layers only exist once you opt in.

---

## The four levels

A step passes through up to four decision levels. At each one, the **local**
path is tried first; the **LLM** path is a labelled fallback that only fires
under the stated condition.

```mermaid
flowchart TD
    S["Gherkin step"] --> L0

    subgraph L0["① Interpret the sentence — resolver"]
        P["Pattern match (40+ regex)\nLOCAL · no cost"] -->|matched| OUT0["action"]
        P -->|no match| LLM0["LLM step fallback\nonly if BDDFRAME_MODEL set\nelse: step FAILS"]
        LLM0 --> OUT0
    end

    OUT0 --> L1{"② Route by tag"}
    L1 -->|@visual| VIS
    L1 -->|web default| WEB

    subgraph WEB["③ Web — find the element (locator.find)"]
        A["Accessibility tree\nrole / label / placeholder / text\nLOCAL"] -->|exactly 1| HIT["use it"]
        A -->|2+ matches| AMB["POM scoped entry?\nLOCAL → yes: use it"]
        AMB -->|no entry| MODE["strict: FAIL · lenient: first + warn"]
        A -->|0| HEAL["scroll, then partial-word retry\nLOCAL"]
        HEAL -->|found| HIT
        HEAL -->|still 0| POM["POM YAML\npage-scoped → shared → flat\nLOCAL"]
        POM -->|found| HIT
        POM -->|not found| VL["Vision LLM locate\nonly if BDDFRAME_MODEL set\nelse: step FAILS"]
        VL --> HIT
    end

    subgraph VIS["③ Visual — find on screen"]
        T["OpenCV template match + OCR\nLOCAL"] -->|found| HIT2["use coords"]
        T -->|not found| VL2["Vision LLM locate\nonly if BDDFRAME_VISION_MODEL set\nelse: step FAILS"]
        VL2 --> HIT2
    end

    HIT --> L3
    HIT2 --> L3

    subgraph L3["④ Assertions"]
        ST["Structural: text / url / title\nLOCAL"]
        SE["Semantic / visual-baseline\nALWAYS vision LLM — requires BDDFRAME_MODEL"]
    end

    style P fill:#1e3a5f,color:#b8d8f5,stroke:#4a80aa
    style A fill:#1e3a5f,color:#b8d8f5,stroke:#4a80aa
    style POM fill:#1e3a5f,color:#b8d8f5,stroke:#4a80aa
    style T fill:#1e3a5f,color:#b8d8f5,stroke:#4a80aa
    style ST fill:#1e3a5f,color:#b8d8f5,stroke:#4a80aa
    style LLM0 fill:#4a3a2a,color:#f5d8b8,stroke:#aa804a,stroke-dasharray:4 4
    style VL fill:#4a3a2a,color:#f5d8b8,stroke:#aa804a,stroke-dasharray:4 4
    style VL2 fill:#4a3a2a,color:#f5d8b8,stroke:#aa804a,stroke-dasharray:4 4
    style SE fill:#4a3a2a,color:#f5d8b8,stroke:#aa804a,stroke-dasharray:4 4
```

---

## Level ① — Interpret the sentence (resolver)

| Path | When | Cost |
|------|------|------|
| **Pattern match** (local) | Step matches one of the 40+ built-in regex patterns | none |
| **LLM step fallback** | No pattern matched **and** `BDDFRAME_MODEL` is set | 1 LLM call |
| **Fail** | No pattern matched and no model set | — |

Code: `bddframe/resolver/step_resolver.py`. The LLM is asked to return a JSON
action only when the regexes all miss.

## Level ② — Route by tag

`@visual` → desktop/OpenCV agent. Everything else → web/Playwright agent.
Routing is local and free (`bddframe/steps/catch_all.py`).

## Level ③ (web) — Find the element

Order in `bddframe/agents/web/locator.py`:

1. **Accessibility tree** (local) — role, label, placeholder, title, text.
   A *unique* match is used immediately.
2. **Ambiguous** (2+ matches): consult **POM** for a scoped selector (local).
   No POM entry → **strict** mode fails with the candidate list; **lenient**
   (default) warns and uses the first match.
3. **Self-heal** (local) — scroll and retry, then first-word partial match.
4. **POM YAML** (local) — page-scoped block → `shared:` → flat keys.
5. **Vision LLM locate** — screenshot → "give me a CSS selector". **Only if
   `BDDFRAME_MODEL` is set**; otherwise the element is unresolved and the step
   fails with a screenshot.

## Level ③ (visual) — Find on screen

`bddframe/orchestrator/visual_runner.py`:

1. **OpenCV template match + Tesseract OCR** (local).
2. **Vision LLM locate by description** — **only if `BDDFRAME_VISION_MODEL`
   is set**.

## Level ④ — Assertions

| Path | When |
|------|------|
| **Structural** (local) | `should see`, `should not see`, `url containing`, `page title` — direct DOM/text checks, never an LLM |
| **Semantic / visual-baseline** | `the X should show…`, `the screen should look the same as before` — **always** a vision LLM call; requires `BDDFRAME_MODEL`, raises a clear error if unset |

---

## Cases — "what runs for this step?"

| Step | Resolves via |
|------|--------------|
| `User clicks the login button` (button reads "Login") | Local — accessibility |
| `User clicks the burger menu` (icon-only) | Local — POM YAML |
| `User clicks "Add to cart"` (six on page) | Local — POM if scoped; else first-match (lenient) or FAIL (strict) |
| `User should see "Products"` | Local — DOM text |
| `User enters X in the obscure_widget` (no label, no POM, model set) | LLM — vision locate |
| `User frobnicates the gizmo` (matches no pattern, model set) | LLM — step fallback |
| `the dashboard should show a healthy state` | LLM — semantic assertion (required) |
| `I click image "save.png"` (`@visual`) | Local — OpenCV template match |
| `I click image "save.png"` not found, vision model set | LLM — vision locate by description |

---

## Env vars that switch LLM layers on

| Var | Turns on |
|-----|----------|
| `BDDFRAME_MODEL` | LLM step fallback · web vision-locate · semantic & baseline assertions |
| `BDDFRAME_VISION_MODEL` | Desktop/visual agent's image vision-locate fallback |

Unset both → fully local, deterministic, zero model cost. This is the default
and the recommended baseline for CI: a step that can't be resolved locally
should fail loudly, not quietly invoke a model.

---

## Forcing failures instead of guesses (strict mode)

By default, ambiguity is lenient (warn + first match) so suites stay green.
For CI you usually want ambiguity to **fail** so wrong-element bugs surface:

```bash
BDDFRAME_STRICT_LOCATOR=true      # whole run
```

```gherkin
@strict
Scenario: ...                      # this scenario only
```

See [phase-09-element-disambiguation.md](phase-09-element-disambiguation.md) for
the design and [pom-key-mapping.md](pom-key-mapping.md) for how to write the
scoped POM entry that resolves an ambiguous step.
