@web @headless
Feature: Scroll and Hover — scrolling to elements, hover-triggered interactions
  # Exercises: scrolls down, scrolls up, scrolls to 'X', hovers over X.
  #
  # UITestingPlayground /scrollbars has a "Hiding Button" below the fold that
  # requires scrolling to become clickable. /mouseover has a link that responds
  # to hover (mouseover event) and tracks double-click count.
  #
  # Capability tier: PATTERN — all resolved locally, zero LLM cost.

  @smoke
  Scenario: Scroll down to bring a button into view
    Given User is on '[UITESTINGPLAYGROUND]/scrollbars'
    When User scrolls down
    Then User should see "Hiding Button"

  @smoke
  Scenario: Scroll to a named element (scroll_to pattern)
    Given User is on '[UITESTINGPLAYGROUND]/scrollbars'
    When User scrolls to 'Hiding Button'
    Then User should see "Hiding Button"

  @smoke
  Scenario: Scroll down then click a revealed button
    Given User is on '[UITESTINGPLAYGROUND]/scrollbars'
    When User scrolls to 'Hiding Button'
    And User clicks 'Hiding Button'
    Then User should see "Hiding Button"

  @smoke
  Scenario: Scroll down then back up
    Given User is on '[UITESTINGPLAYGROUND]/scrollbars'
    When User scrolls down
    Then User should see "Hiding Button"
    When User scrolls up
    Then User should see "Scrollbars"

  @smoke
  Scenario: Hover over a link to trigger mouseover event
    # The mouseover page responds to pointer-enter events on "Click me" links.
    Given User is on '[UITESTINGPLAYGROUND]/mouseover'
    When User hovers over the Click me link
    Then User should see "Click me"
