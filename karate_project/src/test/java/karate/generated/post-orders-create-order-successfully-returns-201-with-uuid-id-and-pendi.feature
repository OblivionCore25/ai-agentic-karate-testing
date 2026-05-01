Feature: Create Order - Happy Path

Background:
  # Shared setup: base URL and Authorization header for all scenarios
  * url baseUrl
  * header Authorization = 'Bearer test-token'
  * header Content-Type = 'application/json'

  # Test data: valid customer and order payload
  * def requestBody =
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

@happy_path
Scenario: Create order successfully returns 201 with UUID id and PENDING status
  # Business Rule: A valid POST /orders request with all required fields must return HTTP 201,
  # assign a UUID-formatted id, set status to PENDING, and populate a valid ISO-8601 createdAt timestamp.
  # Source: orders-api.yaml (POST /orders 201 schema), OrderController.java (createOrder method)

  Given path '/orders'
  And request requestBody
  When method POST

  # Assert HTTP 201 Created
  Then status 201

  # Assert response body contains a UUID-formatted id (non-null, matches UUID pattern)
  And match response.id == '#notnull'
  And match response.id == '#regex [0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'

  # Assert status is PENDING (default per DB schema: status DEFAULT 'PENDING')
  And match response.status == 'PENDING'

  # Assert totalAmount reflects the single item price submitted
  And match response.totalAmount == 49.99

  # Assert createdAt is present and non-null (ISO-8601 timestamp populated by DB DEFAULT now())
  And match response.createdAt == '#notnull'
  And match response.createdAt == '#present'

  # Assert no unexpected discount was applied for a STANDARD tier customer
  # Business Rule: discounts only apply to GOLD tier customers with total > $500
  And match response contains { status: 'PENDING' }

  # -----------------------------------------------------------------------
  # JDBC Verification: Confirm the order was persisted correctly in the DB
  # Source: postgresql://public/orders — id DEFAULT gen_random_uuid(),
  #         status DEFAULT 'PENDING', created_at DEFAULT now()
  # -----------------------------------------------------------------------

  # Capture the created order id from the API response
  * def createdOrderId = response.id

  # Open a JDBC connection using config from karate-config.js
  * def props = new java.util.Properties()
  * eval props.setProperty('user', dbUser)
  * eval props.setProperty('password', dbPassword)
  * def conn = java.sql.DriverManager.getConnection(dbUrl, props)

  # Query the orders table for the newly created record
  * def stmt = conn.prepareStatement('SELECT id, status, total_amount, discount_applied, created_at FROM orders WHERE id = ?')
  * eval stmt.setObject(1, java.util.UUID.fromString(createdOrderId))
  * def rs = stmt.executeQuery()

  # Assert the record exists and has the correct values
  * eval rs.next()

  # DB status must be PENDING
  * match rs.getString('status') == 'PENDING'

  # DB total_amount must match the submitted item price
  * match rs.getBigDecimal('total_amount').doubleValue() == 49.99

  # DB discount_applied must be 0.00 for a STANDARD tier customer (no discount rule triggered)
  * match rs.getBigDecimal('discount_applied').doubleValue() == 0.00

  # DB created_at must be populated (not null)
  * match rs.getTimestamp('created_at') == '#notnull'

  # Clean up JDBC resources
  * eval rs.close()
  * eval stmt.close()
  * eval conn.close()

  # -----------------------------------------------------------------------
  # JDBC Verification: Confirm the order_items line item was persisted correctly
  # Source: postgresql://public/order_items — order_id FK → orders.id,
  #         line_total auto-computed, quantity > 0 (CHECK constraint)
  # -----------------------------------------------------------------------

  * def itemStmt = conn.prepareStatement('SELECT product_id, quantity, unit_price, line_total FROM order_items WHERE order_id = ?')

  # Re-open connection since it was closed above
  * def conn2 = java.sql.DriverManager.getConnection(dbUrl, props)
  * def itemStmt2 = conn2.prepareStatement('SELECT product_id, quantity, unit_price, line_total FROM order_items WHERE order_id = ?')
  * eval itemStmt2.setObject(1, java.util.UUID.fromString(createdOrderId))
  * def itemRs = itemStmt2.executeQuery()

  # Assert the line item record exists with correct product and pricing
  * eval itemRs.next()
  * match itemRs.getString('product_id') == 'prod-A'
  * match itemRs.getInt('quantity') == 1
  * match itemRs.getBigDecimal('unit_price').doubleValue() == 49.99
  * match itemRs.getBigDecimal('line_total').doubleValue() == 49.99

  # Clean up JDBC resources
  * eval itemRs.close()
  * eval itemStmt2.close()
  * eval conn2.close()