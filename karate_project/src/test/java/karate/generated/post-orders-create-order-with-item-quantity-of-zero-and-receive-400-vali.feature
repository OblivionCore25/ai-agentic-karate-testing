Feature: Order Creation - Item Quantity Boundary Validation

  # Tests boundary validation for item quantity field in POST /orders
  # Spec: items[].quantity has minimum: 1 constraint
  # Sending quantity=0 must be rejected with HTTP 400

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @boundary @validation
  # Business Rule: item quantity must be >= 1 (minimum: 1 per spec)
  # Lower boundary test: quantity=0 violates the minimum constraint and must return 400
  Scenario Outline: Create order with item quantity of zero and receive 400 validation error
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
    # Validate error response body matches the 400 schema: {code, message}
    And match response.code == '#present'
    And match response.message == '#notnull'
    And match response.message contains '#string'

    Examples:
      | read('testdata/order-quantity-boundary.csv') |