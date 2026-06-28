# ============================================================================
# STEP DEPENDENCIES DEMO (Phase 12) — live site (canadiantire.ca).
#
# Flow: go to the site -> close popups -> search "mastercraft toolbox" ->
#       GRAB the second result's title (a value only known at runtime) ->
#       ASSERT it equals the known expected title.
#
# The dependency is on the grab step: `result` holds the live second-result
# title, and the next step asserts that captured value against a literal.
#
# Variable syntax:
#   "literal"  → a fixed string you type (the URL, the search, the expected title)
#   `name`     → a value CAPTURED during this run (scenario-scoped store)
#   [name]     → a value from .env / config (e.g. [SAUCE_USERNAME])
#
# Selectors (searchbox/secondresulttitle) come from this folder's pom.yaml.
#
# Run it:   behave features/canadiantire/step_dependencies.feature --no-capture
# Live site: needs network + the settle waits; ordering can change over time, so
# the expected title may need updating if Canadian Tire reorders results.
# ============================================================================
@web @headless @step_dependencies
Feature: Step Dependencies and Shared State

  @web @smoke
  Scenario: Grab the second result's title and assert its value
    Given User is on "https://www.canadiantire.ca"
    And User waits 5 seconds
    And User closes all popups

    When User searches for "mastercraft toolbox"
    And User waits until "Mastercraft" is visible
    And User waits 5 seconds

    # grab the second result's title into the shared store (the dependency)
    And User grabs the secondresulttitle as `result`

    # assert the captured value equals the actual expected title
    Then `result` should equal "Mastercraft Mini Toolbox with 2 Drawers, Lilac"
