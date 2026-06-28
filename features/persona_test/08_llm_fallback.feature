# ============================================================================
# LLM FALLBACK — Trigger 1: a step sentence with a verb the regex layer has
# never seen. The step resolver finds no matching pattern and hands the
# sentence to the LLM, which returns a JSON action the orchestrator executes.
#
#   PATTERN PATH  → verb matched by built-in regex (no model). [A11Y]
#   LLM PATH      → verb unknown to the regex layer → model interprets. [LLM]
#
# Requires a model configured:
#   BDDFRAME_MODEL=ollama/llama3
#   BDDFRAME_LLM_URL=http://localhost:11434
#   # or any LiteLLM-compatible endpoint
#
# Without BDDFRAME_MODEL set the [LLM] steps FAIL by design — which is the
# correct local-deterministic behaviour. Run with the model configured to
# see the fallback in action:
#   bddframe run features/persona_test/08_llm_fallback.feature --no-capture
#
# What verb triggers the LLM:
#   "authenticates" — not in the _FIRST_TO_THIRD map and matches no PATTERNS
#                      entry → step_resolver returns None → model call.
#   "confirm the outcome" — same reason.
# ============================================================================
@web @headless @llm_fallback
Feature: LLM Fallback — unmatched verb hands the step to the model

  Scenario: Authenticate using a verb the regex layer cannot parse

    # [A11Y] navigate — built-in 'navigates to' pattern, no model
    Given User navigates to '[UITESTINGPLAYGROUND]/sampleapp'

    # [A11Y] fills in — built-in 'fills in X with Y' pattern, no model
    When User fills in the User Name field with 'admin'
    And User fills in the password field with 'pwd'

    # [LLM] "authenticates on the sample application" — verb "authenticates"
    #       appears in no pattern → resolver passes to model, which should
    #       return {"type": "click", "locator": "Log In"} or equivalent.
    When User authenticates on the sample application  # llm-ok

    # [A11Y] plain DOM text assertion — no model
    Then User should see "Welcome, admin!"

  Scenario: Confirm the login outcome with an unrecognised phrasing

    # [A11Y] standard login flow
    Given User navigates to '[UITESTINGPLAYGROUND]/sampleapp'
    When User enters 'admin' in the User Name field
    And User enters 'pwd' in the password field
    And User clicks the Log In button
    Then User should see "Welcome, admin!"

    # [LLM] "confirm the outcome shows a welcome message" — verb "confirm" not
    #       in any pattern → model interprets as a visual/semantic assertion
    Then User confirms the outcome shows a welcome message  # llm-ok
