# ============================================================================
# LLM FALLBACK DEMO — shows Trigger 1: a step sentence that matches NO regex
# pattern, so the framework hands it to the model to interpret.
#
#   LOCAL PATH   → sentence matches a built-in pattern. Free, no model. ([A11Y])
#   LLM PATH     → sentence matches NOTHING in patterns.py, so step_resolver
#                  calls the model, which returns a JSON action. ([LLM])
#
# Requires a model (this is the whole point):
#   BDDFRAME_MODEL=openai/qwen2.5-7b-instruct-generic-cpu   # via Foundry Local
#   BDDFRAME_LLM_URL=http://localhost:<port>/v1
#   OPENAI_API_KEY=not-needed
#   (with BDDFRAME_MODEL unset, the [LLM] steps FAIL locally — by design.)
#
# Run it:   behave features/fallback-demo/llm_fallback.feature --no-capture
#
# The [LLM] steps below use verbs the regex layer doesn't know ("submits",
# "authenticates"), so normalize_subject can't map them and pattern_match
# returns None — which is exactly what routes them to the model.
# ============================================================================
@web @headless @llm_fallback
Feature: LLM Fallback Demonstration

  Scenario: A step the regex layer can't parse is interpreted by the model

    # [A11Y] navigate — matches the built-in "is on '...'" pattern, no model
    Given User is on "https://www.saucedemo.com"

    # [A11Y] "username" field — matched by input placeholder, no model
    When User enters [SAUCE_USERNAME] in the username field

    # [A11Y] "password" field — matched by input placeholder, no model
    And User enters [SAUCE_PASSWORD] in the password field

    # [LLM] "submits the login form" — no pattern has the verb "submit", so
    #       step_resolver hands it to the model, which should return e.g.
    #       {"type": "click", "locator": "Login"}
    When User submits the login form

    # [A11Y] plain DOM text assertion — confirms the model's action worked
    Then User should see "Products"
