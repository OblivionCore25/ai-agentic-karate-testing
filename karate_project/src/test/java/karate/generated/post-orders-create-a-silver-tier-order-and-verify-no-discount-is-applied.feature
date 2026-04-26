Feature: SILVER Tier Order - No Discount Applied

  # Business Rule: Discounts are only applied for GOLD tier customers.
  # SILVER tier customers must receive no discount (discountApplied=0.0).
  # This feature validates the negative branch of the discount logic,
  # ensuring SILVER tier is not incorrectly treated as GOLD.

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'

  @business_rule
  Scenario: Create a SILVER tier order and verify no discount is applied
    # Business Rule: POST /orders applies discounts only for GOLD tier customers.
    # SILVER tier must result in discountApplied=0.0 and totalAmount = sum(quantity * price).
    # Test data: cust-004, SILVER, qty=5, price=150.0 => totalAmount=750.0, discountApplied=0.0

    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-004",
        "customerTier": "SILVER",
        "items": [
          {
            "productId": "prod-1",
            "quantity": 5,
            "price": 150.0
          }
        ]
      }
      """
    When method POST
    Then status 201

    # Verify no discount is applied for SILVER tier
    And match response.discountApplied == 0.0

    # Verify totalAmount equals full sum of (quantity * price): 5 * 150.0 = 750.0
    And match response.totalAmount == 750.0

    # Verify the order was created with correct customer and tier details
    And match response.customerId == 'cust-004'
    And match response.customerTier == 'SILVER'

    # Verify the response contains expected structural fields
    And match response.id == '#notnull'
    And match response.status == '#present'

  @business_rule
  Scenario Outline: Verify SILVER tier orders never receive a discount across multiple data rows
    # Business Rule: Regardless of quantity or price, SILVER tier must always yield discountApplied=0.0.
    # This outline drives multiple SILVER tier combinations from CSV to confirm consistent behaviour.

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
    And match response.discountApplied == <expectedDiscount>
    And match response.totalAmount == <expectedTotalAmount>

    Examples:
      | read('classpath:testdata/silver-tier-orders.csv') |