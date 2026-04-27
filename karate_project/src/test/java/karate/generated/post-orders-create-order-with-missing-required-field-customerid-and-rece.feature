Feature: Order Validation - Missing Required Field customerId

  # Tests the @RequestBody validation path in OrderController.createOrder()
  # Business Rule: POST /orders requires 'customerId' as a mandatory field.
  # Submitting an order without customerId must trigger validation failure and return HTTP 400
  # with a structured error response containing 'code' and 'message' fields.

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  # Business Rule: customerId is required per POST /orders spec.
  # A null customerId must result in HTTP 400 with a structured error body.
  @validation
  Scenario Outline: Create order with missing required field customerId and receive 400 error
    # Load test data from CSV for data-driven validation coverage
    * def testData = read('testdata/order-missing-customerid.csv')

    Given path '/orders'
    And request
      """
      {
        "customerId": <customerId>,
        "customerTier": "<customerTier>",
        "items": [
          {
            "productId": "<productId>",
            "quantity": <quantity>,
            "price": <price>
          }
        ]
      }
      """
    When method POST

    # Assert HTTP 400 is returned when customerId is missing/null
    Then status <expectedStatus>

    # Assert the error response body contains required 'code' and 'message' fields
    # per POST /orders 400 response schema: {code, message}
    And match response.code == '#present'
    And match response.message == '#present'
    And match response.code == '#notnull'
    And match response.message == '#notnull'

    Examples:
      | read('testdata/order-missing-customerid.csv') |