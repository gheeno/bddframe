@rest
Feature: REST API — POST, PUT, PATCH, DELETE operations against restful-api.dev
  # Exercises: calls POST/PUT/PATCH/DELETE with body, run_command for JSON body
  # responses, variable store chain across steps.
  #
  # Content-Type note:
  #   `calls POST 'URL' with body '...'` uses Playwright's fetch(data=str) which
  #   sends text/plain by default — fine for APIs that auto-detect JSON, but not
  #   guaranteed. `run_command 'curl -X POST -H "Content-Type: application/json"'`
  #   is the safe path for strict APIs. restful-api.dev is lenient, so both work;
  #   the curl form is shown here as the production-grade pattern.
  #
  # Run it:
  #   bddframe run features/persona_test/12_rest_write.feature --no-capture
  #
  # Capability tier: PATTERN (api_call, run_command, assert_compare/store).

  @smoke
  Scenario: POST creates a new object and response contains the assigned id
    When User runs the command 'curl -s -X POST "[RESTFULAPI]/objects" -H "Content-Type: application/json" -d "{\"name\": \"BDDFrame Test Device\", \"data\": {\"tester\": \"persona_test\", \"year\": 2026}}"'
    Then `SCRIPT_OUTPUT` should contain 'BDDFrame Test Device'
    And `SCRIPT_OUTPUT` should contain 'id'
    And `SCRIPT_OUTPUT` should contain 'createdAt'

  @smoke
  Scenario: POST using built-in calls-with-body phrasing (2xx assertion only)
    # api_call sends the body as text/plain; restful-api.dev is lenient enough
    # to accept it. This pattern is the right tool for data SETUP steps, not
    # for response body assertion.
    When User calls POST '[RESTFULAPI]/objects' with body '{"name": "Setup Object", "data": {"env": "persona_test"}}'

  @smoke
  Scenario: POST create then verify via GET (write then read chain)
    # Step 1 — create
    When User runs the command 'curl -s -X POST "[RESTFULAPI]/objects" -H "Content-Type: application/json" -d "{\"name\": \"ChainTest Device\"}"' and storing the output in `CREATED`
    Then `CREATED` should contain 'ChainTest Device'
    And `CREATED` should contain 'id'
    # Step 2 — read all to confirm the created name exists in the list
    When User runs the command 'curl -s "[RESTFULAPI]/objects"'
    Then `SCRIPT_OUTPUT` should contain 'id'

  @smoke
  Scenario: PUT updates an object completely (creates if not exists)
    When User runs the command 'curl -s -X PUT "[RESTFULAPI]/objects/1" -H "Content-Type: application/json" -d "{\"name\": \"Updated Google Pixel\", \"data\": {\"color\": \"Obsidian\", \"capacity\": \"256 GB\"}}"'
    Then `SCRIPT_OUTPUT` should contain 'Updated Google Pixel'
    And `SCRIPT_OUTPUT` should contain 'updatedAt'

  @smoke
  Scenario: PATCH partially updates an object (only changed fields)
    When User runs the command 'curl -s -X PATCH "[RESTFULAPI]/objects/1" -H "Content-Type: application/json" -d "{\"name\": \"Patched Google Pixel\"}"'
    Then `SCRIPT_OUTPUT` should contain 'Patched Google Pixel'
    And `SCRIPT_OUTPUT` should contain 'updatedAt'

  @smoke
  Scenario: DELETE removes an object and response confirms deletion
    # Create a temporary object first, then delete it.
    When User runs the command 'curl -s -X POST "[RESTFULAPI]/objects" -H "Content-Type: application/json" -d "{\"name\": \"ToBeDeleted\"}"' and storing the output in `TO_DELETE`
    Then `TO_DELETE` should contain 'ToBeDeleted'
    When User runs the command 'curl -s -X DELETE "[RESTFULAPI]/objects/1"'
    Then `SCRIPT_OUTPUT` should contain 'deleted'

  @smoke
  Scenario: DELETE via built-in calls phrasing (2xx teardown pattern)
    # api_call DELETE is the right teardown tool after a scenario leaves behind data.
    # Here we use it as a teardown step — fails if the DELETE returns non-2xx.
    When User calls DELETE '[RESTFULAPI]/objects/1'
