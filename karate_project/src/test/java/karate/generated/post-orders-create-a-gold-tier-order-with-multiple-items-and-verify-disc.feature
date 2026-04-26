Feature: GOLD Tier Order Discount Applied to Combined Total

  # Business Rule: For GOLD tier customers, a 10% discount is applied to the
  # combined total of all items in the order, not calculated on a per-item basis.
  # This ensures discount aggregation works correctly across multi-item orders.
  # Reference: POST /orders spec, orders-data-driven.feature (cust-002 pattern),
  #            OrderController.java -> orderService.createOrder(request)

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @business_rule
  Scenario: Create a GOLD tier order with multiple items and verify discount is applied to combined total

    # Business Rule: GOLD tier discount (10%) must be calculated on the aggregated
    # order total (sum of all item subtotals), not applied individually per line item.
    # Test Data:
    #   - prod-1: quantity=2, price=100.0 => subtotal=200.0
    #   - prod-2: quantity=1, price=200.0 => subtotal=200.0
    #   - Combined gross total = 400.0
    #   - Expected discount = 10% of 400.0 = 40.0
    #   - Expected net total = 400.0 - 40.0 = 360.0

    * def orderRequest =
      """
      {
        "customerId": "cust-gold-multi",
        "customerTier": "GOLD",
        "items": [
          {
            "productId": "prod-1",
            "quantity": 2,
            "price": 100.0
          },
          {
            "productId": "prod-2",
            "quantity": 1,
            "price": 200.0
          }
        ]
      }
      """

    Given path '/orders'
    And request orderRequest
    When method POST
    Then status 201

    # Verify the gross total reflects the sum of all item subtotals (2*100 + 1*200 = 400)
    And match response.grossTotalAmount == 400.0

    # Verify the discount is 10% of the combined total (not per-item), i.e. 40.0
    And match response.discountApplied == 40.0

    # Verify the net total after discount is correctly reduced (400 - 40 = 360)
    And match response.totalAmount == 360.0

    # Verify the order was created with the correct customer and tier
    And match response.customerId == 'cust-gold-multi'
    And match response.customerTier == 'GOLD'

    # Verify the order is in a valid initial state and has been assigned an ID
    And match response.id == '#notnull'
    And match response.status == 'PENDING'

    # Verify both line items are present in the response
    And match response.items == '#[2]'
    And match response.items contains deep { "productId": "prod-1", "quantity": 2, "price": 100.0 }
    And match response.items contains deep { "productId": "prod-2", "quantity": 1, "price": 200.0 }

  @business_rule
  Scenario Outline: GOLD tier discount is applied to combined total across multiple order configurations

    # Business Rule: Validates the 10% GOLD tier combined-total discount rule
    # across a range of multi-item order configurations using data-driven inputs.

    * def orderRequest =
      """
      {
        "customerId": "<customerId>",
        "customerTier": "<customerTier>",
        "items": [
          {
            "productId": "<productId1>",
            "quantity": <quantity1>,
            "price": <price1>
          },
          {
            "productId": "<productId2>",
            "quantity": <quantity2>,
            "price": <price2>
          }
        ]
      }
      """

    Given path '/orders'
    And request orderRequest
    When method POST
    Then status <expectedStatus>

    # Verify discount is applied to the combined gross total, not per item
    And match response.grossTotalAmount == <expectedGrossTotalAmount>
    And match response.discountApplied == <expectedDiscountApplied>
    And match response.totalAmount == <expectedTotalAmount>

    Examples:
      | read('classpath:testdata/gold-tier-multi-item-orders.csv') |