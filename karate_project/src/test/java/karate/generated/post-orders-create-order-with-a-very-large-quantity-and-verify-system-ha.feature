Feature: Order Creation - Large Quantity Boundary Test

  # Tests integer overflow boundary conditions in order total computation logic.
  # Spec: POST /orders - items[].quantity: integer, minimum: 1 (no maximum defined)
  # Spec: POST /orders - totalAmount: number, format: double
  # Source: OrderController.java - createOrder() delegates to orderService.createOrder(request)

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  # Business Rule: When quantity is Integer.MAX_VALUE (2147483647), the system must either:
  #   (a) Return HTTP 201 with a correctly computed totalAmount using double precision (no integer overflow), OR
  #   (b) Return HTTP 400 if a maximum quantity business limit is enforced.
  # This verifies the order total computation logic is overflow-safe.
  @boundary
  Scenario Outline: Create order with a very large quantity and verify system handles it without overflow
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
    # Business Rule: System must respond with 201 (success with overflow-safe total) or 400 (quantity limit enforced)
    Then status <expectedStatus>
    * def isSuccess = responseStatus == 201
    * if (isSuccess) karate.call('classpath:helpers/assert-large-quantity-response.feature', { response: response, quantity: <quantity>, price: <price> })
    * if (!isSuccess) match response contains { error: '#notnull' }

    Examples:
      | read('testdata/large-quantity-orders.csv') |



  # Inline single-scenario variant for direct execution without CSV dependency.
  # Business Rule: totalAmount must be computed as double (2147483647 * 1.0 = 2.147483647E9) without overflow.
  @boundary
  Scenario: Create order with Integer.MAX_VALUE quantity - inline boundary check
    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-123",
        "customerTier": "STANDARD",
        "items": [
          {
            "productId": "prod-1",
            "quantity": 2147483647,
            "price": 1.0
          }
        ]
      }
      """
    When method POST
    # Business Rule: Accept 201 (overflow-safe double computation) or 400 (max quantity limit enforced)
    Then status '#? _ == 201 || _ == 400'
    * def isCreated = responseStatus == 201
    * def isRejected = responseStatus == 400
    # If created: totalAmount must be a valid non-null number (double precision, no overflow to negative)
    * if (isCreated) match response.totalAmount == '#notnull'
    * if (isCreated) match response.totalAmount == '#number'
    # Business Rule: totalAmount must be positive - integer overflow would produce a negative value
    * if (isCreated) assert response.totalAmount > 0
    # Business Rule: Correct double-precision result: 2147483647 * 1.0 = 2147483647.0
    * if (isCreated) assert response.totalAmount == 2147483647.0
    * if (isCreated) match response.status == '#notnull'
    # If rejected: error details must be present
    * if (isRejected) match response contains { error: '#notnull' }