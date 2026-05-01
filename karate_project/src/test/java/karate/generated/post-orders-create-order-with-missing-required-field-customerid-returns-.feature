Feature: Create Order Validation - Missing Required Field 'customerId'

  # Business Rule: POST /orders requires 'customerId' as a mandatory field.
  # The orders table enforces customer_id as NOT NULL with a FK constraint to customers.id.
  # Omitting 'customerId' must be caught at the API layer and return HTTP 400 before
  # any database write is attempted.

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @validation
  Scenario: Create order with missing required field 'customerId' returns 400

    # Business Rule: POST /orders — required fields: ['customerId', 'items']
    # Omitting 'customerId' must trigger a 400 Bad Request with a structured error body
    # containing 'code' and 'message' fields, as defined in the orders-api.yaml 400 response schema.
    # The DB constraint (customer_id NOT NULL, FK → customers.id) must never be reached.

    Given path '/orders'
    And request
      """
      {
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
    Then status 400

    # Verify the response body conforms to the 400 error schema: {code, message}
    And match response.code == '#present'
    And match response.message == '#present'
    And match response.code == '#notnull'
    And match response.message == '#notnull'

    # Verify that no order record was inserted into the database.
    # Since the request is invalid, the API layer should reject it before any DB write.
    # We confirm by checking that no row exists with the submitted item productId
    # and a recent created_at timestamp (within the last 5 seconds).
    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def conn = java.sql.DriverManager.getConnection(dbUrl, props)
    * def stmt = conn.prepareStatement("SELECT COUNT(*) AS row_count FROM orders o JOIN order_items oi ON oi.order_id = o.id WHERE oi.product_id = ? AND o.created_at >= NOW() - INTERVAL '5 seconds'")
    * eval stmt.setString(1, 'prod-A')
    * def rs = stmt.executeQuery()
    * eval rs.next()

    # Business Rule: A rejected request must not persist any order or order_items rows.
    * match rs.getInt('row_count') == 0

    * eval rs.close()
    * eval stmt.close()
    * eval conn.close()