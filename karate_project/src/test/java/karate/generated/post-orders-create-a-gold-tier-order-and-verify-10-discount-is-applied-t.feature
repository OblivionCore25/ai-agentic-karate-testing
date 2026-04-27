Feature: GOLD Tier Order Discount Business Rule

  # Tests the core discount logic in OrderService.createOrder() for GOLD tier customers.
  # API spec states: "Applies discounts for GOLD tier customers"
  # A 10% discount is applied to the total order amount for GOLD tier customers.

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @business_rule @happy_path
  Scenario: Create a GOLD tier order and verify 10% discount is applied to total amount
    # Business Rule: GOLD tier customers receive a 10% discount on their total order amount.
    # cust-002 orders 3x prod-2 at 200.0 each = 600.0 subtotal -> 10% discount = 60.0 -> totalAmount = 540.0
    # Validates the GOLD tier branch in OrderService.createOrder()

    * url baseUrl
    * header Authorization = 'Bearer test-token'
    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-002",
        "customerTier": "GOLD",
        "items": [
          {
            "productId": "prod-2",
            "quantity": 3,
            "price": 200.0
          }
        ]
      }
      """
    When method POST
    Then status 201

    # Assert discount is exactly 10% of 600.0 (subtotal)
    And match response.discountApplied == 60.0

    # Assert totalAmount reflects the discounted value (600.0 - 60.0 = 540.0)
    And match response.totalAmount == 540.0

    # Assert supporting response fields are present and valid
    And match response.customerId == 'cust-002'
    And match response.customerTier == 'GOLD'
    And match response.id == '#notnull'
    And match response.status == '#present'

  @business_rule @data_driven
  Scenario Outline: Verify GOLD tier 10% discount across multiple order configurations
    # Business Rule: 10% discount must be consistently applied for all GOLD tier orders
    # regardless of product or quantity, as long as the subtotal meets the threshold.
    # Driven by companion CSV: testdata/gold-tier-discount-orders.csv

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
    And match response.discountApplied == <expectedDiscountApplied>
    And match response.totalAmount == <expectedTotalAmount>
    And match response.customerTier == 'GOLD'
    And match response.id == '#notnull'

    Examples:
      | read('testdata/gold-tier-discount-orders.csv') |