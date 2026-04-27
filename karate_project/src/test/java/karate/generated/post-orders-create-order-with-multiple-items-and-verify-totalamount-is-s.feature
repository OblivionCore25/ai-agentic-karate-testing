Feature: Order Total Amount Calculation

  # Business Rule: When an order contains multiple items, the totalAmount must equal
  # the sum of (quantity * price) for each line item in the items array.
  # Reference: POST /orders spec, OrderController.java -> orderService.createOrder()

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @happy_path
  Scenario Outline: Create order with multiple items and verify totalAmount is sum of all item totals

    # Business Rule: totalAmount = sum of (quantity * price) for each item in the order.
    # This scenario validates the total calculation logic across multiple line items
    # for a STANDARD tier customer (no discount expected).

    * url baseUrl
    * header Authorization = 'Bearer test-token'

    Given path '/orders'
    And def orderRequest =
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
          },
          {
            "productId": "<productId3>",
            "quantity": <quantity3>,
            "price": <price3>
          }
        ]
      }
      """
    And request orderRequest
    When method POST
    Then status <expectedStatus>

    # Assert totalAmount equals the expected sum: (2*50.0) + (1*150.0) + (3*30.0) = 340.0
    And match response.totalAmount == <expectedTotalAmount>

    # Assert no discount is applied for STANDARD tier customer
    And match response.discountApplied == <expectedDiscountApplied>

    # Assert order is created in PENDING state with a valid ID
    And match response.status == 'PENDING'
    And match response.id == '#notnull'
    And match response.id == '#present'

    # Assert all items are present in the response
    And match response.items == '#[3]'

    Examples:
      | read('testdata/order-multi-item-totals.csv') |