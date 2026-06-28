# BDDFrame — Enterprise-Grade Plan

Status: proposed (not yet implemented). Owner: @gheeno. Date: 2026-06-27.

Target: production-grade test framework runnable in **Azure DevOps**, that beats
Selenium / Selenide **including** their self-healing add-ons (Healenium / Autoheal).

---

## Verdict

> **Update 2026-06-27: Phases A–D implemented.** The operational gaps below are
> closed — parallelism (CI sharding), retry/quarantine, failure traces,
> deterministic visual diff, structured logging, Key Vault secrets, healing
> telemetry, Docker, and API/mock/test-data steps all landed. Suite: 212 tests
> green. The sections below are kept as the original assessment.

Architecturally ahead of Selenium/Selenide; operationally not yet enterprise-grade.

The core bet — accessibility-first locators, no hand-written selectors — is
genuinely stronger than Selenium+Healenium, because the brittle CSS/XPath that
Healenium exists to repair mostly doesn't exist here. But the run / scale / debug
/ secrets layers that "enterprise + Azure DevOps" demands have gaps, and two are
currently **broken**, not just missing.

---

## What's already solid (don't touch)

- **Locator strategy** (`bddframe/agents/web/locator.py`): role/label/placeholder/
  text, unique-match enforcement, strict mode, POM escape hatch, iframe + row/
  section scoping (D365-grade). This is the moat.
- **LLM is opt-in fallback only** — deterministic, zero-cost by default. Correct
  posture for CI gating.
- **Reporting**: Allure + JUnit wired into behave lifecycle, annotated failure
  screenshots, Azure Tests-tab integration.
- **Hygiene**: secrets gitignored, recorder redacts sensitives, 172 headless unit
  tests, LSP + VS Code extension, cross-browser.

---

## Gaps (ranked, Azure-weighted)

### Broken today — fix before claiming "enterprise"

1. **Parallelism is fake.** `cli.py:38` accepts `--workers` and silently ignores
   it — never passed to behave; behave has no native parallelism (no behavex/
   xdist in deps). Enterprise suites run fully serial. Also the #1 thing
   Selenium-Grid+TestNG users expect. → remove the lie or make it real.
2. **The Azure pipeline can't run.** `azure-pipelines.yml` does
   `pip install bddframe` — pulls from PyPI where `bddframe 0.1.0` isn't
   published. CI fails at install. → `pip install -e ".[all]"` or publish to an
   Azure Artifacts feed.

### Missing for enterprise

3. **No retry / flaky quarantine.** No rerun-failed, no quarantine tag. TestNG
   `retryAnalyzer` is table stakes.
4. **No Playwright trace/video on failure.** Ships only a screenshot. The trace
   viewer (DOM snapshots, network, timeline, time-travel) is the single biggest
   debugging edge over Selenium/Selenide and it's currently off. Video is opt-in
   via `@record_video` only.
5. **Visual baseline is LLM-described prose** (`actions.py:111`) — non-
   deterministic, unusable as a CI gate. No deterministic pixel/DOM diff.
6. **Secrets stop at `.env` / variable groups.** Code says "soon AKV". No Azure
   Key Vault / managed-identity path.
7. **No structured logging.** Emoji `print()` everywhere; no log levels, no
   machine-readable run log.
8. **No Docker / devcontainer.** CI relies on ad-hoc Xvfb; no reproducible image.
9. **No API/test-data setup-teardown or network mocking.** Tests can't seed or
   clean state.

---

## Beating Selenium / Selenide + Autoheal

Don't beat Healenium by building a better healer — beat it by **not needing one**,
which we mostly already do. Lean into that and close the debug/scale gap.

- **Already winning:** no brittle selectors to heal; Playwright auto-waits (beats
  Selenide smart waits); plain-English tests (no glue/POM).
- **Shallow spot:** current "self-heal" is scroll + first-word partial. Healenium's
  real edge is *telemetry* — it records what broke, what it healed to, and surfaces
  it. We heal via vision-LLM but **log/persist nothing**. Add healing telemetry +
  POM-writeback suggestion → match its one real feature while keeping the
  structural advantage.

