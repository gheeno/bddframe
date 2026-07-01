"""Healing telemetry — what the locator layer had to repair, and how.

Healenium/Autoheal's real value isn't the heal itself, it's the *record*: which
locator broke and what it healed to, surfaced for review. Noodle heals
structurally (accessibility-first, so there's rarely a brittle selector to break)
but never reported it. This does.

Every self-heal (scroll/partial), POM disambiguation, and vision-LLM locate is
recorded; at end of run `write_report` emits a JSONL log + pom.yaml suggestions
so a flaky-by-naming locator becomes a one-line POM fix instead of a mystery.
"""
import json
from pathlib import Path

from noodle.log import logger

# Module-level run log. Cleared per run by hooks.before_all.
EVENTS: list[dict] = []


def record(locator: str, strategy: str, detail: str = ""):
    """Note that `locator` was resolved by a non-primary `strategy`."""
    EVENTS.append({"locator": locator, "strategy": strategy, "detail": detail})


def reset():
    EVENTS.clear()


def _suggestions() -> list[str]:
    """One pom.yaml line per distinct locator that needed healing — the fix that
    makes the resolution deterministic next time."""
    seen = {}
    for e in EVENTS:
        seen.setdefault(e["locator"], e["strategy"])
    return [f'  {loc.lower()}: ""   # was healed via {strat} — add a real selector'
            for loc, strat in seen.items()]


def write_report(path: str = "healing-report.txt"):
    """Write the JSONL log + human summary. No-op when nothing healed."""
    if not EVENTS:
        return
    jsonl = Path(path).with_suffix(".jsonl")
    jsonl.write_text("\n".join(json.dumps(e) for e in EVENTS) + "\n")

    lines = [
        f"Noodle healing report — {len(EVENTS)} event(s) this run.",
        "These locators did NOT resolve on the primary accessibility match.",
        "Add the suggested pom.yaml keys to make them deterministic:",
        "",
        *(f"  • '{e['locator']}' — {e['strategy']}"
          + (f" ({e['detail']})" if e["detail"] else "") for e in EVENTS),
        "",
        "Suggested pom.yaml entries:",
        *_suggestions(),
    ]
    report = "\n".join(lines)
    Path(path).write_text(report + "\n")
    logger.info(f"\n  🩹 {len(EVENTS)} locator(s) needed healing — see {path}")
