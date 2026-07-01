"""Resolver dry-run for .feature text (NOOD_0007).

Answers one question before anything runs: which steps resolve
deterministically via the pattern table, and which would need the LLM
fallback (or fail with no model set)? Used by the agent after generation
and by `noodle validate --resolve` for hand-written features — same check,
agent or no agent.
"""
from noodle.resolver.patterns import match as pattern_match, normalize_subject

# Steps a table is attached to resolve via patterns but carry their data in
# the Gherkin table, which behave strips from step.name — nothing special
# needed, the pattern regexes already accept the bare sentence.


def check_feature(text: str, filename: str = "<generated>") -> dict:
    """Parse feature text and classify every step.

    Returns {"error": str|None, "steps": [(step_line, matched: bool)]}.
    A parse failure returns error and no steps — the file isn't Gherkin.
    """
    from behave.parser import parse_feature, ParserError
    try:
        feature = parse_feature(text, filename=filename)
    except ParserError as e:
        return {"error": str(e), "steps": []}
    if feature is None:                     # empty / comment-only file
        return {"error": None, "steps": []}

    steps = []
    if feature.background:
        steps.extend(feature.background.steps)
    for scenario in feature.scenarios:
        steps.extend(scenario.steps)

    results = []
    for step in steps:
        line = f"{step.keyword} {step.name}"
        matched = pattern_match(normalize_subject(step.name)) is not None
        results.append((line, matched))
    return {"error": None, "steps": results}


def unmatched(result: dict) -> list[str]:
    return [line for line, ok in result["steps"] if not ok]


def render(result: dict) -> str:
    """Human-readable per-step report."""
    if result["error"]:
        return f"  ✗ parse error: {result['error']}"
    lines = []
    for line, ok in result["steps"]:
        lines.append(f"  {'[pattern]' if ok else '[LLM]    '} {line}")
    misses = unmatched(result)
    if misses:
        lines.append(
            f"\n  ⚠️  {len(misses)} step(s) need the LLM fallback at run time "
            "(NOODLE_MODEL) — or rephrase to a pattern (see docs/steps_dictionary.md)."
        )
    else:
        lines.append("\n  ✅ all steps resolve deterministically — no LLM needed.")
    return "\n".join(lines)
