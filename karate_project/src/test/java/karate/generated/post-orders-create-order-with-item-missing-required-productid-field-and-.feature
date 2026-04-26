Feature: Order Validation - Missing Required Item Fields

  # Business Rule: Each item in the items array requires productId, quantity, and price.
  # Omitting productId from any item must fail validation and return HTTP 400.
  # Spec Reference: POST /orders - items[]: required: [productId, quantity, price]
  # Spec Reference: POST /orders - 400 response schema: {code, message}

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @validation
  Scenario: Create order with item missing required productId field and receive 400 error

    # Business Rule: productId is a required field for every item in the items array.
    # Submitting an item without productId must be rejected with HTTP 400 and a descriptive error body.

    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-123",
        "customerTier": "STANDARD",
        "items": [
          {
            "quantity": 2,
            "price": 100.0
          }
        ]
      }
      """
    When method POST
    Then status 400
    And match response.code == '#notnull'
    And match response.message == '#notnull'
    And match response.message contains '#string'

  @validation
  Scenario Outline: Create orders with missing or invalid item fields and receive 400 error

    # Business Rule: All three item fields (productId, quantity, price) are required.
    # This data-driven scenario validates that omitting any required item field returns HTTP 400.

    * def testData = read('classpath:testdata/order-missing-item-fields.csv')

    Given path '/orders'
    And request
      """
      {
        "customerId": "<customerId>",
        "customerTier": "<customerTier>",
        "items": [
          {
            "quantity": <quantity>,
            "price": <price>
          }
        ]
      }
      """
    When method POST
    Then status <expectedStatus>
    And match response.code == '#notnull'
    And match response.message == '#notnull'

    Examples:
      | customerId | customerTier | quantity | price | expectedStatus |
      | cust-123   | STANDARD     | 2        | 100.0 | 400            |
      | cust-456   | GOLD         | 1        | 50.0  | 400            |
      | cust-789   | SILVER       | 5        | 75.0  | 400            |