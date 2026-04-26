Feature: Create Order - Minimum Quantity Boundary Validation

  # Tests that the POST /orders endpoint correctly accepts quantity=1 (minimum valid value per spec)
  # and returns HTTP 201 with totalAmount calculated as 1 * price.
  # Business Rule: items[].quantity must be an integer with minimum: 1

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @boundary @happy_path
  Scenario Outline: Create order with item quantity of exactly 1 (minimum boundary) and succeed

    # Business Rule: quantity=1 is the exact lower boundary per spec (minimum: 1).
    # Sending this value must be accepted and result in a successful order creation.
    # Expected: HTTP 201, totalAmount == 1 * price (no discount for STANDARD tier).

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

    # Assert order was created with correct totalAmount (quantity * price = 1 * 99.99 = 99.99)
    And match response.totalAmount == <expectedTotalAmount>

    # Assert no discount is applied for STANDARD tier
    And match response.discountApplied == <expectedDiscountApplied>

    # Assert core response fields are present and valid
    And match response.id == '#notnull'
    And match response.status == '#present'
    And match response.customerId == '<customerId>'

    Examples:
      | read('classpath:testdata/order-min-quantity-boundary.csv') |