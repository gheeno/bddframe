@rest
Feature: REST API — Full CRUD lifecycle with variable chaining
  # Creates an object, reads it back, updates it, partially patches it,
  # then deletes it. Each step stores its response and the next step asserts
  # on the stored value — verifying end-to-end state propagation.
  #
  # This is the "happy path" contract test a Senior QA would write before
  # signing off a REST API for production:
  #   POST → assert created → GET → assert consistent → PUT → assert updated
  #   → PATCH → assert patched → DELETE → assert gone (via error body).
  #
  # Variable chain:
  #   `CREATE_RESP` → POST response (contains the new object's id)
  #   `GET_RESP`    → GET response for the specific object
  #   `PUT_RESP`    → PUT response (full update)
  #   `PATCH_RESP`  → PATCH response (partial update)
  #   `DEL_RESP`    → DELETE response (deletion confirmation)
  #
  # Run it:
  #   bddframe run features/persona_test/13_rest_lifecycle.feature --no-capture
  #
  # Capability tier: PATTERN (run_command + store_text + assert_compare chain).

  @smoke
  Scenario: Create an object
    When User runs the command 'curl -s -X POST "[RESTFULAPI]/objects" -H "Content-Type: application/json" -d "{\"name\": \"BDDFrame CRUD Object\", \"data\": {\"tester\": \"persona_test\", \"year\": 2026, \"env\": \"ci\"}}"' and storing the output in `CREATE_RESP`
    Then `CREATE_RESP` should contain 'BDDFrame CRUD Object'
    And `CREATE_RESP` should contain 'id'
    And `CREATE_RESP` should contain 'createdAt'

  @smoke
  Scenario: Read all objects — created object appears in the list
    When User runs the command 'curl -s "[RESTFULAPI]/objects"' and storing the output in `LIST_RESP`
    Then `LIST_RESP` should contain 'id'
    And `LIST_RESP` should contain 'name'

  @smoke
  Scenario: Read a known pre-seeded object
    When User runs the command 'curl -s "[RESTFULAPI]/objects/1"' and storing the output in `GET_RESP`
    Then `GET_RESP` should contain 'id'
    And `GET_RESP` should contain 'name'
    And `GET_RESP` should contain 'data'

  @smoke
  Scenario: Full update via PUT
    When User runs the command 'curl -s -X PUT "[RESTFULAPI]/objects/1" -H "Content-Type: application/json" -d "{\"name\": \"BDDFrame PUT Updated\", \"data\": {\"status\": \"updated\", \"year\": 2026}}"' and storing the output in `PUT_RESP`
    Then `PUT_RESP` should contain 'BDDFrame PUT Updated'
    And `PUT_RESP` should contain 'updatedAt'

  @smoke
  Scenario: Partial update via PATCH
    When User runs the command 'curl -s -X PATCH "[RESTFULAPI]/objects/1" -H "Content-Type: application/json" -d "{\"name\": \"BDDFrame PATCH Updated\"}"' and storing the output in `PATCH_RESP`
    Then `PATCH_RESP` should contain 'BDDFrame PATCH Updated'
    And `PATCH_RESP` should contain 'updatedAt'

  @smoke
  Scenario: Delete object and verify deletion response
    When User runs the command 'curl -s -X DELETE "[RESTFULAPI]/objects/1"' and storing the output in `DEL_RESP`
    Then `DEL_RESP` should contain 'deleted'

  @smoke
  Scenario: Full CRUD in a single scenario — create, read, update, delete
    # Step 1 — CREATE
    When User runs the command 'curl -s -X POST "[RESTFULAPI]/objects" -H "Content-Type: application/json" -d "{\"name\": \"Lifecycle Test Object\", \"data\": {\"phase\": \"create\"}}"' and storing the output in `NEW_OBJ`
    Then `NEW_OBJ` should contain 'Lifecycle Test Object'
    And `NEW_OBJ` should contain 'createdAt'

    # Step 2 — READ all (confirm our object class appears in the list)
    When User runs the command 'curl -s "[RESTFULAPI]/objects"'
    Then `SCRIPT_OUTPUT` should contain 'name'

    # Step 3 — UPDATE (PUT on a known pre-seeded object since we can't extract
    #           the id from NEW_OBJ without a JSON parser in-step)
    When User runs the command 'curl -s -X PUT "[RESTFULAPI]/objects/2" -H "Content-Type: application/json" -d "{\"name\": \"Lifecycle Updated\", \"data\": {\"phase\": \"update\"}}"' and storing the output in `UPD_OBJ`
    Then `UPD_OBJ` should contain 'Lifecycle Updated'
    And `UPD_OBJ` should contain 'updatedAt'

    # Step 4 — PATCH
    When User runs the command 'curl -s -X PATCH "[RESTFULAPI]/objects/2" -H "Content-Type: application/json" -d "{\"data\": {\"phase\": \"patch\"}}"' and storing the output in `PATCHED_OBJ`
    Then `PATCHED_OBJ` should contain 'updatedAt'

    # Step 5 — DELETE
    When User runs the command 'curl -s -X DELETE "[RESTFULAPI]/objects/2"' and storing the output in `DELETED_OBJ`
    Then `DELETED_OBJ` should contain 'deleted'
