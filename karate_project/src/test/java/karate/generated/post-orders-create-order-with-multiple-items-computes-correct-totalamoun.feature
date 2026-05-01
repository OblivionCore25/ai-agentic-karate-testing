Feature: Create Order - Multiple Items Total Amount Calculation

  # Tests that the service layer correctly aggregates line totals (quantity * price)
  # into the totalAmount field when multiple items are submitted in a single order.
  # Business Rule: totalAmount = sum of (quantity * price) for each line item.
  # Reference: orders-api.yaml POST /orders — items array and totalAmount in 201 response schema

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @happy_path
  Scenario: Create order with multiple items computes correct totalAmount

    # Business Rule: totalAmount must equal the sum of all (quantity * price) across all line items.
    # Test Data:
    #   prod-A: 2 * 50.00 = 100.00
    #   prod-B: 3 * 30.00 =  90.00
    #   prod-C: 1 * 20.00 =  20.00
    #   Expected totalAmount = 210.00
    # Preconditions: customer cust-001 exists in the customers table; STANDARD tier (no discount applies)

    * def requestBody =
      """
      {
        "customerId": "cust-001",
        "customerTier": "STANDARD",
        "items": [
          {
            "productId": "prod-A",
            "quantity": 2,
            "price": 50.0
          },
          {
            "productId": "prod-B",
            "quantity": 3,
            "price": 30.0
          },
          {
            "productId": "prod-C",
            "quantity": 1,
            "price": 20.0
          }
        ]
      }
      """

    Given path '/orders'
    And request requestBody
    When method POST
    Then status 201

    # Verify the response contains a valid order id and correct computed totalAmount
    And match response.id == '#notnull'
    And match response.id == '#present'
    And match response.totalAmount == 210.0
    And match response.discountApplied == 0.0
    And match response.status == 'PENDING'
    And match response.customerId == 'cust-001'

    # Verify all three line items are reflected in the response
    And match response.items == '#[3]'
    And match response.items contains deep { "productId": "prod-A", "quantity": 2, "price": 50.0 }
    And match response.items contains deep { "productId": "prod-B", "quantity": 3, "price": 30.0 }
    And match response.items contains deep { "productId": "prod-C", "quantity": 1, "price": 20.0 }

    # Capture the created order id for database verification
    * def orderId = response.id

    # --- JDBC Verification: Confirm orders table reflects correct totalAmount and discount ---
    # Business Rule: STANDARD tier with total $210 should have discount_applied = 0.00
    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def conn = java.sql.DriverManager.getConnection(dbUrl, props)

    # Verify the orders record
    * def stmtOrders = conn.prepareStatement("SELECT status, total_amount, discount_applied FROM orders WHERE id = ?")
    * eval stmtOrders.setObject(1, java.util.UUID.fromString(orderId))
    * def rsOrders = stmtOrders.executeQuery()
    * eval rsOrders.next()
    * match rsOrders.getString('status') == 'PENDING'
    * match rsOrders.getBigDecimal('total_amount').doubleValue() == 210.0
    * match rsOrders.getBigDecimal('discount_applied').doubleValue() == 0.0
    * eval rsOrders.close()
    * eval stmtOrders.close()

    # --- JDBC Verification: Confirm order_items table has 3 rows with correct line_total values ---
    # Business Rule: line_total is auto-computed as quantity * unit_price per order_items schema
    * def stmtItems = conn.prepareStatement("SELECT product_id, quantity, unit_price, line_total FROM order_items WHERE order_id = ? ORDER BY product_id")
    * eval stmtItems.setObject(1, java.util.UUID.fromString(orderId))
    * def rsItems = stmtItems.executeQuery()

    # Verify prod-A: quantity=2, unit_price=50.00, line_total=100.00
    * eval rsItems.next()
    * match rsItems.getString('product_id') == 'prod-A'
    * match rsItems.getInt('quantity') == 2
    * match rsItems.getBigDecimal('unit_price').doubleValue() == 50.0
    * match rsItems.getBigDecimal('line_total').doubleValue() == 100.0

    # Verify prod-B: quantity=3, unit_price=30.00, line_total=90.00
    * eval rsItems.next()
    * match rsItems.getString('product_id') == 'prod-B'
    * match rsItems.getInt('quantity') == 3
    * match rsItems.getBigDecimal('unit_price').doubleValue() == 30.0
    * match rsItems.getBigDecimal('line_total').doubleValue() == 90.0

    # Verify prod-C: quantity=1, unit_price=20.00, line_total=20.00
    * eval rsItems.next()
    * match rsItems.getString('product_id') == 'prod-C'
    * match rsItems.getInt('quantity') == 1
    * match rsItems.getBigDecimal('unit_price').doubleValue() == 20.0
    * match rsItems.getBigDecimal('line_total').doubleValue() == 20.0

    * eval rsItems.close()
    * eval stmtItems.close()

    # --- JDBC Verification: Confirm order_summary view reflects aggregated totals ---
    * def stmtSummary = conn.prepareStatement("SELECT total_amount, discount_applied, final_amount, item_count, customer_tier FROM order_summary WHERE order_id = ?")
    * eval stmtSummary.setObject(1, java.util.UUID.fromString(orderId))
    * def rsSummary = stmtSummary.executeQuery()
    * eval rsSummary.next()
    * match rsSummary.getBigDecimal('total_amount').doubleValue() == 210.0
    * match rsSummary.getBigDecimal('discount_applied').doubleValue() == 0.0
    * match rsSummary.getLong('item_count') == 3
    * match rsSummary.getString('customer_tier') == 'STANDARD'
    * eval rsSummary.close()
    * eval stmtSummary.close()

    # Close the database connection
    * eval conn.close()