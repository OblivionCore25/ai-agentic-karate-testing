Feature: Order Creation Error Handling - Empty Request Body

  # Tests error handling for POST /orders when a completely empty JSON object is submitted.
  # Business Rule: All required fields (customerId, items) must be present; omitting them yields HTTP 400.
  # Source: spec POST /orders, OrderController.java @RequestBody OrderRequest

  Background:
    # Shared setup: base URL and valid bearer token as required by preconditions
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @error_handling
  Scenario: Create order with a completely empty request body and receive 400 error
    # Business Rule: POST /orders requires both 'customerId' and 'items' fields.
    # Sending an empty JSON object {} omits all required fields and must trigger a 400 Bad Request.
    # The response body must contain 'code' and 'message' fields per the 400 error schema.

    Given path '/orders'
    # Empty request body - omits all required fields: customerId and items
    And request {}
    When method POST
    Then status 400

    # Validate that the error response body contains the required 'code' field
    And match response.code == '#present'
    And match response.code == '#notnull'

    # Validate that the error response body contains the required 'message' field
    And match response.message == '#present'
    And match response.message == '#notnull'

    # Validate overall response shape matches the 400 error schema: {code, message}
    And match response contains { code: '#notnull', message: '#notnull' }