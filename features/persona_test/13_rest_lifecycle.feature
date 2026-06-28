@rest @api
Feature: REST API — Full CRUD lifecycle with variable chaining
  # Creates an object, reads it back, updates it, partially patches it,
  # then deletes it. Each step uses the id extracted from the POST response —
  # the proper pattern for mutable object testing on restful-api.dev.
  #
  # Variable chain:
  #   `OBJ_ID`     → id of the created object (extracted via rest_extract_json)
  #   `CREATE_RESP` → POST response body
  #   `GET_RESP`    → GET single-object response body
  #   `PUT_RESP`    → PUT response body
  #   `PATCH_RESP`  → PATCH response body
  #   `DEL_RESP`    → DELETE response body
  #
  # Run it:
  #   bddframe run features/persona_test/13_rest_lifecycle.feature
  #
  # Note: restful-api.dev has a 50-request/day limit on the free tier.
  # Run this suite in isolation, not after 11 and 12 in the same session.

  Background:
    Given sets `REST_BASE_URL` to '[RESTFULAPI]'

  @smoke
  Scenario: Create an object and verify response shape
    When performs a POST call at '/objects' with body '{"name": "BDDFrame CRUD Object", "data": {"tester": "persona_test", "year": 2026, "env": "ci"}}' storing response in `CREATE_RESP`
    Then the response status should be 200
    And the response body should contain:
      | Key       | Value                |
      | name      | BDDFrame CRUD Object |
      | id        |                      |
      | createdAt |                      |

  @smoke
  Scenario: Read all objects — list returns id and name fields
    When performs a GET call at '/objects' storing response in `LIST_RESP`
    Then the response status should be 200
    And `LIST_RESP` should contain 'id'
    And `LIST_RESP` should contain 'name'

  @smoke
  Scenario: Read a known pre-seeded object
    When performs a GET call at '/objects/1' storing response in `GET_RESP`
    Then the response status should be 200
    And the response body should contain:
      | Key  | Value              |
      | id   | 1                  |
      | name | Google Pixel 6 Pro |

  @smoke
  Scenario: Full update via PUT on a self-created object
    When performs a POST call at '/objects' with body '{"name": "PUT Target"}' storing response in `CREATE_RESP`
    And extracts 'id' from response storing in `OBJ_ID`
    When performs a PUT call at '/objects/`OBJ_ID`' with body '{"name": "BDDFrame PUT Updated", "data": {"status": "updated", "year": 2026}}' storing response in `PUT_RESP`
    Then the response status should be 200
    And `PUT_RESP` should contain 'BDDFrame PUT Updated'
    And `PUT_RESP` should contain 'updatedAt'

  @smoke
  Scenario: Partial update via PATCH on a self-created object
    When performs a POST call at '/objects' with body '{"name": "PATCH Target"}' storing response in `CREATE_RESP`
    And extracts 'id' from response storing in `OBJ_ID`
    When performs a PATCH call at '/objects/`OBJ_ID`' with body '{"name": "BDDFrame PATCH Updated"}' storing response in `PATCH_RESP`
    Then the response status should be 200
    And `PATCH_RESP` should contain 'BDDFrame PATCH Updated'
    And `PATCH_RESP` should contain 'updatedAt'

  @smoke
  Scenario: Delete a self-created object and verify deletion response
    When performs a POST call at '/objects' with body '{"name": "DELETE Target"}' storing response in `CREATE_RESP`
    And extracts 'id' from response storing in `OBJ_ID`
    When performs a DELETE call at '/objects/`OBJ_ID`' storing response in `DEL_RESP`
    Then the response status should be 200
    And `DEL_RESP` should contain 'deleted'

  @smoke
  Scenario: Full CRUD in a single scenario — create, read, update, patch, delete
    # CREATE
    When performs a POST call at '/objects' with body '{"name": "Lifecycle Test Object", "data": {"phase": "create"}}' storing response in `NEW_OBJ`
    Then the response status should be 200
    And `NEW_OBJ` should contain 'Lifecycle Test Object'
    And `NEW_OBJ` should contain 'createdAt'
    And extracts 'id' from response storing in `LIFE_ID`

    # READ single object (pre-seeded, guaranteed to exist)
    When performs a GET call at '/objects/1'
    Then the response status should be 200
    And the response body should contain 'Google Pixel 6 Pro'

    # UPDATE via PUT on the created object
    When performs a PUT call at '/objects/`LIFE_ID`' with body '{"name": "Lifecycle Updated", "data": {"phase": "update"}}' storing response in `UPD_OBJ`
    Then the response status should be 200
    And `UPD_OBJ` should contain 'Lifecycle Updated'
    And `UPD_OBJ` should contain 'updatedAt'

    # PATCH on the same object
    When performs a PATCH call at '/objects/`LIFE_ID`' with body '{"data": {"phase": "patch"}}' storing response in `PATCHED_OBJ`
    Then the response status should be 200
    And `PATCHED_OBJ` should contain 'updatedAt'

    # DELETE
    When performs a DELETE call at '/objects/`LIFE_ID`' storing response in `DELETED_OBJ`
    Then the response status should be 200
    And `DELETED_OBJ` should contain 'deleted'
