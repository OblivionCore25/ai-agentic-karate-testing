Feature: Order Creation - Negative Item Quantity Boundary Validation

  # Tests the boundary constraint: items[].quantity must be >= 1 (minimum: 1)
  # Spec: POST /orders - items[].quantity: integer, minimum: 1
  # Spec: POST /orders - 400 response schema: {code, message}

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @boundary @validation
  Scenario Outline: Create order with item quantity of negative value and receive 400 validation error

    # Business Rule: item quantity must satisfy minimum: 1 constraint.
    # Sending quantity = <quantity> (below the lower boundary of 1) must be rejected with HTTP 400.
    # The response body must conform to the error schema: {code, message}.

    * url baseUrl
    * header Authorization = 'Bearer test-token'
    Given path '/orders'
    And request
      """
      {
        "customerId": "<customerId>",
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
    Then status <expectedStatus>

    # Assert the error response body matches the expected schema: {code, message}
    And match response.code == '#present'
    And match response.message == '#notnull'
    And match response.message contains '#string'

    Examples:
      | read('classpath:testdata/negative-quantity-boundary.csv') |