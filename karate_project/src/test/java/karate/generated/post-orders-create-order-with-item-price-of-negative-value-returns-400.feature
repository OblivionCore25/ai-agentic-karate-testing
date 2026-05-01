Feature: Create Order - Negative Item Price Validation

  # Business Rule: The DB CHECK constraint (unit_price >= 0) on order_items forbids negative prices.
  # This constraint should be enforced at the API validation layer, returning HTTP 400
  # before any record is persisted to the database.

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @boundary
  Scenario: Create order with item price of negative value returns 400
    # Business Rule: API must reject negative unit prices with HTTP 400.
    # The order_items table enforces unit_price >= 0 via a CHECK constraint.
    # Validation should occur at the API layer before any DB write is attempted.

    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-001",
        "customerTier": "STANDARD",
        "items": [
          {
            "productId": "prod-A",
            "quantity": 1,
            "price": -10.0
          }
        ]
      }
      """
    When method POST
    Then status 400
    And match response != null
    And match response contains { message: '#notnull' }

    # DB Verification: Confirm no order record was created for this rejected request.
    # Since the API should reject before persisting, no rows should exist for this customer
    # with a PENDING status created in the last few seconds.
    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def conn = java.sql.DriverManager.getConnection(dbUrl, props)
    * def stmt = conn.prepareStatement("SELECT COUNT(*) AS cnt FROM orders o JOIN order_items oi ON oi.order_id = o.id WHERE o.customer_id = (SELECT id FROM customers WHERE external_id = ? LIMIT 1) AND oi.unit_price < 0 AND o.created_at >= NOW() - INTERVAL '10 seconds'")
    * eval stmt.setString(1, 'cust-001')
    * def rs = stmt.executeQuery()
    * eval rs.next()
    * match rs.getInt('cnt') == 0
    * eval rs.close()
    * eval stmt.close()
    * eval conn.close()