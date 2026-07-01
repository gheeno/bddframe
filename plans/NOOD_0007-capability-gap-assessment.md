# NOOD_0007 — Capability & Gap Assessment vs. the Codeless-Framework Goal

> **Status:** Phases 1, 2, 3 and 5 implemented (this branch). Phase 4
> (desktop foundation, Windows 11 first) remains planned — needs a Windows
> box to validate.
> Reviewed: `docs/architecture.md`, `docs/guide.md`, `plans/*` (future-roadmap,
> BFRAME_0034 agent architecture, NOOD_0006 LLM selection, pattern-coverage,
> peer review), `QUICK_START_GUIDE.md`, `QUICK_START_AGENTIC.md`, and the
> actual code under `noodle/`.

The target: a "codeless" framework where a user prompts test cases to an
agent (local LLM or hosted), the agent generates `.feature` + supporting
files, and the engine runs them — while hand-written `.feature` files work
identically with no agent at all. Web / REST / Desktop test types.

---

## Verdict per specification item

| # | Spec | Verdict | Evidence |
|---|------|---------|----------|
| 1.1 | Agentic interface to the framework | ✅ **Capable** (with gaps) | `noodle-agent` REPL (`noodle/agent/repl.py`) — rule-based create/run/list/summary, `--llm ollama\|claude\|gemini` upgrade. BFRAME_0034 phases 1–5 delivered. |
| 1.2 | Agent generates correctly-formatted, pattern-conformant Gherkin | ⚠️ **Partial** | Template path (`generate.py`) is correct-by-construction but produces `<placeholder>` skeletons. LLM path prompts toward pattern vocabulary but **never validates its output** — no parse check, no resolver dry-run. `noodle validate` exists in the CLI but the agent never calls it. |
| 1.3 | Engine handles sentences outside the pattern dictionary | ✅ **Capable** | Trigger-1 LLM fallback (`step_resolver.py`) + `NOODLE_LLM_MODE=full`. Fails loudly when no model is set — by design. Hardening gaps remain (cost cap, caching, structured outputs — see NOOD_0006). |
| 1.4a | Web testing | ✅ **Capable** (mature) | Full pipeline: patterns → accessibility locator → POM → vision LLM; tabs, iframes, dialogs, uploads, network mocking, tracing, healing, Allure/JUnit, CI sharding. |
| 1.4a′ | Web — screen size | ⚠️ **Partial** | Only hardcoded `@mobile` → iPhone 13 / Pixel 5 emulation (`hooks.py:227`). No arbitrary viewport via tag, step, or `noodle.yaml`. |
| 1.4b | RESTful tests | ⚠️ **Partial** | Real step family exists (BFRAME_0029): request headers, GET/POST/PUT/PATCH/DELETE, status/body/header assertions (incl. table-driven), JSON key extraction into vars, `rest_client.py` standalone HTTP client. But every scenario still launches a browser (`hooks.py:222-224`), and no auth helper / JSONPath / schema assertion. |
| 1.4c | Desktop applications | ❌ **Weakest area** | `@visual` agent = OpenCV template match + Tesseract OCR + PyAutoGUI only (`agents/visual/`, ~330 lines). Pixel-based, not semantic — the "find by name, no selectors" promise does not hold on desktop. No window management, no app launch/teardown, no DPI/resolution normalization, no OS CI matrix. |

---

## Gap list (ranked)

### G-A — Agent generation has no validation loop (spec 1.2)

`generate_llm()` writes whatever the model returns straight to disk. Nothing
checks that (a) it parses as Gherkin, (b) each step resolves against
`patterns.match()`. A generated suite can silently depend on the runtime LLM
fallback — or fail outright — defeating "deterministic by default".

### G-B — No arbitrary screen-size control (spec 1.4a′, 1.4.1.1)

- **Web:** no `@viewport:1920x1080` tag, no `sets the viewport to W x H`
  step, no `viewport:` key in `noodle.yaml`. Responsive testing beyond two
  hardcoded phones is impossible without code changes.
