# BDDFrame — Documentation

A QA writes a `.feature` file in plain Gherkin sentences. No step definitions, no
selectors, no code. BDDFrame reads each sentence, finds the element by what it
*is* (role / label / text), runs it with Playwright (web) or OpenCV (visual), and
produces an annotated Allure report. An LLM is an **optional, opt-in fallback** —
off by default.

## Start here

| Doc | For | What's in it |
|-----|-----|--------------|
| **[../README.md](../README.md)** | everyone | Elevator pitch, install, run, report, the LLM in brief. The front door. |
| **[Guide](guide.md)** | new & veteran testers | The complete how-to: install → write → run → `pom.yaml` → shared state → reports → CI → editor. |
| **[Architecture](architecture.md)** | learning the tech | One-stop deep dive (study it like Selenium/Appium/Selenide): mental model, component map, request lifecycle, resolution hierarchy, the LLM layer, tech stack — with Mermaid diagrams throughout. |
| **[Design History](design-history.md)** | maintainers | The rationale trail behind every capability, condensed from the build phases. |

## Quick links

- **How do I run the bundled BusterBlock test app?** → [README → Run the bundled test app](../README.md#run-the-bundled-test-app-busterblock).
- **How do I seed data before a test (preconditions/teardowns)?** → [README → Preconditions & teardowns](../README.md#preconditions--teardowns) · plan: [preconditions-plan.md](preconditions-plan.md).
- **How do I run a Python/JS/jar/shell script from a step?** → [README → Run a script from a step](../README.md#run-a-script-from-a-step).
- **When does the LLM run, and which sample test triggers it?** → [Architecture → The LLM layer](architecture.md#5-the-llm-layer) (`features/fallback-demo/llm_fallback.feature`).
- **How does step wording map to `pom.yaml` keys?** → [Guide → pom.yaml](guide.md#5-pomyaml--when-natural-naming-fails).
- **Local agent vs LLM, step by step?** → [Architecture → Resolution hierarchy](architecture.md#4-the-resolution-hierarchy).
- **Every library and why?** → [Architecture → Tech stack](architecture.md#7-the-tech-stack).
</content>
