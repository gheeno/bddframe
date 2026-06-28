@web
Feature: Hooks demo — cross-cutting behaviour via custom hooks
  # Hooks defined in features/steps/custom_hooks.py fire for every scenario
  # in the suite. The .feature itself needs no changes — hooks are transparent.
  #
  # before_scenario:  assigns context.session_id and starts a timer
  # after_scenario:   logs elapsed time and session ID for every scenario
  # @audit tag:       after_scenario also logs a named audit line

  Background:
    Given User is on "[BUSTERBLOCK]"
    When User enters [BB_USER] in the username field
    And User enters [BB_PASS] in the password field
    And User clicks the login button
    And User waits until "VHS Catalog" appears

  @smoke
  Scenario: Login succeeds and hook records session timing
    # The before_scenario hook already ran — context.session_id is set.
    # The after_scenario hook will log [session_id] name — PASSED (Xs) on exit.
    Then User should see "VHS Catalog"

  @smoke @audit
  Scenario: Catalog is visible and the run is audit-logged
    # @audit causes the after_scenario hook to emit an extra AUDIT log line
    # alongside the normal timing log. No step change needed.
    Then User should see "VHS Catalog"
    And User should see "Jaws"
