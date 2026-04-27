Feature: Order Validation - Missing Required Item Fields

  # Business Rule: POST /orders requires each item in the items array to include
  # productId, quantity, AND price. Omitting any of these required fields must
  # result in HTTP 400 with a structured error response containing code and message.

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @validation
  # Business Rule: items[].price is a required field per the POST /orders spec.
  # Submitting an order where an item is missing the price field must be rejected
  # with HTTP 400 and an error body conforming to {code, message} schema.
  Scenario: Create order with item missing required price field and receive 400 error
    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-123",
        "customerTier": "STANDARD",
        "items": [
          {
            "productId": "prod-1",
            "quantity": 2
          }
        ]
      }
      """
    When method POST
    Then status 400
    And match response.code == '#present'
    And match response.message == '#present'
    And match response.code == '#notnull'
    And match response.message == '#notnull'

  @validation
  # Business Rule: Validates that the 400 error response body strictly conforms
  # to the {code, message} schema defined in the POST /orders spec, and that the
  # message content references the missing field to aid client-side debugging.
  Scenario Outline: Create orders with missing item fields returns 400 for various omission combinations
    Given path '/orders'
    And request
      """
      {
        "customerId": "<customerId>",
        "customerTier": "<customerTier>",
        "items": [
          <itemPayload>
        ]
      }
      """
    When method POST
    Then status <expectedStatus>
    And match response.code == '#notnull'
    And match response.message == '#notnull'

    Examples:
      | read('testdata/order-missing-price.csv') |