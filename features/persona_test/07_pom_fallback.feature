@web @headless @pom_fallback
Feature: POM Fallback — element resolved via pom.yaml when accessibility returns 0 matches
  # Trigger: the step uses a human alias ("progress start trigger") that does NOT
  # match any accessible name, role, placeholder, or visible text in the DOM.
  # Playwright returns 0 matches → framework falls back to
  # features/persona_test/pageobjects/uitesting_pom.yaml → id: startButton.
  #
  # Watch for this line in the output:
  #   📋 POM: resolved 'progress start trigger' via pom.yaml
  #
  # Steps marked [A11Y] resolve via the accessibility tree with no POM lookup.
  # Steps marked [POM] are the ones that prove the fallback fired.
  #
  # Capability tier: PATTERN + POM — zero LLM cost.

  Scenario: Start a progress bar via POM-resolved button alias
    # [A11Y] navigate — accessibility lookup not needed
    Given User is on '[UITESTINGPLAYGROUND]/progressbar'

    # [A11Y] page text visible — DOM text assertion
    Then User should see "Progress Bar"

    # [POM] "progress start trigger" has no matching text/label/role in DOM.
    # id: startButton resolves from uitesting_pom.yaml.
    When User clicks the progress start trigger

    # [A11Y] Wait for some progress — text "%" will appear in the bar
    Then User waits until 'Stop' is visible

  Scenario: Rename a button using POM-aliased input and button
    # [A11Y] navigate
    Given User is on '[UITESTINGPLAYGROUND]/textinput'

    # [POM] "new button name input" → id: newButtonName (no accessible label)
    When User enters 'POMResolved' in the new button name input field

    # [POM] "updating button" → id: updatingButton (label is the button text
    #       but it's very long; alias is cleaner)
    And User clicks the updating button

    # [A11Y] the button text should now be "POMResolved"
    Then User should see "POMResolved"
