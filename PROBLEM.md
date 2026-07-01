# Noodle Test Framework — AI Solution Brief

---

## 1. Summary of the AI Solution

Noodle Test Framework is an AI-augmented BDD test automation framework. QA engineers write one artifact — a plain-English `.feature` file — and the framework handles the rest: step resolution, element location, browser control, and reporting.

```gherkin
Scenario: Valid user can log in
  Given User is on "[SAUCEDEMO]"
  When User enters [SAUCE_USERNAME] in the username field
  And User clicks the login button
  Then User should see "Products"
```

No selector code. No step glue. No page object class. The AI layer is opt-in: by default the framework is fully deterministic and free-to-run. The LLM enters only when local resolution fails — or when you explicitly need it for natural-language test generation and semantic assertions.

---

## 2. The Problem

Traditional test automation (Selenium, Selenide, Appium) forces QA engineers to write **three separate layers** for every test:

| Layer | What you write | Breaks when |
|-------|---------------|-------------|
| Gherkin sentence | `When User clicks the login button` | Requirement changes |
| Step definition (glue code) | `@When("user clicks the login button") public void ...` | Step text changes |
| Page Object / locator | `By.id("login-button")` | UI refactor, CSS rename |

This creates three compounding problems:

**1. High creation cost.** A single feature scenario can require 4–8 hours of glue and selector work before a single test runs. Non-coder QAs are locked out entirely.

**2. Brittle maintenance.** UI changes break locators. Healenium and similar tools exist to patch this problem, but they patch the symptom — the real issue is hand-written selectors.

**3. Sprint spillover.** Selector maintenance consumes 30–40% of QA automation capacity per sprint. Stories that need new tests don't get them because the team is fixing existing ones.

---

## 3. How We Built the Solution

Noodle Test Framework replaces the glue-and-locator stack with a local resolution pipeline and an optional LLM fallback.

```
Feature file
    │
    ▼
Step Resolver — 50+ regex patterns (free, deterministic)
    │
    ├─ match found ────────────────► Web Agent (Playwright)
    │                                  └─ accessibility-first locator
    │                                      (role / label / text)
    │                                  └─ POM YAML escape hatch
    │                                  └─ LLM vision-locate (opt-in)
    │
    └─ no match
          ├─ LLM off (default) ──────► FAIL loudly with screenshot
          └─ LLM auto (opt-in) ──────► LLM interprets step → Web Agent
```

**Resolution hierarchy (local first, LLM last):**

1. Regex pattern match — 50+ built-in patterns cover navigation, click, fill, assert, API calls, network mocks, waits.
2. Accessibility tree — elements found by role, label, placeholder, text. No `By.id` needed.
3. `pom.yaml` — optional named selectors for unlabelled elements (icon-only buttons, legacy widgets).
4. LLM fallback — only reached when all local layers fail, and only when `BDDFRAME_MODEL` is configured.

**Key technology decisions:**

- **Behave** — BDD runner; Gherkin parser drives the step lifecycle.
- **Playwright** — browser automation with built-in auto-waits and accessibility APIs.
- **LiteLLM** — single interface to any model (Claude, Gemini, OpenAI, Ollama, Foundry Local). Zero code change to swap providers.
- **Allure + JUnit XML** — reports readable by humans and Azure DevOps Tests tab.
- **Healing telemetry** — every self-heal is logged to `healing.jsonl` with a suggested `pom.yaml` fix. QA never hunts for what broke.

**AI is a separate installable layer:**

```bash
pip install noodle          # deterministic, zero cost
pip install noodle[llm]     # adds LiteLLM; LLM still off until BDDFRAME_MODEL is set
```

---

## 4. What Actions Will AI Take?

The LLM has four precisely-scoped triggers. It never runs speculatively.

| # | Trigger | LLM call | Gate |
|---|---------|----------|------|
| 1 | No regex pattern matched the step sentence | `ask(step_text)` → returns structured action JSON | `BDDFRAME_MODEL` set |
| 2 | Web element not found by accessibility tree + POM | `ask_vision(prompt, screenshot)` → returns CSS selector | `BDDFRAME_MODEL` set |
| 3 | Semantic or visual-baseline assertion | `ask_vision(prompt, screenshot)` → pass/fail verdict | `BDDFRAME_MODEL` set |
| 4 | `@visual` desktop image not found by OpenCV/OCR | `ask_vision(prompt, screenshot)` → coordinates | `BDDFRAME_VISION_MODEL` set |

**Beyond test execution, the AI will also:**

- **Generate test scaffolds** (Phase 3 of the agent roadmap): `create test for login at https://...` → writes a `.feature` file and `pom.yaml` skeleton, template-based (free) or LLM-assisted (opt-in Ollama or paid API).
- **Classify failure root causes** (RCA): on step failure with `BDDFRAME_RCA` set, a vision model classifies the failure category and tags the Allure result — no manual triage needed.
- **Summarise run results** in plain English (Phase 4): reads `allure-results/*.json` → emits a human-readable pass/fail summary without opening a browser.

