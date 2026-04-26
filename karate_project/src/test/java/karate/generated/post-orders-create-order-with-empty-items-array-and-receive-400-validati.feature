Feature: Order Creation Validation - Empty Items Array

  # Tests the minItems: 1 constraint on the 'items' array for POST /orders.
  # Spec reference: POST /orders - items array with minItems: 1
  # Spec reference: POST /orders - 400 response schema: {code, message}

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @validation
  # Business Rule: The 'items' array must contain at least one item (minItems: 1).
  # Sending an empty array must be rejected with HTTP 400 and a structured error body.
  Scenario: Create order with empty items array and receive 400 validation error
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    Given path '/orders'
    And request { customerId: 'cust-123', customerTier: 'STANDARD', items: [] }
    When method POST
    Then status 400
    # Verify the error response body contains both 'code' and 'message' fields
    And match response.code == '#present'
    And match response.message == '#present'
    And match response.code == '#notnull'
    And match response.message == '#notnull'

  @validation
  # Business Rule: The minItems: 1 constraint applies regardless of customer tier or customerId.
  # Data-driven coverage ensures the empty items rejection is consistent across inputs.
  Scenario Outline: Create order with empty items array is rejected for various customer inputs
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    Given path '/orders'
    And request { customerId: '<customerId>', customerTier: '<customerTier>', items: [] }
    When method POST
    Then status <expectedStatus>
    And match response.code == '#notnull'
    And match response.message == '#notnull'

    Examples:
      | read('classpath:testdata/empty-items-validation.csv') |