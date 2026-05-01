Feature: Create Order with Numeric Overflow - Boundary Test

  # Tests that submitting an order with a total_amount exceeding NUMERIC(12,2) precision
  # (max 9,999,999,999.99) is handled gracefully by the service layer,
  # returning a 400 error rather than a 500 Internal Server Error.

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @boundary
  Scenario: Create order with totalAmount exceeding NUMERIC(12,2) precision limit should return 400 not 500

    # Business rule: The orders.total_amount column is NUMERIC(12,2), supporting a maximum
    # value of 9,999,999,999.99. Submitting a value of 99999999999.99 (11 digits before decimal)
    # exceeds this limit and must be rejected gracefully by the service layer.

    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-001",
        "customerTier": "STANDARD",
        "items": [
          {
            "productId": "prod-overflow",
            "quantity": 1,
            "price": 99999999999.99
          }
        ]
      }
      """
    When method POST

    # Expect a client-side error (400) indicating invalid input.
    # A 500 would indicate the service failed to validate before hitting the DB.
    Then status 400
    And match responseStatus == 400 || responseStatus == 422
    And match response != null

    # Optionally verify an error message is present in the response
    And match response.error == '#present' || response.message == '#present'

    # JDBC verification: confirm no order record was persisted for this overflow attempt
    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def conn = java.sql.DriverManager.getConnection(dbUrl, props)
    * def stmt = conn.prepareStatement("SELECT COUNT(*) AS cnt FROM orders WHERE customer_id = (SELECT id FROM customers WHERE external_id = ? LIMIT 1) AND total_amount = 99999999999.99")
    * eval stmt.setString(1, 'cust-001')
    * def rs = stmt.executeQuery()
    * eval rs.next()
    * def overflowOrderCount = rs.getInt('cnt')
    * eval rs.close()
    * eval stmt.close()
    * eval conn.close()

    # Assert that no overflow order was persisted in the database
    * match overflowOrderCount == 0

  @boundary
  Scenario Outline: Create order with various amounts near and beyond NUMERIC(12,2) boundary

    # Business rule: Validates boundary behaviour around the NUMERIC(12,2) precision limit.
    # Values at or below 9,999,999,999.99 may succeed (200/201),
    # values above must be rejected (400/422), never 500.

    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-001",
        "customerTier": "STANDARD",
        "items": [
          {
            "productId": "prod-overflow",
            "quantity": 1,
            "price": <price>
          }
        ]
      }
      """
    When method POST
    Then status <expectedStatus>
    And match responseStatus != 500

    Examples:
      | price             | expectedStatus |
      | 9999999999.99     | 201            |
      | 99999999999.99    | 400            |
      | 999999999999.99   | 400            |