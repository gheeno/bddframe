@rest @api
Feature: REST API — payloads loaded from resource files
  # Demonstrates the load_resource step: payload files live under
  # features/<suite>/resources/ and are referenced by relative path.
  #
  # Run it:
  #   bddframe run features/persona_test/14_resource_payload.feature --no-capture

  Background:
    Given sets `REST_BASE_URL` to '[RESTFULAPI]'

  @smoke
  Scenario: POST with a single payload file
    Given uses this payload 'payloads/create_device.json'
    When performs a POST call at '/objects' with body '`PAYLOAD`'
    Then the response status should be 200
    And the response body should contain 'BDDFrame Resource Device'
    And the response body should contain 'id'

  @smoke
  Scenario: POST then PUT using payloads from a table
    Given uses these payloads:
      | payload                      |
      | payloads/create_device.json  |
      | payloads/update_device.json  |
    When performs a POST call at '/objects' with body '`PAYLOAD_CREATE_DEVICE`'
    And extracts 'id' from response storing in `DEV_ID`
    When performs a PUT call at '/objects/`DEV_ID`' with body '`PAYLOAD_UPDATE_DEVICE`'
    Then the response status should be 200
    And the response body should contain 'BDDFrame Updated Device'
    And the response body should contain 'updatedAt'
