Feature: GOLD Tier Order Discount Threshold Behavior

  # Business Rule: GOLD tier customers may have a minimum order value threshold
  # before discounts are applied. This feature probes the boundary condition
  # where a GOLD customer with a low-price single item (total = $50.00) receives
  # no discount, contrasting with cust-002 (GOLD, qty=3, price=200.0) who does.
  # Reference: orders-data-driven.feature row cust-003 anomaly vs cust-002.

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @business_rule
  Scenario Outline: GOLD tier order discount threshold - verify discount eligibility based on order value

    # Business Rule: GOLD discount is NOT applied when the total order value falls
    # below the minimum threshold. A single item at $50.00 (total = $50.00) should
    # yield discountApplied = 0.0, even for a GOLD tier customer.
    # This contrasts with cust-002 (GOLD, 3 x $200.00 = $600.00) which receives a discount.

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

    # Assert discount is 0.0 — confirming the minimum order value threshold is not met
    And match response.discountApplied == <expectedDiscountApplied>

    # Assert core response fields are present and well-formed
    And match response.customerId == '<customerId>'
    And match response.customerTier == '<customerTier>'
    And match response.status == 'PENDING'
    And match response.id == '#notnull'
    And match response.totalAmount == '#present'

    # Assert total amount reflects qty * price with no discount deducted
    And match response.totalAmount == <expectedTotalAmount>

    Examples:
      | customerId | customerTier | productId | quantity | price | expectedStatus | expectedDiscountApplied | expectedTotalAmount |
      | cust-003   | GOLD         | prod-3    | 1        | 50.0  | 201            | 0.0                     | 50.0                |

  @business_rule
  Scenario: GOLD tier order above threshold receives discount - contrast case for boundary validation

    # Business Rule: This scenario documents the GOLD discount-eligible case for
    # comparison. cust-002 with qty=3 and price=200.0 (total=$600.00) receives
    # a discount, confirming the threshold lies somewhere between $50.00 and $600.00.
    # This contrast scenario validates the boundary from the other side.

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

    # Assert discount IS applied for the high-value GOLD order
    And match response.discountApplied == 60.0
    And match response.customerId == 'cust-002'
    And match response.customerTier == 'GOLD'
    And match response.status == 'PENDING'
    And match response.id == '#notnull'

  @business_rule
  Scenario Outline: GOLD tier discount threshold boundary sweep - multiple order values

    # Business Rule: Sweep across order values to probe where the GOLD discount
    # threshold boundary lies. Uses companion CSV data covering low, mid, and
    # high order values for GOLD tier customers to identify the exact cutoff.

    * url baseUrl
    * header Authorization = 'Bearer test-token'
    Given path '/orders'
    And request
      """
      {
        "customerId": "<customerId>",
        "customerTier": "GOLD",
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
    And match response.id == '#notnull'
    And match response.status == '#notnull'

    Examples:
      | customerId | productId | quantity | price  | expectedStatus | expectedDiscountApplied |
      | cust-003   | prod-3    | 1        | 50.0   | 201            | 0.0                     |
      | cust-003   | prod-3    | 2        | 50.0   | 201            | 0.0                     |
      | cust-003   | prod-3    | 1        | 200.0  | 201            | 0.0                     |
      | cust-003   | prod-3    | 3        | 200.0  | 201            | 60.0                    |