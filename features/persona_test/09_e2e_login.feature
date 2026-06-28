@web @headless
Feature: End-to-End — Sample App login, logout, error, and variable flow
  # Full user journey on UITestingPlayground's SampleApp: happy path login,
  # error state, logout, and a variable-passing assertion chain.
  #
  # This is the kind of real-world E2E suite a senior QA would hand to the
  # framework. No page objects were written. No selectors were written.
  # No step definitions were written. Plain English ran the whole thing.
  #
  # Capability tier: PATTERN — all resolved locally, zero LLM cost.

  Background:
    Given User is on '[UITESTINGPLAYGROUND]/sampleapp'

  @smoke
  Scenario: Valid credentials log the user in
    When User enters 'admin' in the User Name field
    And User enters 'pwd' in the password field
    And User clicks the Log In button
    Then User should see "Welcome, admin!"
    And User should not see "Invalid username/password"
    And User should have url containing 'sampleapp'

  @smoke
  Scenario: Wrong password shows an error message
    When User enters 'admin' in the User Name field
    And User enters 'wrong' in the password field
    And User clicks the Log In button
    Then User should see "Invalid username/password"
    And User should not see "Welcome"

  @smoke
  Scenario: Logout returns to the login state
    When User enters 'admin' in the User Name field
    And User enters 'pwd' in the password field
    And User clicks the Log In button
    Then User should see "Welcome, admin!"
    When User clicks the Log Out button
    Then User should see "Log In"
    And User should not see "Welcome, admin!"

  @smoke
  Scenario: Empty username shows an error
    When User enters '' in the password field
    And User clicks the Log In button
    Then User should see "Invalid username/password"

  @smoke
  Scenario: Store welcome message text and assert it contains the username
    When User enters 'alice' in the User Name field
    And User enters 'pwd' in the password field
    And User clicks the Log In button
    Then User waits until 'Welcome, alice!' is visible
    And User stores the login status as `WELCOME_TEXT`
    And `WELCOME_TEXT` should contain 'alice'

  @smoke
  Scenario: Screenshot captured on successful login
    When User enters 'admin' in the User Name field
    And User enters 'pwd' in the password field
    And User clicks the Log In button
    Then User should see "Welcome, admin!"
    And User takes a screenshot 'uitap_sampleapp_logged_in'
