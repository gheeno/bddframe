"""Custom hook registrations — fires for every scenario in the run.

Drop this file (or any *.py in features/steps/) to add cross-cutting
behaviour without touching the .feature files or bddframe internals.
"""
import time
import uuid

from bddframe.hooks import hook
from bddframe.log import logger


@hook("before_scenario")
def assign_session(context, scenario):
    """Inject a short session ID and start a timer before each scenario."""
    context.session_id = str(uuid.uuid4())[:8]
    context._hook_start = time.monotonic()


@hook("after_scenario")
def log_timing(context, scenario):
    """Log elapsed time + session ID; extra audit line when @audit is present."""
    elapsed = time.monotonic() - getattr(context, "_hook_start", 0)
    status = "PASSED" if "passed" in str(scenario.status) else "FAILED"
    logger.info(
        f"\n  🪝 [{context.session_id}] {scenario.name} — {status} ({elapsed:.1f}s)"
    )
    if "audit" in scenario.effective_tags:
        logger.info(f"\n  📋 AUDIT: {scenario.feature.name} / {scenario.name}")
