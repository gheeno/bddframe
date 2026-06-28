@rest @api
Feature: REST API — GET operations against restful-api.dev
  # Exercises: REST GET calls using the proper HTTP client (no curl).
  #
  # Resolution path:
  #   performs a GET call at '/path' → rest_client (urllib) → REST_STATUS, REST_BODY
  #
  # Assertions:
  #   the response status should be 200     → status code check
  #   the response body should contain 'x'  → string-contains on body
  #   the response body should contain:     → table-driven key/value checks
  #     | Key | Value |
  #
  # Objects 1–13 are permanent fixtures the server guarantees.
  #
  # Run it:
  #   bddframe run features/persona_test/11_rest_get.feature --no-capture

  Background:
    Given sets `REST_BASE_URL` to '[RESTFULAPI]'

  @smoke
  Scenario: GET all objects returns 200 OK
    When performs a GET call at '/objects'
    Then the response status should be 200

  @smoke
  Scenario: GET all objects body contains expected shape
    When performs a GET call at '/objects'
    Then the response status should be 200
    And the response body should contain:
      | Key  | Value |
      | id   |       |
      | name |       |
      | data |       |

  @smoke
  Scenario Outline: GET object by ID returns the expected name
    When performs a GET call at '/objects/<id>'
    Then the response status should be 200
    And the response body should contain '<name>'

    Examples:
      | id | name                    |
      | 1  | Google Pixel 6 Pro      |
      | 5  | Samsung Galaxy Z Fold2  |

  @smoke
  Scenario: GET object and store response for downstream assertion
    When performs a GET call at '/objects/1' storing response in `OBJECT_1`
    Then `OBJECT_1` should contain 'Google Pixel 6 Pro'
    And `OBJECT_1` should contain 'id'

  @smoke
  Scenario: GET by query params returns matching objects
    When performs a GET call at '/objects?id=3&id=5&id=10'
    Then the response status should be 200
    And the response body should contain 'id'
    And the response body should contain 'name'

  @smoke
  Scenario: GET non-existent object returns 404 with error body
    When performs a GET call at '/objects/nonexistent-id-99999'
    Then the response status should be 404
    And the response body should contain 'error'

  @smoke
  Scenario: GET response includes expected Content-Type header
    When performs a GET call at '/objects/1'
    Then the response status should be 200
    And the response header 'Content-Type' should contain 'application/json'
