# Noodle Test Framework — Documentation

A QA writes a `.feature` file in plain Gherkin sentences. No step definitions, no
selectors, no code. Noodle Test Framework reads each sentence, finds the element by what it
*is* (role / label / text), runs it with Playwright (web) or OpenCV (visual), and
produces an annotated Allure report. An LLM is an **optional, opt-in fallback** —
off by default.

## Start here

| Doc | For | What's in it |
|-----|-----|--------------|
| **[../README.md](../README.md)** | everyone | Overview, tech stack, quick setup, BusterBlock. The front door. |
| **[Glossary](glossary.md)** | everyone | Where to find everything — env vars, YAML files, outputs, resources. |
| **[Guide](guide.md)** | new & veteran testers | The complete how-to: install → write → run → `pom.yaml` → shared state → reports → CI → LLM setup. |
| **[Steps Dictionary](steps_dictionary.md)** | testers | All built-in step patterns with phrasings and examples. |
| **[Architecture](architecture.md)** | learning the tech | Deep dive: components, resolution hierarchy, the LLM layer, tech stack. |
| **[Design History](design-history.md)** | maintainers | The rationale trail behind every capability, condensed from the build phases. |

## Quick links

- **How do I run the bundled BusterBlock test app?** → [README → Run the bundled test app](../README.md#run-the-bundled-test-app-busterblock).
- **How do I seed data before a test (preconditions/teardowns)?** → [README → Preconditions & teardowns](../README.md#preconditions--teardowns).
- **How do I run a Python/JS/jar/shell script from a step?** → [README → Run a script from a step](../README.md#run-a-script-from-a-step).
- **When does the LLM run, and which sample test triggers it?** → [Architecture → The LLM layer](architecture.md#5-the-llm-layer).
- **How does step wording map to `pom.yaml` keys?** → [Guide → pom.yaml](guide.md#5-pomyaml--when-natural-naming-fails).
- **Local agent vs LLM, step by step?** → [Architecture → Resolution hierarchy](architecture.md#4-the-resolution-hierarchy).
- **Every library and why?** → [Architecture → Tech stack](architecture.md#7-the-tech-stack).
- **Full list of built-in steps?** → [Guide → Built-in step reference](guide.md#6-built-in-step-reference).

## Plans & historical reviews

Implementation plans, phase documents, and point-in-time reviews live in **[../plans/](../plans/)**:

| File | Contents |
|------|----------|
| `future-roadmap.md` | Phases E–K — parallelism, Appium, desktop gaps, remote browser, LLM cost cap, multi-context, step retry |
| `enterprise-plan.md` | Enterprise assessment (Phases A–D, all implemented) + future plans origin |
| `pattern-coverage.md` | BFRAME_0025 coverage review — step gaps, missing actions, phases |
| `peer-review-2026-06-28.md` | Peer review after Phases A–D (all 7 items implemented) |
| `preconditions-plan.md` | Phase 13 implementation plan — BusterBlock test seam + preconditions runner |
