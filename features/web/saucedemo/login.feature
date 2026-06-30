@headless
Feature: Sauce Demo Login

  @web @smoke
  Scenario: Standard user logs in successfully

    Given User is on "[SAUCEDEMO]"
    When User enters [SAUCE_USERNAME] in the username field
    And User enters [SAUCE_PASSWORD] in the password field
    And User clicks the login button
    Then User should see "Products"

  @web @smoke
  Scenario: Locked out user sees an error message

    Given User is on "[SAUCEDEMO]"
    When User enters "locked_out_user" in the username field
    And User enters "secret_sauce" in the password field
    And User clicks the login button
    Then User should see "Epic sadface: Sorry, this user has been locked out."

  @web
  Scenario: Empty credentials shows a validation error

    Given User is on "[SAUCEDEMO]"
    When User clicks the login button
    Then User should see "Username is required"
