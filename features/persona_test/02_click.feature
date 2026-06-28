@web @headless
Feature: Click Interactions — button clicks, quoted text, link variants
  # Exercises: clicks 'X', clicks the X button, clicks the X link,
  # presses the X button, double-click.
  #
  # Dynamic ID page proves the framework resolves by visible text — not DOM id —
  # so click assertions survive every page refresh.
  #
  # Capability tier: PATTERN — all resolved locally, zero LLM cost.

  @smoke
  Scenario: Click a button with dynamic DOM id via visible text
    # The button id is generated fresh each load — only text is stable.
    Given User is on '[UITESTINGPLAYGROUND]/dynamicid'
    When User clicks 'Button with Dynamic ID'
    Then User should see "Button with Dynamic ID"

  @smoke
  Scenario: Click using the X button phrasing
    Given User is on '[UITESTINGPLAYGROUND]/dynamicid'
    When User clicks the Button with Dynamic ID button
    Then User should see "Button with Dynamic ID"

  @smoke
  Scenario: Click the Bad button (click-trap page)
    # This page traps automation that navigates onclick instead of a real click.
    # BDDFrame uses Playwright's click() which sends real pointer events.
    Given User is on '[UITESTINGPLAYGROUND]/click'
    When User clicks 'Bad button'
    Then User should see "Bad button"

  @smoke
  Scenario: Login flow using clicks the X button phrasing
    Given User is on '[UITESTINGPLAYGROUND]/sampleapp'
    When User enters 'admin' in the User Name field
    And User enters 'pwd' in the password field
    And User clicks the Log In button
    Then User should see "Welcome, admin!"

  @smoke
  Scenario: Logout after login using presses phrasing
    Given User is on '[UITESTINGPLAYGROUND]/sampleapp'
    When User enters 'admin' in the User Name field
    And User enters 'pwd' in the password field
    And User presses the Log In button
    Then User should see "Welcome, admin!"
    When User clicks the Log Out button
    Then User should see "Log In"

  @smoke
  Scenario: Double-click on a mouseover link (double-click action)
    Given User is on '[UITESTINGPLAYGROUND]/mouseover'
    When User double-clicks on the Click me link
    Then User should see "2"
