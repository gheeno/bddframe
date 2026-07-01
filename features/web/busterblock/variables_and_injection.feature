@web @headless @variables @injection @capability
Feature: Variables and Step Dependency Injection — capture values and chain them

  # Noodle has a per-scenario variable store. Values captured in one step
  # are available to all later steps in the same scenario — this is "step
  # dependency injection": a step's output is injected into subsequent steps
  # without any function-call wiring.
  #
  # Variable syntax:
  #   "literal"  → a fixed string you type in the step
  #   `name`     → a value captured during this run (set/store steps, scenario-scoped)
  #   [name]     → a .env / environments.yaml value (config or secret)
  #
  # Patterns demonstrated:
  #   sets `VAR` to 'value'                      — seed a literal into the store
  #   stores the X as `VAR`                      — capture element text
  #   grabs the X as `VAR`                       — alias for stores
  #   stores attribute 'attr' of X as `VAR`      — capture an element attribute
  #   `VAR` should contain / equal               — assert on a stored value
  #   `VAR` used in a later step URL or text     — variable substitution mid-step
  #
  # Run:  noodle run features/web/busterblock/variables_and_injection.feature

  Background:
    Given User is on "[BUSTERBLOCK]"
    When User enters [BB_USER] in the username field
    And User enters [BB_PASS] in the password field
    And User clicks the login button
    Then User waits until "VHS Catalog" is visible

  @smoke @set_var
  Scenario: Seed a literal value and assert it later
    # sets `VAR` to 'value' — write a constant into the store.
    # Useful to name a magic value so later assertions are readable.
    Given User sets `EXPECTED_TITLE` to 'VHS Catalog'
    Then User should see `EXPECTED_TITLE`
    And `EXPECTED_TITLE` should equal 'VHS Catalog'

  @smoke @store_text @injection
  Scenario: Capture element text — step dependency injection
    # Step 1 captures text from the page into `HEADING`.
    # Step 2 uses `HEADING` — the captured value is INJECTED into the assertion.
    # No function call, no parameter passing — the store is the channel.
    When User stores the "catalog heading" as `HEADING`
    Then `HEADING` should contain "VHS Catalog"

  @grab @injection
  Scenario: Grab a value from a table cell and use it in a search
    # Grab the title of the first row; inject it into the search field.
    # Proves the same value that was in the catalog also appears in search results.
    When User grabs the "Die Hard" text as `MOVIE_TITLE`
    And User enters `MOVIE_TITLE` in the search movies field
    Then User should see `MOVIE_TITLE`

  @store_attribute
  Scenario: Capture an element attribute value
    # stores attribute 'attr' of X as `VAR` — capture an HTML attribute
    # instead of visible text. Useful for href, data-*, value, aria-*, etc.
    When User stores attribute "aria-label" of "View cart" as `CART_LABEL`
    Then `CART_LABEL` should equal "View cart"

  @smoke @chained_vars
  Scenario: Variable chain — set, capture, compare
    # Classic "expected vs actual" pattern:
    #   1. Seed the expected value into `EXPECTED`.
    #   2. Navigate / interact.
    #   3. Capture the actual value into `ACTUAL`.
    #   4. Compare.
    Given User sets `EXPECTED` to 'VHS Catalog'
    When User navigates to "[BUSTERBLOCK]/catalog.html"
    And User waits until "VHS Catalog" is visible
    And User stores the "catalog heading" as `ACTUAL`
    Then `ACTUAL` should contain `EXPECTED`
