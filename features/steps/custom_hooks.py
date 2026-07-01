"""Custom hook registrations and project-local step definitions.

Two things live here:
  1. Hook registrations — fire around every scenario (before/after) without
     touching .feature files. See hooks.feature for usage.
  2. Custom step definitions — steps NOT in Noodle's built-in dictionary.
     Behave discovers all *.py in features/steps/ at startup. The z_ prefix
     on z_catch_all.py keeps it last in load order, so custom steps registered
     here are tried before the catch-all. See custom_steps.feature for usage.
"""
import csv
import os
import time
import uuid

from behave import then, when
from noodle.hooks import hook
from noodle.log import logger


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


# ---------------------------------------------------------------------------
# Custom step: CSV login
# Usage:  When a user from this list "users.csv" logs in
# The CSV file must live in resources/ relative to the current feature file.
# Row columns: username, password. Logs in as the first row only.
# See login.feature (@csv) and custom_steps.feature (@custom_step) for usage.
# ---------------------------------------------------------------------------
@when('a user from this list "{csv_path}" logs in')
def step_csv_login(context, csv_path):
    feature_dir = os.path.dirname(os.path.abspath(context.feature.filename))
    full_path = os.path.join(feature_dir, "resources", csv_path)
    with open(full_path, newline="") as fh:
        row = next(csv.DictReader(fh))
    context.execute_steps(f"""
        When User enters "{row['username']}" in the username field
        And User enters "{row['password']}" in the password field
        And User clicks the login button
    """)


# ---------------------------------------------------------------------------
# Custom assertion: catalog movie count
# Usage:  Then the catalog should have at least 10 movies
# Reads the #movie-count badge text (e.g. "15 movies") and asserts >= N.
# See custom_steps.feature (@custom_assert) for usage.
# ---------------------------------------------------------------------------
@then("the catalog should have at least {n:d} movies")
def step_catalog_min_count(context, n):
    badge = context.page.locator("#movie-count").inner_text()
    digits = "".join(ch for ch in badge if ch.isdigit())
    count = int(digits) if digits else 0
    assert count >= n, f"Expected at least {n} movies but badge shows: {badge!r}"
