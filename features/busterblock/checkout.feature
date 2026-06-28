@web
Feature: Cart and Checkout — Receipt in New Tab

  Background:
    Given User is on "[BUSTERBLOCK]"
    When User enters [BB_USER] in the username field
    And User enters [BB_PASS] in the password field
    And User clicks the login button
    Then User should see "VHS Catalog"

  @smoke
  Scenario: User completes a rental from catalog to receipt
    When User clicks "Add to Cart"
    Then User should see "1"

    When User clicks "Cart"
    Then User should see "Your Cart"
    And User should see "Checkout"

    When User clicks "Checkout"
    Then User should see "Order placed"

  @smoke
  Scenario: Receipt opens in a new tab after checkout
    When User clicks "Add to Cart"
    And User clicks "Cart"
    And User clicks "Checkout"
    Then a new tab should open
    And User should see "BusterBlock" in the new tab
    And User should see "Total" in the new tab
    And User should see "Thank you for renting" in the new tab

  @smoke
  Scenario: Cart shows subtotal, tax, and total
    When User clicks "Add to Cart"
    And User clicks "Cart"
    Then User should see "Subtotal"
    And User should see "HST"
    And User should see "Total"

  @smoke
  Scenario: User can remove an item from cart
    When User clicks "Add to Cart"
    And User clicks "Cart"
    Then User should see "Your Cart"
    When User clicks "Remove"
    Then User should see "Your cart is empty"