---

## Plan (phased, lazy-first)

### Phase A — Stop the bleeding (days) — DONE 2026-06-27

- [x] Fixed both pipelines' install step → `pip install -e ".[all]"`.
- [x] Deleted the fake `--workers` flag (`cli.py`). Parallelism now comes from an
      Azure **matrix that shards by feature folder** — one agent per shard, each
      publishes its own junit.xml, Azure aggregates. No in-process pool, no dep.
      *Skipped: in-process worker pool; add only if single-agent throughput
      matters more than agent count.*
- [x] Playwright tracing in `hooks.py`: started per scenario, saved to
      `traces/<name>.zip` only on failure (discarded on pass), published as a
      pipeline artifact on `failed()`. View with `playwright show-trace`.
      *Skipped: per-scenario video (overhead on green runs) — trace snapshots
      cover it; keep the opt-in `@record_video` tag. Skipped Allure attachment —
      the existing attachment path doesn't copy files into allure-results/ (pre-
      existing latent bug, see Phase B logging/reporting cleanup).*

### Phase B — CI maturity — DONE 2026-06-27

- [x] Retry via behave's `scenario_autoretry` (`hooks.before_feature`), gated by
      `BDDFRAME_RETRIES` (default 1; `--retries` flag). Retries fire only on
      failure → green scenarios cost nothing. `@no_retry` opts out.
      `@quarantine` = non-blocking: `cli.run` scans this run's Allure results and
      exits 0 if every failure is quarantined (`_all_failures_quarantined`).
      `before_all` now clears stale `allure-results` so the scan + report reflect
      only this run.
- [x] Deterministic pixel diff with Pillow (no new dep): `pixel_baseline` action
      + step "the [\"name\"] screen should match the baseline", threshold
      `BDDFRAME_PIXEL_THRESHOLD` (default 1%), diff image saved on mismatch. LLM
      baseline kept as the opt-in semantic tier.
      *Skipped: Playwright `to_have_screenshot` — its pytest-oriented baseline/
      first-run semantics fought the BDD flow; Pillow gave full control in ~25
      lines.*
- [x] `bddframe/log.py` logger, `BDDFRAME_LOG_LEVEL` + `--log-level`; runtime
      breadcrumbs migrated off `print()` (live-stdout handler keeps capsys/behave
      output intact). *Skipped: migrating CLI command UX prints — those are user
      output, not runtime telemetry.*

### Phase C — Enterprise integration — DONE 2026-06-27

- [x] `bddframe/secrets_akv.py` — Key Vault loader gated by
      `BDDFRAME_KEYVAULT_URL`, `DefaultAzureCredential` (managed identity in CI,
      `az login` locally), dash→underscore name mapping. `[azure]` extra. Wired
      into `hooks.before_all`; `$(VAR)`-literal guarded. Unset → `.env` fallback.
- [x] `bddframe/healing.py` — every self-heal (scroll/partial), POM
      disambiguation and vision-locate is recorded; `after_all` writes
      `healing.jsonl` + a report with one `pom.yaml` suggestion per healed
      locator. The Healenium-killer: we report what broke *and* the deterministic
      fix.
- [x] `Dockerfile` (Playwright base image, browsers preinstalled) +
      `.devcontainer/` + `.dockerignore` for reproducible CI/local parity.

### Phase D — Nice-to-have — DONE 2026-06-27

- [x] Network mocking — `mock_route` ("mocks \"glob\" with status N and body ...")
      + `block_route` ("blocks requests to \"glob\""), via Playwright `route`.
- [x] API setup/teardown — `api_call` ("calls POST \"url\" with body ...") via
      Playwright's request context (shares browser cookies, no new dep).
- [x] Test-data fixtures — `load_data` ("loads test data from \"file.yaml\"")
      merges a YAML/JSON mapping into the run-scoped variable store.

---

## Recommended starting point

Phase A. It's the overlap of "broken" and "biggest differentiator", and it's
small diffs: pipeline fix + tracing + feature-sharding.
