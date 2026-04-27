Feature: Create Standard Order - Happy Path
  # Tests the order creation flow for STANDARD tier customers
  # Business Rules Verified:
  #   - POST /orders returns HTTP 201 for valid requests
  #   - totalAmount is calculated as sum of (quantity * price)
  #   - New orders are assigned PENDING status
  #   - STANDARD tier customers receive no discount (discountApplied = 0.0)
  #   - Response contains a valid UUID id

  Background:
    # Shared setup: base URL and authorization header applied to all scenarios
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * def expectedUuidRegex = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

  @happy_path
  Scenario: Create a standard order successfully with correct total amount and PENDING status
    # Business Rule: A STANDARD tier customer submitting a valid order with one or more items
    # should receive HTTP 201, a correctly computed totalAmount (quantity * price),
    # an order status of PENDING, and a discountApplied of 0.0.
    # Preconditions: Valid bearer token is available; product 'prod-1' exists in the system.

    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-123",
        "customerTier": "STANDARD",
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

    # Verify the response contains a valid UUID id
    And match response.id == '#regex ' + expectedUuidRegex

    # Verify totalAmount equals quantity * price (2 * 100.0 = 200.0)
    And match response.totalAmount == 200.0

    # Verify new order is assigned PENDING status
    And match response.status == 'PENDING'

    # Verify STANDARD tier customers receive no discount
    And match response.discountApplied == 0.0

    # Verify required fields are present in the response
    And match response.customerId == 'cust-123'
    And match response contains { id: '#present', totalAmount: '#present', status: '#present', discountApplied: '#present' }

  @happy_path
  Scenario Outline: Create standard orders with various item configurations - data driven
    # Business Rule: totalAmount must always equal the sum of (quantity * price) for all items,
    # STANDARD tier always yields discountApplied = 0.0, and status is always PENDING on creation.
    # Data is sourced from testdata/standard-order-happy-path.csv

    * def testData = read('testdata/standard-order-happy-path.csv')

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

    # Verify totalAmount calculation: quantity * price
    And match response.totalAmount == <expectedTotalAmount>

    # Verify order status is PENDING upon creation
    And match response.status == 'PENDING'

    # Verify no discount is applied for STANDARD tier
    And match response.discountApplied == <expectedDiscountApplied>

    # Verify a valid id is returned
    And match response.id == '#notnull'

    Examples:
      | read('testdata/standard-order-happy-path.csv') |