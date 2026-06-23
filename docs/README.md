# BDDFrame — Design Documentation

## Core idea

A QA writes a `.feature` file in plain Gherkin sentences. No step definitions. No selectors. No code. BDDFrame reads each sentence, understands it with an LLM, and runs the test using Playwright (web), OpenCV (visual/desktop), or Appium (mobile).

## Overall architecture

```mermaid
flowchart TD
    QA["👤 QA Analyst\nwrites .feature file\nin plain sentences"] --> F["📄 checkout.feature\nGherkin format"]

    F --> P["behave Parser\nbreaks file into steps"]
    P --> O["LangGraph Orchestrator\nroutes each step"]

    O --> R{"Step Router"}
    R -->|web action| W["🌐 Web Agent\nPlaywright"]
    R -->|visual action| V["🖥️ Visual Agent\nOpenCV + PyAutoGUI"]
    R -->|mobile action| M["📱 Mobile Agent\nAppium"]

    W & V & M --> C["Result Collector\npass / fail + screenshot"]
    C --> Rep["📊 Allure Report\nannotated screenshots\nJUnit XML for Azure DevOps"]

    style QA fill:#e8f5e9
    style F fill:#e8f5e9
    style Rep fill:#e3f2fd
```

## Phases

| Phase | Topic | Status |
|-------|-------|--------|
| [1 — Foundation](phase-01-foundation.md) | Parser, LLM backend, orchestrator, step resolver | Planned |
| [2 — Web Agent](phase-02-web-agent.md) | Playwright, intent locators, semantic assertions, self-healing | Planned |
| [3 — Visual Agent](phase-03-visual-agent.md) | OpenCV, OCR, vision LLM, desktop automation | Planned |
| [4 — Reporting](phase-04-reporting.md) | Allure, JUnit XML, annotated screenshots | Planned |
| [5 — CLI, Recorder & Azure DevOps](phase-05-cli-devops.md) | CLI, flow recorder, pipeline YAML | Planned |
| [6 — Syntax Highlighting](phase-06-syntax-highlighting.md) | VS Code extension, variable highlighting, tag autocomplete | Planned |

## Design principles

1. **The `.feature` file is the only QA artifact.** No Python, no YAML, no JSON config alongside it.
2. **Sentences over syntax.** Steps are plain English. The LLM interprets them — no regex matching.
3. **Accessibility tree before LLM.** Elements are found by role, label, and text first. LLM is the fallback, not the default.
4. **Semantic assertions.** "The screen should look the same as before" is a valid, runnable assertion.
5. **Evidence-first failures.** Every failure includes an annotated screenshot showing exactly what went wrong and where.
6. **All open source.** Every dependency has a permissive license.
