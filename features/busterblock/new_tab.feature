@web
Feature: New Tab Interactions

  Background:
    Given User is on "[BUSTERBLOCK]"
    When User enters [BB_USER] in the username field
    And User enters [BB_PASS] in the password field
    And User clicks the login button
    Then User should see "VHS Catalog"

  @smoke
  Scenario: Preview button opens movie detail in a new tab
    When User clicks "Preview"
    Then a new tab should open
    And User should see "PLAY" in the new tab
    And User should see "Director" in the new tab
    And User should see "Close Tab" in the new tab

  @smoke
  Scenario: Framework can switch back to original tab
    When User clicks "Preview"
    Then a new tab should open
    And User should see "PLAY" in the new tab
    When User switches to the previous tab
    Then User should see "VHS Catalog"

  @smoke
  Scenario: Receipt tab opens after checkout and can be closed
    When User clicks "Add to Cart"
    And User clicks "Cart"
    And User clicks "Checkout"
    Then a new tab should open
    And User should see "Receipt" in the new tab
    And User should see "Confirmed" in the new tab
    When User clicks "Close Tab" in the new tab
    And User switches to the previous tab
    Then User should see "VHS Catalog"
