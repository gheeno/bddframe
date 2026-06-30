@web @headless
Feature: Canadian Tire Product Search

  # Guest user, three real pages: home -> search results -> product detail.
  # The search box / submit / first-result have no usable accessible label,
  # so they resolve via the per-page files in pageobjects/ (home_pom.yaml,
  # results_pom.yaml), scoped by URL.
  # Single-word locator keys (searchbox, searchbutton, firstresult) are used
  # on purpose: a multi-word label triggers the partial-text self-heal, which
  # would grab the wrong button before the POM is consulted.

  @web @smoke
  Scenario: Guest searches for a product and opens the first result
    Given User is on "https://www.canadiantire.ca"
    And User waits 5 seconds
    When User enters "mastercraft tool box" in the searchbox field
    And User clicks the searchbutton
    And User waits until "Mastercraft" is visible
    And User clicks the firstresult
    And User waits until "Mastercraft" is visible
    Then User should see "Mastercraft"
    And User should have url containing "pdp"

  @web
  Scenario: Search results page shows relevant products
    Given User is on "https://www.canadiantire.ca"
    And User waits 5 seconds
    When User enters "mastercraft tool box" in the searchbox field
    And User clicks the searchbutton
    And User waits until "Mastercraft" is visible
    Then User should have url containing "search-results"
    And User should see "Mastercraft"
