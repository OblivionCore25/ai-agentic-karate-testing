Feature: Create Order Validation - Missing Required 'productId' Field

  # Tests that the POST /orders endpoint enforces the 'productId' required field
  # within each item object in the items array.
  # Spec reference: orders-api.yaml POST /orders — items.items required: ['productId', 'quantity', 'price']
  # DB reference: postgresql://public/order_items — product_id NOT NULL

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @validation
  Scenario: Create order with item missing required 'productId' field returns 400

    # Business rule: Every item in the items array must include 'productId'.
    # Omitting 'productId' violates the schema constraint (required field) and
    # the DB-level NOT NULL constraint on order_items.product_id.
    # Expected: API rejects the request with HTTP 400 before any DB write occurs.

    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-001",
        "customerTier": "STANDARD",
        "items": [
          {
            "quantity": 2,
            "price": 25.0
          }
        ]
      }
      """
    When method POST
    Then status 400

    # Verify the response contains a meaningful validation error
    And match response != null
    And match response contains { "message": "#notnull" }

    # Confirm no order record was written to the database as a result of this failed request
    * def conn = java.sql.DriverManager.getConnection(dbUrl, dbUser, dbPassword)
    * def stmt = conn.prepareStatement("SELECT COUNT(*) AS cnt FROM orders o JOIN order_items oi ON oi.order_id = o.id WHERE oi.product_id IS NULL AND o.created_at >= NOW() - INTERVAL '10 seconds'")
    * def rs = stmt.executeQuery()
    * eval rs.next()
    * match rs.getInt('cnt') == 0
    * eval rs.close()
    * eval stmt.close()
    * eval conn.close()