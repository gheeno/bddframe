@headless
Feature: Canadian Tire Product Search

  # Guest user browses across three pages:
  # Home → Search Results → Product Detail
  # No POM entries needed if the agent resolves all elements naturally.
  # See pom.yaml in this folder for fallback selectors.

  @web @smoke
  Scenario: Guest user searches for a product and views its details

    Given User is on "https://www.canadiantire.ca"
    When User fills in "mastercraft tool box" in the search bar
    And User wait for the page to load
    And User clicks the first result
    Then User should see "MASTERCRAFT"
    And User should see "Tool Box"

  @web
  Scenario: Search results page loads with relevant products

    Given User is on "https://www.canadiantire.ca"
    When User fills in "mastercraft tool box" in the search bar
    And User wait for the page to load
    Then User should have url containing "search"
    And User should see "mastercraft"
    And User should not see "No results found"
