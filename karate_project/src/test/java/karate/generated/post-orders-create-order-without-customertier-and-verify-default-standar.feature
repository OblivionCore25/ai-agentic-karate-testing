Feature: Default CustomerTier Behavior for Order Creation

  # Business Rule: When customerTier is omitted from a POST /orders request,
  # the system must default to 'STANDARD' tier, apply zero discount, and return
  # a valid order with totalAmount equal to the full item total.
  # Spec reference: POST /orders - customerTier field with default: 'STANDARD'

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'

  @business_rule
  Scenario: Create order without customerTier and verify default STANDARD tier behavior
    # Business Rule: customerTier is NOT a required field per spec.
    # When omitted, the system should deserialize the request using the default
    # value of 'STANDARD', resulting in no discount and full price totalAmount.

    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-123",
        "items": [
          {
            "productId": "prod-1",
            "quantity": 2,
            "price": 100.0
          }
        ]
      }
      """
    When method POST
    Then status 201

    # Verify no discount is applied when defaulting to STANDARD tier
    And match response.discountApplied == 0.0

    # Verify order is created in initial PENDING state
    And match response.status == 'PENDING'

    # Verify totalAmount equals full item total (2 x 100.0 = 200.0) with no discount deducted
    And match response.totalAmount == 200.0

    # Verify the response contains a valid order identity
    And match response.id == '#notnull'
    And match response.customerId == 'cust-123'