- **Desktop:** OpenCV template matching is scale-sensitive. A template
  captured at 1080p/100% scaling misses at 4K/150%. No multi-scale matching,
  no DPI awareness. This is the single biggest reliability risk for the
  desktop path across Windows 11 / macOS / Linux (spec 1.4.1).

### G-C — Desktop is pixel-only, no native accessibility (spec 1.4c)

The web path finds elements by role/label/text. The desktop path cannot —
every element needs a pre-captured template image or OCR-able text. Windows
UIA, macOS Accessibility (AX), and Linux AT-SPI all expose the same
role/name semantics the web locator already uses; none are wired. Roadmap
items G2 (multi-word OCR) and G3 (window management) are still open;
multi-monitor (F3d) deferred.

### G-D — REST scenarios drag a browser along (spec 1.4b)

`before_scenario` unconditionally starts Playwright + Chromium for any
non-`@visual` scenario. A pure API suite pays browser startup per scenario
and requires browser binaries in API-only CI. Also missing: bearer/basic
auth convenience step, JSONPath (nested extraction), response-schema
assertion.

### G-E — No app-lifecycle primitive (all test types, from NOOD_0006 gap 2)

No way to declare "start the app under test, wait until healthy, tear down
even on failure". Desktop testing especially needs *launch app → test →
kill app*. Today it's DIY `run_command` with no readiness gate and no
guaranteed teardown.

### G-F — LLM path hardening (spec 1.3, carried from NOOD_0006 / roadmap Phase I)

No cost cap (`NOODLE_LLM_MAX_CALLS` planned, not built), no caching of
identical step-text resolutions across scenarios, fence-strip JSON parsing
instead of structured outputs, no provider failover.

### G-G — Agent interface is single-shot, not conversational

The REPL keyword-matches one command at a time. The stated goal — "user
prompts the test cases via an LLM" — implies iterating on a scenario in
dialogue ("add a step that…", "make it also check X"). There is also no
programmatic surface (MCP server or importable API) so an *external* agent
(Claude Code, Copilot, etc.) could drive the framework as a tool; today it
would have to shell out to the CLI blind.

---

## Proposed plans

Ordered by (impact × effort). Phases 1–3 close the spec for web + agent;
4–5 build out REST and Desktop.

### Phase 1 — Generation validation loop (G-A) — ~1–2 days

1. After `generate_llm()` (and template generation), run the output through
   behave's parser, then `patterns.match(normalize_subject(step))` per step.
2. Report per step: `[pattern]` deterministic / `[LLM]` will need runtime
   fallback / `[parse-error]`.
