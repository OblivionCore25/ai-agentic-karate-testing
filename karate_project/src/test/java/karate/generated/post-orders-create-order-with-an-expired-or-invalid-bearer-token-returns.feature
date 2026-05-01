Feature: Create Order Security - Invalid Bearer Token

  # Business Rule: The POST /orders endpoint requires a valid Bearer token for authentication.
  # An invalid, malformed, or expired JWT/Bearer token must be rejected with HTTP 401 Unauthorized.
  # This prevents unauthorized order creation and protects customer and order data.

  Background:
    * url baseUrl
    * header Content-Type = 'application/json'

  @security
  Scenario: Create order with an expired or invalid Bearer token returns 401

    # Business Rule: Bearer token authentication is enforced on POST /orders.
    # A malformed or expired token must not allow order creation and must return 401 Unauthorized.

    # Set an invalid/expired Bearer token — this should be rejected by the auth layer
    * header Authorization = 'Bearer invalid-token-xyz'

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
            "price": 49.99
          }
        ]
      }
      """
    When method POST

    # The server must reject the request with 401 Unauthorized
    Then status 401

    # Verify the response indicates an authentication failure
    And match response == '#notnull'

    # JDBC Verification: Confirm that NO order record was inserted into the database
    # when authentication fails — the request must be rejected before any data is persisted.
    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def conn = java.sql.DriverManager.getConnection(dbUrl, props)
    * def stmt = conn.prepareStatement("SELECT COUNT(*) AS order_count FROM orders WHERE customer_id = (SELECT id FROM customers WHERE external_id = ? LIMIT 1)")
    * eval stmt.setString(1, 'cust-001')
    * def rs = stmt.executeQuery()
    * eval rs.next()

    # No order should have been created due to the authentication failure
    * def orderCount = rs.getInt('order_count')
    * match orderCount == 0

    * eval rs.close()
    * eval stmt.close()
    * eval conn.close()