The LLM never executes steps for which local resolution already works. Green CI runs cost zero model calls.

---

## 5. Potential Impact

### Qualitative

- **QA writes tests, not code.** `.feature` files are plain English. Domain experts, BAs, and product owners can read and review tests without a developer.
- **Locators don't break on CSS renames.** Accessibility-first location (`role=button, name="Login"`) survives UI refactors that break `By.id("login-btn")`.
- **Self-healing is logged, not silent.** When the framework adapts to a changed UI, it records the change and suggests the permanent fix — unlike Healenium which patches without explanation.
- **AI extends coverage without AI dependency.** Steps the pattern resolver can't handle become LLM calls, not test gaps. New product vocabulary doesn't require new framework code.

### Quantitative — Calculator View

The numbers below are estimates based on typical automation team ratios. Replace the inputs with your team's actuals to size the saving.

---

#### 1. Test Case Creation Effort

| Approach | Time per scenario |
|----------|-------------------|
| Traditional (Selenium + POM) | 4–8 hrs (feature + glue + selectors) |
| Noodle Test Framework (pattern-based) | 1–2 hrs (feature file only) |
| Noodle Test Framework + AI generation | 0.5–1 hr (generated scaffold + review) |

**Saving per scenario: ~3–7 hours**

At 20 new scenarios per sprint, a 5-engineer QA team recaptures **60–140 engineer-hours per sprint** — enough to automate coverage that would otherwise never be written.

```
Metric,Selenium + POM (hrs),Noodle Test Framework (hrs),Delta
Creation time per scenario,6,1.5,-75%
```

---

#### 2. Maintenance Effort per Broken Test

| Scenario | Traditional (hrs) | Noodle Test Framework (hrs) |
|----------|------------------:|---------------:|
| CSS selector changed | 1–3 | 0 (accessibility locator unaffected) |
| Element label renamed | 1–2 | 0.25 (update feature sentence) |
| New unlabelled element | 2–4 | 0.5 (add one `pom.yaml` entry, suggested by healing log) |
| Step verb not in patterns | 2–4 (add step def) | 0 (LLM fallback handles it) |

**Average maintenance per broken test: ~4 hrs (traditional) → ~0.5 hrs (Noodle Test Framework)**

```
Metric,Selenium + POM (hrs),Noodle Test Framework (hrs),Delta
Maintenance effort per broken test,4,0.5,-87%
```

---

#### 3. Percentage of Tests That Fail a Given Cycle

| Cause of failure | Traditional risk | Noodle Test Framework risk |
|-----------------|-----------------|---------------|
| CSS/XPath selector drift | High (every deploy) | Near zero (no hand-written selectors) |
| Step definition mismatch | Medium (sentence edit) | Low (pattern covers variants) |
| Environment / data issues | Same | Same |
| True regression | Same | Same |

**Industry baseline:** 10–20% of a traditional Selenium suite breaks per release due to locator drift.  
**Noodle Test Framework target:** <5% failure rate attributable to framework brittleness (locator heals or logs a fix; only genuine regressions fail).

_At 200 tests, that's the difference between triaging 20–40 false failures per release vs. 0–10._

```
Metric,Selenium + POM (%),Noodle Test Framework (%),Delta
% of tests failing per cycle (locator drift),15,3,-80%
```

---

#### 4. Percentage of Automation Work Not Completed in Sprint

| Work type | Traditional capacity consumed | Noodle Test Framework capacity consumed |
|-----------|------------------------------|---------------------------|
| Selector maintenance | 30–40% | <5% |
| Step definition glue | 10–20% | 0% |
| New test authoring | 40–60% | 95–100% |

**Net effect:** Maintenance drops from ~50% of sprint capacity to ~5%, freeing the team to write new coverage instead of fixing old tests.

```
Metric,Selenium + POM (%),Noodle Test Framework (%),Delta
% sprint capacity lost to maintenance,45,5,-89%
```

---

#### Summary Calculator

| Metric | Selenium + POM | Noodle Test Framework | Delta |
|--------|---------------|----------|-------|
| Creation time per scenario | 6 hrs avg | 1.5 hrs avg | **−75%** |
| Maintenance hrs per broken test | 4 hrs | 0.5 hrs | **−87%** |
| % of tests failing from locator drift | 15% | 3% | **−80%** |
| % sprint capacity lost to maintenance | 45% | 5% | **−89%** |

```
Metric,Selenium + POM,Noodle Test Framework,Delta
Creation time per scenario (hrs),6,1.5,-75%
Maintenance effort per broken test (hrs),4,0.5,-87%
% of tests failing per cycle,15%,3%,-80%
% sprint capacity lost to maintenance,45%,5%,-89%
```

Replace the averages with your team's tracked actuals — the ratios hold directionally regardless of team size.
