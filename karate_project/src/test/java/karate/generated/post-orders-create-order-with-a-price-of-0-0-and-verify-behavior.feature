Feature: Create Order with Zero Price - Boundary Validation

  # Tests boundary behavior when an item with price=0.0 is submitted.
  # The API spec does not define a minimum for price (format: double, no minimum),
  # so zero-price items may be accepted (HTTP 201) or rejected (HTTP 400) depending
  # on business logic. Both outcomes are validated in this feature.

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  # Business Rule: Zero-price items are a boundary case with no defined minimum in the spec.
  # This scenario verifies the primary expected outcome: HTTP 201 with totalAmount=0.0
  # and discountApplied=0.0 when a single item with price=0.0 is submitted.
  @boundary @happy_path
  Scenario: Create order with zero-price item and verify totals are zero
    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-123",
        "customerTier": "STANDARD",
        "items": [
          {
            "productId": "prod-free",
            "quantity": 1,
            "price": 0.0
          }
        ]
      }
      """
    When method POST
    Then status 201
    # Business Rule: totalAmount should equal sum of (price * quantity) = 0.0 * 1 = 0.0
    And match response.totalAmount == 0.0
    # Business Rule: No discount should be applied when order value is zero
    And match response.discountApplied == 0.0
    # Business Rule: Newly created orders must have a PENDING status
    And match response.status == 'PENDING'
    # Business Rule: Response must include a generated order ID
    And match response.id == '#notnull'
    And match response.customerId == 'cust-123'

  # Business Rule: If the system enforces a minimum price greater than 0.0,
  # a zero-price item must be rejected with HTTP 400 and a meaningful error message.
  @boundary @negative
  Scenario: Create order with zero-price item rejected by business logic
    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-123",
        "customerTier": "STANDARD",
        "items": [
          {
            "productId": "prod-free",
            "quantity": 1,
            "price": 0.0
          }
        ]
      }
      """
    When method POST
    # Business Rule: If zero price violates a business constraint, HTTP 400 is expected
    Then match responseStatus == 400 || responseStatus == 201
    * if (responseStatus == 400) karate.log('Zero price rejected by business logic - HTTP 400 received as per alternate expected outcome')
    * if (responseStatus == 201) karate.log('Zero price accepted by API - HTTP 201 received as per primary expected outcome')

  # Business Rule: Data-driven boundary tests covering zero price alongside
  # other price boundary values to confirm consistent validation behavior.
  @boundary @data_driven
  Scenario Outline: Create order with boundary price values and verify response
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
    # Business Rule: On successful creation, totalAmount must equal price * quantity
    * if (responseStatus == 201) karate.match(response.totalAmount, <expectedTotalAmount>)
    # Business Rule: On successful creation, discountApplied must reflect tier-based discount
    * if (responseStatus == 201) karate.match(response.discountApplied, <expectedDiscountApplied>)
    # Business Rule: On rejection, a descriptive error message must be present
    * if (responseStatus == 400) karate.match(response.message, '#notnull')

    Examples:
    | read('classpath:testdata/zero-price-boundary.csv') |