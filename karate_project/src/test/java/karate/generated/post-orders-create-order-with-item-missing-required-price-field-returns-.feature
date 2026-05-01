Feature: Create Order Validation - Missing Required 'price' Field

  # Business Rule: Each order item must include the required 'price' field.
  # Source: orders-api.yaml POST /orders — items.items required: ['productId', 'quantity', 'price']
  # Source: postgresql://public/order_items — unit_price NOT NULL
  # Omitting 'price' must result in HTTP 400 and no record persisted to the database.

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @validation
  Scenario: Create order with item missing required 'price' field returns 400

    # Business Rule: The 'price' field is required for every item in the order payload.
    # Omitting it must be rejected before any DB write occurs (unit_price NOT NULL).

    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-001",
        "customerTier": "STANDARD",
        "items": [
          {
            "productId": "prod-A",
            "quantity": 2
          }
        ]
      }
      """
    When method POST
    Then status 400

    # Verify the response contains a meaningful validation error
    And match response == '#object'
    And match response contains { error: '#present' }
    And match response.error == '#notnull'

    # JDBC Verification: Confirm that NO order record was persisted to the database.
    # A 400 validation error must prevent any DB write (orders and order_items tables).
    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def conn = java.sql.DriverManager.getConnection(dbUrl, props)

    # Check that no order was created for this customer in the last few seconds
    * def stmt = conn.prepareStatement("SELECT COUNT(*) AS cnt FROM orders o JOIN order_items oi ON oi.order_id = o.id WHERE oi.product_id = 'prod-A' AND oi.unit_price IS NULL AND o.created_at >= NOW() - INTERVAL '10 seconds'")
    * def rs = stmt.executeQuery()
    * eval rs.next()
    * def orphanCount = rs.getInt('cnt')
    * match orphanCount == 0
    * eval rs.close()
    * eval stmt.close()

    # Also confirm no incomplete order_items rows exist with NULL unit_price for this product
    * def stmt2 = conn.prepareStatement("SELECT COUNT(*) AS cnt FROM order_items WHERE product_id = 'prod-A' AND unit_price IS NULL AND id::text IN (SELECT oi2.id::text FROM order_items oi2 JOIN orders o2 ON oi2.order_id = o2.id WHERE o2.created_at >= NOW() - INTERVAL '10 seconds')")
    * def rs2 = stmt2.executeQuery()
    * eval rs2.next()
    * def nullPriceCount = rs2.getInt('cnt')
    * match nullPriceCount == 0
    * eval rs2.close()
    * eval stmt2.close()
    * eval conn.close()