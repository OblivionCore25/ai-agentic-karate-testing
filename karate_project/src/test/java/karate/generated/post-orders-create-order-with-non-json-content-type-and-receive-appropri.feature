Feature: Order API - Content Type Validation and Error Handling

  # Tests content negotiation and deserialization error path when non-JSON content types are sent.
  # Business Rule: POST /orders endpoint uses @RequestBody annotation and expects application/json.
  # Sending text/plain or omitting Content-Type should be rejected with HTTP 415 or 400.

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'

  @error_handling
  Scenario: Create order with text/plain Content-Type should be rejected with 415 Unsupported Media Type
    # Business Rule: Spring @RequestBody handler requires application/json content type.
    # Sending Content-Type: text/plain bypasses JSON deserialization and must be rejected.
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'text/plain'
    Given path '/orders'
    And request 'customerId=cust-123'
    When method POST
    Then status 415

  @error_handling
  Scenario: Create order with no Content-Type header should be rejected with 415 or 400
    # Business Rule: Absence of Content-Type header means the server cannot determine
    # how to deserialize the request body, resulting in a 415 or 400 error response.
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    Given path '/orders'
    And request 'customerId=cust-123'
    When method POST
    Then status 415
    # Note: Some Spring configurations may return 400 instead of 415 depending on
    # the error handling configuration. Both are acceptable per the scenario spec.

  @error_handling
  Scenario: Create order with application/x-www-form-urlencoded Content-Type should be rejected
    # Business Rule: Only application/json is accepted by the @RequestBody annotated endpoint.
    # Form-encoded data is not a supported media type for this endpoint.
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/x-www-form-urlencoded'
    Given path '/orders'
    And request 'customerId=cust-123&items=prod-1'
    When method POST
    Then status 415
    And match responseStatus == 415 || responseStatus == 400

  @error_handling
  Scenario Outline: Create order with various unsupported content types should be rejected
    # Business Rule: The POST /orders endpoint must reject all non-JSON content types
    # with an appropriate HTTP error status (415 Unsupported Media Type or 400 Bad Request).
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = '<contentType>'
    Given path '/orders'
    And request '<requestBody>'
    When method POST
    Then status <expectedStatus>

    Examples:
      | contentType                       | requestBody        | expectedStatus |
      | text/plain                        | customerId=cust-123 | 415           |
      | application/x-www-form-urlencoded | customerId=cust-123 | 415           |
      | text/xml                          | customerId=cust-123 | 415           |