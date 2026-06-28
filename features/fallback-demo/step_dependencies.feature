# ============================================================================
# STEP DEPENDENCIES DEMO (Phase 12) — a value made in one step, used in another.
#
#   [VAR] is the shared store (behave's `context`, scenario-scoped). It is the
#   BDDFrame equivalent of a Spring scenario-scoped bean:
#     - store/set  → writes  context._vars[VAR]
#     - [VAR]      → substituted to its value BEFORE the next step runs ("DI")
#
#   No expression engine: the framework does NOT compute maths. The app under
#   test computes; the test STORES the app's output and COMPARES it.
#
# Run it:   behave features/fallback-demo/step_dependencies.feature --no-capture
# ============================================================================
@web @headless @step_dependencies
Feature: Step Dependencies and Shared State

  # Fully self-contained: navigates once, then pure store/compare steps.
  Scenario: Compare values carried between steps
    Given User is on "https://example.com"

    # seed two literals into the shared store
    When User sets [PRICE] to "42"
    And User sets [BUDGET] to "50"

    # later steps reference them by [VAR] — substituted before comparison
    Then [PRICE] should be less than [BUDGET]
    And [PRICE] should equal "42"
    And [BUDGET] should be greater than "40"
    And [BUDGET] should be greater than or equal to "50"
    And [PRICE] should not equal [BUDGET]

  # The calculator example from the request. Needs a calculator under test:
  # point BASE_URL / the navigate step at one, and adjust the field labels.
  # Shown here as the canonical "store the app's result, then assert" shape.
  @manual
  Scenario: Assert a computed result against an input (calculator)
    Given User is on "https://example.com"          # ← replace with a calculator
    When User enters "5" in the "first number" field
    And User enters "3" in the "second number" field
    And User clicks the equals button

    # store the APP's result (store_text reads the displayed value) ...
    And User stores the result as [Y]

    # ... then assert on it, referencing the original input
    Then [Y] should be greater than "5"
    And [Y] should equal "8"
