# Run Examples

Copy-paste commands for the three things people actually want: **see the logs**,
**see the Allure report**, **see the Azure DevOps dashboard**.

Prereqs once:

```bash
uv pip install -e ".[all]"        # framework + all extras
playwright install chromium        # the browser binary (not pip-installable)
```

---

## 1. Run a test and watch the logs

Capture is already off (`behave.ini` sets `*_capture = false`) and `bddframe
run` passes `--no-capture`, so everything streams live — no flags needed.

```bash
# whole suite
bddframe run features/

# one feature, headed (watch the browser), filter by tag
bddframe run features/saucedemo/login.feature --headed
bddframe run features/ --tag smoke

# the LLM-fallback demo (needs a model configured — see llm.md / phase-10)
bddframe run features/fallback-demo/llm_fallback.feature --headed
```

**What to watch for in the output** — these lines prove which resolution path fired:

| Log line | Means |
|----------|-------|
| `📋 POM: resolved '<key>' via pom.yaml` | accessibility missed → POM fallback hit |
| `🔧 Healed: found '<text>' via vision LLM` | both missed → vision LLM (Trigger 2) hit |
| (a step that's neither matched nor errored) | resolved by the accessibility tree, free |

Raw behave (same thing, without the CLI wrapper):

```bash
behave features/ --no-capture
behave features/ --no-capture -D ...   # behave's own flags
```

### See the model exchange (LLM smoke test)

To watch exactly what a step sentence sends the model and gets back:

```bash
uv run --with litellm --with pytest python tests/test_llm_openai_endpoint.py
```

Prints the prompt bddframe sent, the model's raw reply, and the parsed action.

### Unit tests (no browser)

```bash
make test            # == python -m pytest tests/ -v
```

---

## 2. Run a test and see the Allure report

Results are written to `allure-results/` during the run. Turn them into the HTML
report with the built-in `report` commands (they shell out to the **Allure CLI**,
so install it first).

```bash
# install the Allure CLI binary (not pip)
brew install allure            # macOS
#  scoop install allure        # Windows
#  npm i -g allure-commandline # any OS

# 1. run (produces allure-results/)
bddframe run features/

# 2. build the HTML report (allure-results/ -> allure-report/)
bddframe report generate

# 3. open it in the browser
bddframe report open
```

One-shot alternative (build + serve in one step, temp report):

```bash
allure serve allure-results
```

Re-generating from existing results without re-running tests:

```bash
bddframe report generate allure-results --out allure-report
bddframe report open allure-report
```

> If `report generate` does nothing, the Allure CLI isn't on PATH — `builder.py`
> skips silently when `allure` is missing.

---

## 3. See the Azure DevOps dashboard

### What's implemented today

The pipelines (`azure-pipelines.yml` Linux, `azure-pipelines-windows.yml`
Windows) already publish results on every run to `main` / `develop`:

| Pipeline step | Where it shows up in Azure DevOps |
|---------------|-----------------------------------|
| `PublishTestResults@2` (JUnit `allure-results/junit.xml`) | **Pipeline run → Tests tab** — native pass/fail dashboard, trends, per-test history. This is your dashboard. |
| `PublishPipelineArtifact@1` (`allure-report`) | **Pipeline run → Artifacts → TestReport** — the Allure HTML, as a **downloadable zip** (open `index.html` locally). |

So you get a real Azure dashboard for free (the **Tests tab**), driven by the
JUnit XML. To see it: push to `main`/`develop` (or run the pipeline manually),
open the run, click **Tests**.

Run it locally the same way the pipeline does, to produce the same artifacts:

```bash
bddframe run features/ --headless     # writes allure-results/junit.xml + allure-report/
```

### What's NOT implemented (the gap)

- The Allure HTML is a **downloadable artifact**, not a **rendered/hosted
  dashboard** inside Azure DevOps. You can't click it and see the rich Allure UI
  in the browser without downloading it (or installing the Allure Azure DevOps
  extension).
- There is **no REST-API integration** pushing results to an external dashboard
  or to Azure Test Plans beyond the built-in JUnit publish.

That gap is captured as a user story below.

---

## User story — Hosted Allure dashboard in Azure DevOps

> **As a** QA lead
> **I want** the Allure report rendered as a browsable dashboard inside Azure
> DevOps (not a zip to download)
> **so that** the team can see rich test results, trends, and failure
> screenshots without downloading artifacts.

**Acceptance criteria**
- A pipeline run links to a browsable Allure dashboard from the run summary.
- History/trends persist across runs (Allure history folder carried between builds).
- Failure screenshots and steps are visible inline.
- Works on both the Linux and Windows pipelines.

**Candidate approaches** (pick one during refinement — ponytail: lightest first):
1. **Allure Azure DevOps marketplace extension** — adds an "Allure" tab that
   renders the published results. Least code; just install + a pipeline task.
2. **Publish to static hosting** — push `allure-report/` to Azure Static Web
   Apps / a storage `$web` container; link the URL from the run.
3. **REST push** — only if a *custom* external dashboard is required; build a
   small step that POSTs results to it. Heaviest — avoid unless 1 & 2 can't meet
   the need.

**Out of scope**: replacing the native Tests-tab JUnit dashboard (keep it).

`# ponytail: the Tests tab already gives a working dashboard. This story is the nice-to-have rich view, not a blocker.`

Suggested branch/id when picked up: `BFRAME_00XX`.
