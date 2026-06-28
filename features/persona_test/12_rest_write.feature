@rest @api
Feature: REST API — POST, PUT, PATCH, DELETE operations against restful-api.dev
  # Exercises: write operations using the proper HTTP client (no curl).
  # Content-Type: application/json is sent automatically by rest_client.
  #
  # Note: objects 1–13 are reserved and cannot be mutated. Each write scenario
  # creates its own object via POST first, then uses the extracted id.
  #
  # Run it:
  #   bddframe run features/persona_test/12_rest_write.feature --no-capture

  Background:
    Given sets `REST_BASE_URL` to '[RESTFULAPI]'

  @smoke
  Scenario: POST creates a new object and response contains the assigned id
    When performs a POST call at '/objects' with body '{"name": "BDDFrame Test Device", "data": {"tester": "persona_test", "year": 2026}}'
    Then the response status should be 200
    And the response body should contain:
      | Key       | Value                |
      | name      | BDDFrame Test Device |
      | id        |                      |
      | createdAt |                      |

  @smoke
  Scenario: POST create then verify response body via stored variable
    When performs a POST call at '/objects' with body '{"name": "ChainTest Device"}' storing response in `CREATED`
    Then `CREATED` should contain 'ChainTest Device'
    And `CREATED` should contain 'id'

  @smoke
  Scenario: PUT fully updates a self-created object
    When performs a POST call at '/objects' with body '{"name": "MutableDevice"}'
    And extracts 'id' from response storing in `MUT_ID`
    When performs a PUT call at '/objects/`MUT_ID`' with body '{"name": "Updated MutableDevice", "data": {"color": "Obsidian"}}'
    Then the response status should be 200
    And the response body should contain 'Updated MutableDevice'
    And the response body should contain 'updatedAt'

  @smoke
  Scenario: PATCH partially updates a self-created object
    When performs a POST call at '/objects' with body '{"name": "PatchTarget"}'
    And extracts 'id' from response storing in `PATCH_ID`
    When performs a PATCH call at '/objects/`PATCH_ID`' with body '{"name": "Patched Target"}'
    Then the response status should be 200
    And the response body should contain 'Patched Target'
    And the response body should contain 'updatedAt'

  @smoke
  Scenario: DELETE removes a self-created object
    When performs a POST call at '/objects' with body '{"name": "ToBeDeleted"}'
    And extracts 'id' from response storing in `DEL_ID`
    When performs a DELETE call at '/objects/`DEL_ID`'
    Then the response status should be 200
    And the response body should contain 'deleted'

  @smoke
  Scenario Outline: POST returns 200 and body contains the submitted name
    When performs a POST call at '/objects' with body '{"name": "<name>"}'
    Then the response status should be 200
    And the response body should contain '<name>'
    And the response body should contain 'id'

    Examples:
      | name            |
      | BDDFrame Alpha  |
      | BDDFrame Beta   |
