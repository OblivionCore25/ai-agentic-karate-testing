Feature: Verify Created Order Response Contains All Required Fields

  # Business Rule: After a successful order creation, the 201 response must conform to the full
  # response contract including: id (UUID format), customerId, status (PENDING), totalAmount,
  # discountApplied, non-empty items array, and createdAt (ISO date-time format).

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * def uuidRegex = '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    * def isoDateTimeRegex = '\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?(Z|[+-]\\d{2}:\\d{2})'

  @happy_path
  Scenario: Verify created order response contains all required fields including UUID id and createdAt timestamp
    # Business Rule: POST /orders with a valid STANDARD customer payload must return HTTP 201
    # with a fully populated response body matching the 201 schema contract.
    # Validates: id (UUID), customerId, status=PENDING, totalAmount, discountApplied=0.0,
    # non-empty items array, and createdAt (ISO date-time).

    * url baseUrl
    * header Authorization = 'Bearer test-token'
    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-123",
        "customerTier": "STANDARD",
        "items": [
          {
            "productId": "prod-1",
            "quantity": 1,
            "price": 75.0
          }
        ]
      }
      """
    When method POST
    Then status 201

    # Validate id is present and matches UUID format
    And match response.id == '#present'
    And match response.id == '#notnull'
    And match response.id == '#regex ' + uuidRegex

    # Validate customerId echoed back correctly
    And match response.customerId == 'cust-123'

    # Validate order status is PENDING as per business rule for new orders
    And match response.status == 'PENDING'

    # Validate totalAmount reflects single item price with no discount for STANDARD tier
    And match response.totalAmount == 75.0

    # Validate no discount applied for STANDARD tier customer
    And match response.discountApplied == 0.0

    # Validate items array is present and non-empty
    And match response.items == '#present'
    And match response.items == '#notnull'
    And match response.items == '#[] #notnull'
    And match response.items[0].productId == 'prod-1'
    And match response.items[0].quantity == 1
    And match response.items[0].price == 75.0

    # Validate createdAt is present and conforms to ISO 8601 date-time format
    And match response.createdAt == '#present'
    And match response.createdAt == '#notnull'
    And match response.createdAt == '#regex ' + isoDateTimeRegex

    # Validate full response schema shape - all required fields must be present
    And match response contains
      """
      {
        "id": "#notnull",
        "customerId": "#notnull",
        "status": "#notnull",
        "totalAmount": "#notnull",
        "discountApplied": "#notnull",
        "items": "#notnull",
        "createdAt": "#notnull"
      }
      """