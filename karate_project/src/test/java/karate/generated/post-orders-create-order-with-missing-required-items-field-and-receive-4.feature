Feature: Order Validation - Missing Required Fields

  # Business Rule: POST /orders requires both 'customerId' and 'items' fields.
  # Omitting 'items' entirely must trigger a 400 validation error with a structured
  # error response body containing 'code' and 'message' fields.
  # Spec reference: POST /orders - required: [customerId, items]
  # Spec reference: POST /orders - 400 response schema: {code, message}

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @validation
  Scenario: Create order with missing required items field and receive 400 validation error
    # Business Rule: The 'items' field is marked as required in the POST /orders spec.
    # Submitting a request body that omits 'items' entirely should result in HTTP 400.

    Given path '/orders'
    And request { customerId: 'cust-123', customerTier: 'STANDARD' }
    When method POST
    Then status 400

    # Validate that the error response body contains the required 'code' and 'message' fields
    And match response.code == '#present'
    And match response.message == '#present'
    And match response.code == '#notnull'
    And match response.message == '#notnull'

  @validation
  Scenario Outline: Create orders with missing items field across multiple customer configurations and receive 400
    # Business Rule: Regardless of customerId or customerTier value, omitting 'items'
    # must always produce a 400 validation error with a structured error body.

    Given path '/orders'
    And request { customerId: '<customerId>', customerTier: '<customerTier>' }
    When method POST
    Then status <expectedStatus>
    And match response.code == '#present'
    And match response.message == '#present'
    And match response.code == '#notnull'
    And match response.message == '#notnull'

    Examples:
      | read('classpath:testdata/order-missing-items-validation.csv') |