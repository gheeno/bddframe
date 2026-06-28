@web @headless
Feature: Text Input — fill, clear, type, press key, and value assertions
  # Exercises: enters X in the Y field, fills in X with Y, clears the X field,
  # types 'X' (raw keyboard), presses Enter, the X field should contain Y.
  #
  # UITestingPlayground /textinput page: type a name into an input and click
  # the button — the button label changes to the typed text.
  #
  # Capability tier: PATTERN — all resolved locally, zero LLM cost.

  @smoke
  Scenario: Enter text using enters X in the Y field phrasing
    Given User is on '[UITESTINGPLAYGROUND]/sampleapp'
    When User enters 'test_user' in the User Name field
    And User enters 'wrong_pass' in the password field
    And User clicks the Log In button
    Then User should see "Invalid username/password"

  @smoke
  Scenario: Enter text using fills-in phrasing
    Given User is on '[UITESTINGPLAYGROUND]/sampleapp'
    When User fills in the User Name field with 'admin'
    And User fills in the password field with 'pwd'
    And User clicks the Log In button
    Then User should see "Welcome, admin!"

  @smoke
  Scenario: Rename button via text input (TextInput page)
    Given User is on '[UITESTINGPLAYGROUND]/textinput'
    When User enters 'MyCustomName' in the new button name input field
    And User clicks the updating button
    Then User should see "MyCustomName"

  @smoke
  Scenario: Clear a field before re-entering a value
    Given User is on '[UITESTINGPLAYGROUND]/sampleapp'
    When User enters 'wrong_name' in the User Name field
    And User clears the User Name field
    And User enters 'admin' in the User Name field
    And User enters 'pwd' in the password field
    And User clicks the Log In button
    Then User should see "Welcome, admin!"

  @smoke
  Scenario: Submit login form by pressing Enter key
    Given User is on '[UITESTINGPLAYGROUND]/sampleapp'
    When User enters 'admin' in the User Name field
    And User enters 'pwd' in the password field
    And User presses 'Enter'
    Then User should see "Welcome, admin!"

  @smoke
  Scenario: Types raw keyboard text without specifying a locator
    # 'types X' (no field locator) sends raw keyboard input to focused element.
    Given User is on '[UITESTINGPLAYGROUND]/sampleapp'
    When User clicks the User Name field
    And User types 'admin'
    And User presses 'Tab'
    And User types 'pwd'
    And User presses 'Enter'
    Then User should see "Welcome, admin!"