3. If `--llm` is active and unmatched steps exist, one retry: feed the model
   the unmatched steps + the closest pattern phrasings ("rewrite using this
   vocabulary"). One retry only — then write the file with the report.
4. Expose the same check as `noodle validate --resolve <file>` so
   hand-written features (agentless path) get identical feedback.
5. Ship the step dictionary (`docs/steps_dictionary.md`) into the generation
   prompt so the model sees the real vocabulary instead of four examples.

### Phase 2 — Viewport / screen-size control (G-B web) — ~0.5 day

1. `@viewport:1920x1080` scenario tag → `ctx_opts["viewport"]` in
   `before_scenario` (next to the existing `@mobile` block).
2. Pattern: `sets the viewport to "1920x1080"` → `page.set_viewport_size`.
3. `viewport:` key in `noodle.yaml` + `NOODLE_VIEWPORT` env as run-wide
   default.

### Phase 3 — REST without a browser (G-D) — ~1.5 days

1. `@api` tag: skip Playwright launch in `before_scenario`; route steps
   through `rest_client` only. Guard web-only actions with a clear error.
2. **Auth best-practice steps** (decision #3 — cover the standard cases):
   - `sets the bearer token to '[TOKEN]'` (sugar over the header step)
   - `uses basic auth with '[USER]' and '[PASS]'` (base64, never logged)
   - `sets the API key header '<name>' to '[KEY]'`
   - `fetches an OAuth2 token from '<url>' with client '[ID]' and secret
     '[SECRET]'` → client-credentials grant, stores token + expiry.
   Edge cases: credentials always via `[VAR]` substitution so secrets stay
   out of feature files and logs; redact `Authorization`/key headers in
   Allure attachments and log output; on 401 with a stored OAuth2 token,
   refresh once and retry the call once (never loop).
3. Dotted-path extraction: `extracts 'data.items[0].id' …` (small recursive
   walk in `rest_extract_json` — no new dependency).
4. Defer JSON-schema assertion until a real suite needs it.

### Phase 4 — Desktop foundation (G-C, G-B desktop, G-E) — ~2–3 weeks, sequenced

Do the already-planned cheap fixes first, then the strategic one:

1. **G2 multi-word OCR** + **G3 window management** from the existing
   roadmap (~1.5 days combined) — unblock basic desktop reliability.
2. **App lifecycle steps** (G-E): `launches the app "cmd"` /
   `the app should be running` (health = window-title or port probe) /
   auto-kill in `after_scenario` even on failure. Mirrors `@precondition`'s
   teardown guarantee. (~2 days)
3. **Scale-invariant matching** (G-B): try template at 3–5 scales
   (0.75–1.5×) in `matcher.py`; record the winning scale per session and try
   it first. Cheap insurance across DPI/resolutions. (~1 day)
4. **Native accessibility driver** — the strategic bet. One new
   `agents/desktop_native/` behind a `@desktop` tag, reusing the existing
   resolver + action dicts:
   - **Windows 11: UIA via `pywinauto` (`[desktop]` extra) — first, per
     decision #1.** Validation target: the built-in Calculator app
     (decision #4) — stable, ships with the OS, rich UIA tree.
   - macOS: AX API via `atomacos` (or `pyobjc` directly) — stubbed for now
   - Linux: AT-SPI via `pyatspi` — stubbed for now
   Locator mirrors the web chain: role/name → POM YAML → vision LLM.
   (~1–2 weeks, Windows first)
5. **CI:** desktop suites need GUI-capable agents (self-hosted or
   `xvfb`+Linux for smoke). Document the matrix; don't block on it.

### Phase 5 — LLM hardening (G-F) — ~1–2 days

1. Roadmap Phase I cost cap (`NOODLE_LLM_MAX_CALLS`) as specced.
2. In-run memo cache in `step_resolver`: identical normalized step text →
   same action dict, one model call per unique sentence per run.
3. Structured outputs where the provider supports it (Claude `strict` tool
   schema via LiteLLM), keeping fence-strip as fallback — per NOOD_0006 §2.

### Explicitly not planned (YAGNI)

- Conversational multi-turn REPL rewrite (G-G) — Phase 1's validation loop +
  `create test` covers the workflow; a dialogue loop is polish. Revisit
  after Phase 1 lands and real usage shows the need.
- MCP server surface — deferred per decision #2: external agents are the
  fallback when the local LLM underperforms, not the primary interface.
  Revisit only when a concrete external-agent consumer appears.
- JSON-schema response assertions, multi-monitor, Win32/COM — on-demand.

---

## Decisions (2026-07-01)

The open questions from the first draft were answered:

1. **Desktop OS: Windows 11 first.** UIA/`pywinauto` is the driver choice;
   macOS/Linux drivers are stubs until Windows is stable.
2. **Agent hierarchy: local LLM is the primary agent path**, external agents
   (Claude Code etc.) are the fallback when the local model underperforms —
   and the framework must keep working with **no LLM at all** (the existing
   deterministic default is non-negotiable). Practical consequence: every
   agent feature (generation, validation retry, summaries) must run against
   an Ollama-class local model, not assume a frontier model; the rule-based
   / template path stays as the zero-LLM floor.
3. **REST auth: implement best practices** — bearer, basic, API-key header,
   OAuth2 client-credentials, with secret redaction and a single 401
   refresh-retry. Folded into Phase 3.
4. **Desktop validation app: the default (Windows) Calculator** when one is
   needed; no dedicated app-under-test for now. Folded into Phase 4.4.
