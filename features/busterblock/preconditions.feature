@web
Feature: Preconditions — seed BusterBlock data before the UI test
  # Like a JDBC @Before/@After in Java: instead of clicking the UI into the state
  # you need, you seed it directly, run the test, then clean up. Here the "database"
  # is BusterBlock's in-memory store, reached over /api/test/* endpoints.
  #
  # The @precondition:NAME tag on a scenario looks up NAME in preconditions.yaml
  # (same folder). Its `setup:` HTTP calls run before the scenario; its `teardown:`
  # calls run after — even if the scenario fails. See docs/preconditions-plan.md.

  Background:
    Given User is on "[BUSTERBLOCK]"
    When User enters [BB_USER] in the username field
    And User enters [BB_PASS] in the password field
    And User clicks the login button
    And User waits until "VHS Catalog" appears
    Then User should see "VHS Catalog"

  @smoke @precondition:jaws_out_of_stock
  Scenario: A movie seeded out of stock shows "Out" in the catalog
    # Precondition forced Jaws (id 1) to stock 0 before this ran — no UI did that.
    Then the cell in row "Jaws" column "Stock" should be "Out"

  @smoke @precondition:cart_preseeded
  Scenario: A pre-seeded cart shows its item without ever clicking Add to Cart
    # Precondition put Star Wars in reel_ryan's cart server-side; we only navigate.
    When User clicks "View cart"
    And User waits until "Your Cart" appears
    Then User should see "Your Cart"
    And User should see "Star Wars"
