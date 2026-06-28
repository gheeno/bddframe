@web @headless
Feature: Assertions — visibility, URL, title, state, count, attribute, and comparison
  # Exercises: should see X, should not see X, should have url containing,
  # page title should contain, the X field should contain Y, should see N items,
  # the X should be enabled/disabled, stores X as [VAR], [VAR] should contain Y.
  #
  # Capability tier: PATTERN — all resolved locally, zero LLM cost.

  @smoke
  Scenario: Assert text is visible on the page
    Given User is on '[UITESTINGPLAYGROUND]/verifytext'
    Then User should see "Welcome UserName!"

  @smoke
  Scenario: Assert text is NOT visible on the page
    Given User is on '[UITESTINGPLAYGROUND]/sampleapp'
    Then User should not see "Welcome"

  @smoke
  Scenario: Assert URL fragment after navigation
    Given User navigates to '[UITESTINGPLAYGROUND]/dynamicid'
    Then User should have url containing 'dynamicid'

  @smoke
  Scenario: Assert page title contains expected string
    Given User is on '[UITESTINGPLAYGROUND]/sampleapp'
    Then the page title should contain "UI Test AutomationPlayground"

  @smoke
  Scenario: Assert a button is enabled (default state)
    Given User is on '[UITESTINGPLAYGROUND]/sampleapp'
    Then the 'Log In' button should be enabled

  @smoke
  Scenario: Assert login status label becomes visible after login
    Given User is on '[UITESTINGPLAYGROUND]/sampleapp'
    When User enters 'admin' in the User Name field
    And User enters 'pwd' in the password field
    And User clicks the Log In button
    Then User should see "Welcome, admin!"
    And User should not see "Invalid username/password"

  @smoke
  Scenario: Count visible elements on a page
    # The home page lists multiple test scenario cards.
    Given User is on '[UITESTINGPLAYGROUND]/'
    Then User should see "Dynamic ID"
    And User should see "Click"
    And User should see "Text Input"

  @smoke
  Scenario: Store element text and compare via variable
    Given User is on '[UITESTINGPLAYGROUND]/sampleapp'
    When User enters 'admin' in the User Name field
    And User enters 'pwd' in the password field
    And User clicks the Log In button
    Then User stores the login status as `LOGIN_MSG`
    And `LOGIN_MSG` should contain 'Welcome'
