"""Plain-English run summary from allure-results/*.json. No LLM needed.

Reads the same per-scenario JSON the Allure report is built from (see
reporting/writer.py) and prints a human glance: pass/fail counts, which
scenario failed at which step, total time.
"""
import json
from datetime import date
from pathlib import Path


def collect(results_dir: str = "allure-results") -> dict:
    """Aggregate result JSON into counts, failures, and total wall time."""
    d = Path(results_dir)
    files = sorted(d.glob("*-result.json")) if d.is_dir() else []
    passed = failed = 0
    failures = []
    starts, stops = [], []
    for f in files:
        try:
            r = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if "start" in r:
            starts.append(r["start"])
        if "stop" in r:
            stops.append(r["stop"])
        if r.get("status") == "passed":
            passed += 1
        elif r.get("status") == "failed":
            failed += 1
            step = next((s["name"] for s in r.get("steps", [])
                         if s.get("status") == "failed"), "")
            feature = next((l["value"] for l in r.get("labels", [])
                            if l["name"] == "feature"), "")
            failures.append({"feature": feature, "scenario": r.get("name", ""),
                             "step": step})
    secs = round((max(stops) - min(starts)) / 1000) if starts and stops else 0
    return {"passed": passed, "failed": failed, "failures": failures, "seconds": secs}


def render(results_dir: str = "allure-results", report_dir: str = "reports/allure-report") -> str:
    s = collect(results_dir)
    lines = [f"Run summary — {date.today().isoformat()}",
             f"✅  {s['passed']} passed",
             f"❌  {s['failed']} failed"]
    for fl in s["failures"]:
        at = f"  failed at: {fl['step']}" if fl["step"] else ""
        lines.append(f"   • {fl['feature']} > {fl['scenario']}{at}")
    lines.append(f"⏱️  Total: {s['seconds']}s")
    if Path(report_dir).exists():
        lines.append(f"\nAllure report → {report_dir}/index.html")
    return "\n".join(lines)


def summarize_llm(results_dir: str = "allure-results") -> str:
    """Opt-in richer narrative — hand the structured counts to a local/paid model."""
    from noodle.llm.client import ask
    s = collect(results_dir)
    return ask(
        "Summarise this test run for a developer in 3-4 sentences, calling out the "
        f"likely root cause of any failures:\n{json.dumps(s, indent=2)}"
    ).strip()
