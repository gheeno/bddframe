# ============================================================================
# STEP DEPENDENCIES DEMO (Phase 12) — live site (canadiantire.ca).
#
# Flow: search "mastercraft tool box" -> capture the first result's title into
#       `title` -> go back home -> search for `title` -> the new first result's
#       title must EQUAL the one captured earlier.
#
# Variable syntax:
#   `name`  → a value CAPTURED during this run (scenario-scoped store).
#   [name]  → a value from .env / config (e.g. [SAUCE_USERNAME]).
#   `name` is written by `stores ... as `name`` and substituted back into a
#   later step BEFORE it runs — the BDDFrame equivalent of dependency injection.
#
# Selectors (searchbox/firstresulttitle) come from this folder's pom.yaml —
# the search box / first result have no usable accessibility label.
#
# Run it:   behave features/canadiantire/step_dependencies.feature --no-capture
# Live site: needs network + the 5s waits; titles are read from the live DOM.
# ============================================================================
@web @headless @step_dependencies
Feature: Step Dependencies and Shared State

  @web @smoke
  Scenario: Capture a result's title, then reuse it in a fresh search
    Given User is on "https://www.canadiantire.ca"
    And User waits 5 seconds

    # search for a product, land on the results page (multi-word query keeps us
    # on /search-results, where the firstresulttitle POM selector applies)
    When User enters "mastercraft tool box" in the searchbox field
    And User presses Enter
    And User waits until "Mastercraft" is visible
    And User waits 5 seconds

    # capture the first result's title into the shared store
    And User stores the firstresulttitle as `title`

    # go back to the main page
    And User is on "https://www.canadiantire.ca"
    And User waits 5 seconds

    # search again, this time using the captured title (`title` is substituted)
    And User enters "`title`" in the searchbox field
    And User presses Enter
    And User waits until "Mastercraft" is visible
    And User waits 5 seconds

    # the new first result's title must match the one we captured first
    And User stores the firstresulttitle as `second_title`
    Then `second_title` should equal `title`
