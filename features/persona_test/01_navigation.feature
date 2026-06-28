@web @headless
Feature: Navigation — URL routing, history, reload, and title assertions
  # Exercises: navigates to, is on, opens, goes to, goes back, goes forward,
  # reloads page, page title assertion, URL fragment assertion.
  #
  # Capability tier: PATTERN — all steps resolved locally, zero LLM cost.

  @smoke
  Scenario: Navigate to the playground home using navigates-to phrasing
    Given User navigates to '[UITESTINGPLAYGROUND]/'
    Then User should see "UI Test AutomationPlayground"

  @smoke
  Scenario: Navigate to a sub-page and assert URL fragment
    Given User navigates to '[UITESTINGPLAYGROUND]/sampleapp'
    Then User should have url containing 'sampleapp'
    And User should see "Sample App"

  @smoke
  Scenario: Navigate using is-on phrasing (Given sugar)
    Given User is on '[UITESTINGPLAYGROUND]/textinput'
    Then User should see "Text Input"

  @smoke
  Scenario: Navigate using opens phrasing
    Given User opens '[UITESTINGPLAYGROUND]/dynamicid'
    Then User should see "Button with Dynamic ID"

  @smoke
  Scenario: Navigate using goes-to phrasing
    Given User goes to '[UITESTINGPLAYGROUND]/click'
    Then User should see "Bad button"

  @smoke
  Scenario: Page title assertion
    Given User is on '[UITESTINGPLAYGROUND]/sampleapp'
    Then the page title should contain "UI Test AutomationPlayground"

  @smoke
  Scenario: Browser back and forward through history
    Given User is on '[UITESTINGPLAYGROUND]/dynamicid'
    Then User should see "Button with Dynamic ID"
    When User navigates to '[UITESTINGPLAYGROUND]/click'
    Then User should see "Bad button"
    When User goes back
    Then User should see "Button with Dynamic ID"
    When User goes forward
    Then User should see "Bad button"

  @smoke
  Scenario: Reload refreshes the page
    Given User is on '[UITESTINGPLAYGROUND]/dynamicid'
    Then User should see "Button with Dynamic ID"
    When User reloads the page
    Then User should see "Button with Dynamic ID"
