@rest
Feature: REST API — GET operations against restful-api.dev
  # Exercises: calls GET, run_command with curl, SCRIPT_OUTPUT variable assertions.
  #
  # Two resolution paths:
  #   calls GET 'URL'           → Playwright request context → asserts 2xx only
  #   run_command 'curl -s URL' → shell curl → SCRIPT_OUTPUT → body content assert
  #
  # The pre-seeded object list at /objects always includes "id" and "name" fields.
  # Objects 1-13 are permanent fixtures the server guarantees.
  #
  # Run it:
  #   bddframe run features/persona_test/11_rest_get.feature --no-capture
  #
  # No browser needed — but the @rest tag still opens one (Playwright request
  # context needs a page). Future: @api tag would skip the browser entirely.
  #
  # Capability tier: PATTERN (api_call) + PATTERN (run_command + assert_compare).

  @smoke
  Scenario: GET all objects returns 200 OK
    # Built-in api_call pattern — asserts 2xx, no body inspection.
    Given User navigates to '[RESTFULAPI]/objects'
    When User calls GET '[RESTFULAPI]/objects'
    Then User should see "Google Pixel 6 Pro"

  @smoke
  Scenario: GET all objects body contains expected shape
    # run_command bridges to shell curl so we can assert on the response body.
    When User runs the command 'curl -s "[RESTFULAPI]/objects"'
    Then `SCRIPT_OUTPUT` should contain 'id'
    And `SCRIPT_OUTPUT` should contain 'name'
    And `SCRIPT_OUTPUT` should contain 'data'

  @smoke
  Scenario: GET single object by ID returns 200 OK
    When User calls GET '[RESTFULAPI]/objects/1'
    Then User should see "Google Pixel 6 Pro"

  @smoke
  Scenario: GET single object body contains the object name
    When User runs the command 'curl -s "[RESTFULAPI]/objects/1"'
    Then `SCRIPT_OUTPUT` should contain 'Google Pixel 6 Pro'
    And `SCRIPT_OUTPUT` should contain 'id'

  @smoke
  Scenario: GET multiple objects by query param IDs
    When User runs the command 'curl -s "[RESTFULAPI]/objects?id=3&id=5&id=10"'
    Then `SCRIPT_OUTPUT` should contain 'id'
    And `SCRIPT_OUTPUT` should contain 'name'

  @smoke
  Scenario: GET object and store response for downstream assertion
    When User runs the command 'curl -s "[RESTFULAPI]/objects/1"' and storing the output in `OBJECT_1`
    Then `OBJECT_1` should contain 'Google Pixel 6 Pro'

  @smoke
  Scenario: GET non-existent object returns an error shape (not 2xx, uses curl)
    # api_call would fail the step on 404. curl lets us assert on the error body.
    When User runs the command 'curl -s "[RESTFULAPI]/objects/nonexistent-id-99999"'
    Then `SCRIPT_OUTPUT` should contain 'error'

  @smoke
  Scenario: Browser renders the JSON list (navigating to the API endpoint)
    # GET via browser navigation — the raw JSON renders in the browser.
    # Confirms the endpoint is reachable and contains expected device names.
    Given User navigates to '[RESTFULAPI]/objects/3'
    Then User should see "name"
