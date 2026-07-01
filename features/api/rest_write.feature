@api @rest @rest_write @capability
Feature: REST Write — POST, PUT, PATCH, DELETE with request bodies

  # Patterns demonstrated:
  #   performs a POST call at 'URL' with body '...'
  #   performs a PUT call at 'URL' with body '...'
  #   performs a PATCH call at 'URL' with body '...'
  #   performs a DELETE call at 'URL'
  #   sets a request header 'X' to 'Y'            — header before the call
  #   the response status should be 200 / 201 / 204
  #
  # For large or reusable bodies, load from a file — see rest_resource_payload.feature.
  # For full CRUD chain with variable extraction — see rest_lifecycle.feature.
  #
  # Run:  noodle run features/api/rest_write.feature --no-capture

  Background:
    Given sets `REST_BASE_URL` to '[RESTFULAPI]'

  @smoke @post
  Scenario: POST — create a new object
    Given sets a request header 'Content-Type' to 'application/json'
    When performs a POST call at '/objects' with body '{"name":"Noodle Test Device","data":{"year":2026}}'
    Then the response status should be 200
    And the response body should contain 'Noodle Test Device'
    And the response body should contain 'id'

  @put
  Scenario: PUT — full replacement of object id 7
    Given sets a request header 'Content-Type' to 'application/json'
    When performs a PUT call at '/objects/7' with body '{"name":"Noodle Updated","data":{"year":2026}}'
    Then the response status should be 200
    And the response body should contain 'Noodle Updated'

  @patch
  Scenario: PATCH — partial update of object id 7
    Given sets a request header 'Content-Type' to 'application/json'
    When performs a PATCH call at '/objects/7' with body '{"name":"Noodle Patched"}'
    Then the response status should be 200
    And the response body should contain 'Noodle Patched'

  @delete
  Scenario: DELETE — remove an object (id 7 is safe to delete on this sandbox)
    When performs a DELETE call at '/objects/7'
    Then the response status should be 200

  @run_command @post_curl
  Scenario: POST via curl — full control over Content-Type and response parsing
    # When you need strict Content-Type or want to parse a field from the JSON
    # response in a later step, drop to run_command with curl.
    When User runs the command 'curl -s -X POST "[RESTFULAPI]/objects" -H "Content-Type: application/json" -d "{\"name\":\"curl-test\"}"' and storing the output in `POST_OUT`
    Then `POST_OUT` should contain 'curl-test'
    And `POST_OUT` should contain 'id'
