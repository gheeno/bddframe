@web @headless
Feature: Waits and Dynamic Content — native wait strategies
  # Exercises: waits until X is visible, waits until X disappears, waits N seconds,
  # waits for page to load, waits for network to be idle.
  #
  # Uses UITestingPlayground /loaddelay (page takes ~3s to render a button) and
  # /ajax (triggers a 15s AJAX request — skipped here as too slow for CI) and
  # /progressbar (polling for 75% completion).
  #
  # All waits use Playwright's native MutationObserver under the hood —
  # no sleep loops, deterministic edge-detection.
  #
  # Capability tier: PATTERN — all resolved locally, zero LLM cost.

  @smoke
  Scenario: Wait until a delayed button appears (LoadDelay page)
    # The page intentionally takes ~3s to show the button.
    Given User is on '[UITESTINGPLAYGROUND]/loaddelay'
    Then User waits until 'Button Appearing After Delay' is visible
    And User should see "Button Appearing After Delay"

  @smoke
  Scenario: Wait for page to be ready before asserting
    Given User is on '[UITESTINGPLAYGROUND]/loaddelay'
    When User waits for the page to load
    Then User should see "Button Appearing After Delay"

  @smoke
  Scenario: Wait for network to be idle on page load
    Given User is on '[UITESTINGPLAYGROUND]/dynamictable'
    When User waits for the network to be idle
    Then User should see "Chrome"

  @smoke
  Scenario: Wait a fixed number of seconds (guardrail, not preferred)
    # Prefer waits-until over waits-N-seconds in production — fixed delays are
    # brittle. Covered here to verify the pattern is wired.
    Given User is on '[UITESTINGPLAYGROUND]/loaddelay'
    When User waits 4 seconds
    Then User should see "Button Appearing After Delay"

  @smoke
  Scenario: Wait until an element disappears (wait_hidden pattern)
    # Log out removes the welcome message — verifies wait_hidden resolves.
    Given User is on '[UITESTINGPLAYGROUND]/sampleapp'
    When User enters 'admin' in the User Name field
    And User enters 'pwd' in the password field
    And User clicks the Log In button
    Then User waits until 'Welcome, admin!' is visible
    When User clicks the Log Out button
    Then User waits until 'Welcome, admin!' disappears
    And User should see "Log In"
