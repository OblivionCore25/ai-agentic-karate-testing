Feature: Create Order with Zero Price (Free Item)

  # Business Rule: The order_items table has a CHECK constraint unit_price >= 0,
  # meaning a price of exactly 0.00 is valid. This test verifies that free or
  # promotional items can be included in an order and result in HTTP 201.

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @boundary @happy_path
  Scenario: Create order with item price of zero is accepted (free item)
    # Business Rule: unit_price >= 0 (order_items_unit_price_check constraint)
    # A price of exactly 0.00 must be accepted, enabling free/promotional items.
    # Expected: HTTP 201, order created with total_amount = 0.00 and discount_applied = 0.00

    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-001",
        "customerTier": "STANDARD",
        "items": [
          {
            "productId": "prod-free",
            "quantity": 1,
            "price": 0.00
          }
        ]
      }
      """
    When method POST
    Then status 201

    # Verify response structure and values
    And match response.id == '#notnull'
    And match response.id == '#present'
    And match response.customerId == 'cust-001'
    And match response.status == 'PENDING'
    And match response.totalAmount == 0.0
    And match response.discountApplied == 0.0
    And match response.items == '#[1]'
    And match response.items[0].productId == 'prod-free'
    And match response.items[0].quantity == 1
    And match response.items[0].price == 0.0

    # JDBC Verification: Confirm the order record was persisted correctly in the database
    * def orderId = response.id

    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def conn = java.sql.DriverManager.getConnection(dbUrl, props)

    # Verify the orders table record
    * def stmtOrders = conn.prepareStatement("SELECT status, total_amount, discount_applied FROM orders WHERE id = ?")
    * eval stmtOrders.setObject(1, java.util.UUID.fromString(orderId))
    * def rsOrders = stmtOrders.executeQuery()
    * eval rsOrders.next()
    * match rsOrders.getString('status') == 'PENDING'
    * match rsOrders.getBigDecimal('total_amount').doubleValue() == 0.0
    * match rsOrders.getBigDecimal('discount_applied').doubleValue() == 0.0
    * eval rsOrders.close()
    * eval stmtOrders.close()

    # Verify the order_items table record — unit_price must be 0.00 (satisfies unit_price >= 0 constraint)
    * def stmtItems = conn.prepareStatement("SELECT product_id, quantity, unit_price, line_total FROM order_items WHERE order_id = ?")
    * eval stmtItems.setObject(1, java.util.UUID.fromString(orderId))
    * def rsItems = stmtItems.executeQuery()
    * eval rsItems.next()
    * match rsItems.getString('product_id') == 'prod-free'
    * match rsItems.getInt('quantity') == 1
    * match rsItems.getBigDecimal('unit_price').doubleValue() == 0.0
    * match rsItems.getBigDecimal('line_total').doubleValue() == 0.0
    * eval rsItems.close()
    * eval stmtItems.close()

    # Verify the order_summary view reflects the free item order correctly
    * def stmtSummary = conn.prepareStatement("SELECT total_amount, discount_applied, final_amount, item_count FROM order_summary WHERE order_id = ?")
    * eval stmtSummary.setObject(1, java.util.UUID.fromString(orderId))
    * def rsSummary = stmtSummary.executeQuery()
    * eval rsSummary.next()
    * match rsSummary.getBigDecimal('total_amount').doubleValue() == 0.0
    * match rsSummary.getBigDecimal('discount_applied').doubleValue() == 0.0
    * match rsSummary.getLong('item_count') == 1
    * eval rsSummary.close()
    * eval stmtSummary.close()

    * eval conn.close()