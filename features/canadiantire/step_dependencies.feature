# ============================================================================
# STEP DEPENDENCIES DEMO (Phase 12) — live site (canadiantire.ca).
#
# Flow: search "mastercraft" -> capture the first result's title into [TITLE]
#       -> go back home -> search for [TITLE] -> the new first result's title
#       must EQUAL the one captured earlier.
#
#   [TITLE] is the shared store (context._vars, scenario-scoped). It is written
#   by `stores ... as [TITLE]` and substituted back into the later search step
#   BEFORE it runs — the BDDFrame equivalent of Spring dependency injection.
#
# Selectors (searchbox/searchbutton/firstresult) come from this folder's
# pom.yaml — the search box / button / first result have no usable a11y label.
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
    # on /search-results, where the firstresult POM selector applies)
    When User enters "mastercraft tool box" in the searchbox field
    And User presses Enter
    And User waits until "Mastercraft" is visible
    And User waits 5 seconds

    # capture the first result's title into the shared store
    And User stores the firstresulttitle as [TITLE]

    # go back to the main page
    And User is on "https://www.canadiantire.ca"
    And User waits 5 seconds

    # search again, this time using the captured title ([TITLE] is substituted)
    And User enters "[TITLE]" in the searchbox field
    And User presses Enter
    And User waits until "Mastercraft" is visible
    And User waits 5 seconds

    # the new first result's title must match the one we captured first
    And User stores the firstresulttitle as [SECOND_TITLE]
    Then [SECOND_TITLE] should equal [TITLE]
