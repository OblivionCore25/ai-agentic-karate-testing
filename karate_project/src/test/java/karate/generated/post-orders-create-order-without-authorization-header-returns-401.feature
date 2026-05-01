Feature: Create Order Security - Authorization Header Enforcement

  # Business Rule: The POST /orders endpoint requires Bearer token authentication.
  # Requests without an Authorization header must be rejected with HTTP 401 Unauthorized.
  # Source: orders-api.yaml — POST /orders, Authentication: http (bearer), 401 response

  Background:
    * url baseUrl
    * header Content-Type = 'application/json'

  @security
  Scenario: Create order without Authorization header returns 401

    # Business Rule: Bearer token authentication is mandatory for all order creation requests.
    # Omitting the Authorization header entirely must result in a 401 Unauthorized response.
    # The server must not process the request or create any order record.

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
    Then status 401

    # Verify that no order record was created in the database as a result of this rejected request
    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def conn = java.sql.DriverManager.getConnection(dbUrl, props)
    * def stmt = conn.prepareStatement("SELECT COUNT(*) AS order_count FROM orders WHERE customer_id = (SELECT id FROM customers WHERE external_id = ? LIMIT 1)")
    * eval stmt.setString(1, 'cust-001')
    * def rs = stmt.executeQuery()
    * eval rs.next()
    * def orderCount = rs.getInt('order_count')
    * match orderCount == 0
    * eval rs.close()
    * eval stmt.close()
    * eval conn.close()