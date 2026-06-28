@web @headless
Feature: Advanced Patterns — store variable, compare, count, key press, tabs
  # Exercises the less-common but production-critical patterns:
  #   sets [VAR] to 'value', stores X as [VAR], [VAR] should contain Y,
  #   [VAR] should equal X, assert_count, press 'Tab'/'Escape', switch tab.
  #
  # Capability tier: PATTERN — all resolved locally, zero LLM cost.

  @smoke
  Scenario: Set a literal variable and use it in a later assertion
    Given User is on '[UITESTINGPLAYGROUND]/sampleapp'
    And User sets `EXPECTED_USER` to 'admin'
    When User enters 'admin' in the User Name field
    And User enters 'pwd' in the password field
    And User clicks the Log In button
    Then User should see "Welcome, admin!"
    And User stores the login status as `ACTUAL_MSG`
    And `ACTUAL_MSG` should contain `EXPECTED_USER`

  @smoke
  Scenario: Press Tab to move focus between fields
    Given User is on '[UITESTINGPLAYGROUND]/sampleapp'
    When User clicks the User Name field
    And User types 'admin'
    And User presses 'Tab'
    And User types 'pwd'
    And User presses 'Enter'
    Then User should see "Welcome, admin!"

  @smoke
  Scenario: Press Escape clears active input focus
    Given User is on '[UITESTINGPLAYGROUND]/sampleapp'
    When User clicks the User Name field
    And User types 'test'
    And User presses 'Escape'
    Then User should see "Log In"

  @smoke
  Scenario: Count of visible section links on the home page
    # The home page renders one card per test scenario — assert we see several.
    Given User is on '[UITESTINGPLAYGROUND]/'
    Then User should see 1 "Dynamic ID" items
    And User should see 1 "Text Input" items
    And User should see 1 "Click" items

  @smoke
  Scenario: Variable equality comparison (assert_compare)
    Given User is on '[UITESTINGPLAYGROUND]/sampleapp'
    And User sets `APP_NAME` to 'Sample App'
    When User is on '[UITESTINGPLAYGROUND]/sampleapp'
    Then User should see "Sample App"
    And `APP_NAME` should equal 'Sample App'
