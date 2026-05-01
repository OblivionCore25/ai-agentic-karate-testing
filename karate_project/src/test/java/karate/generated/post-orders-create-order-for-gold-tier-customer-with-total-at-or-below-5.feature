Feature: Create Order - GOLD Tier Boundary Condition (No Discount at $500)

  # Business Rule: GOLD tier customers receive 10% discount ONLY when total > $500.
  # This feature tests the strict inequality boundary: an order totalling exactly $500
  # should NOT receive any discount (discountApplied = 0.00).

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @business_rule
  Scenario: Create order for GOLD tier customer with total exactly $500 receives no discount
    # Business Rule: Discount applies only when total > $500 (strict inequality).
    # At exactly $500, the condition is NOT met, so discountApplied must be 0.00.
    # Customer: cust-gold-001 (GOLD tier), 1x prod-002 @ $500.00 = $500.00 total.

    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-gold-001",
        "customerTier": "GOLD",
        "items": [
          {
            "productId": "prod-002",
            "quantity": 1,
            "price": 500.00
          }
        ]
      }
      """
    When method POST
    Then status 201

    # Verify response fields: no discount should be applied at the $500 boundary
    And match response.discountApplied == 0.00
    And match response.totalAmount == 500.00
    And match response.id == '#notnull'
    And match response.status == '#present'

    # JDBC Verification: Confirm the order was persisted correctly in the database
    # and that no discount was recorded for this boundary-condition order.
    * def orderId = response.id
    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def conn = java.sql.DriverManager.getConnection(dbUrl, props)

    # Verify orders table: discount_applied = 0.00 and total_amount = 500.00
    * def stmt = conn.prepareStatement("SELECT total_amount, discount_applied, status FROM orders WHERE id = ?")
    * eval stmt.setObject(1, java.util.UUID.fromString(orderId))
    * def rs = stmt.executeQuery()
    * eval rs.next()
    * match rs.getBigDecimal('total_amount').doubleValue() == 500.00
    * match rs.getBigDecimal('discount_applied').doubleValue() == 0.00
    * match rs.getString('status') == 'PENDING'
    * eval rs.close()
    * eval stmt.close()

    # Verify order_items table: one line item for prod-002 with correct quantity and price
    * def itemStmt = conn.prepareStatement("SELECT product_id, quantity, unit_price, line_total FROM order_items WHERE order_id = ?")
    * eval itemStmt.setObject(1, java.util.UUID.fromString(orderId))
    * def itemRs = itemStmt.executeQuery()
    * eval itemRs.next()
    * match itemRs.getString('product_id') == 'prod-002'
    * match itemRs.getInt('quantity') == 1
    * match itemRs.getBigDecimal('unit_price').doubleValue() == 500.00
    * match itemRs.getBigDecimal('line_total').doubleValue() == 500.00
    * eval itemRs.close()
    * eval itemStmt.close()

    # Verify order_summary view: confirms denormalized view reflects correct tier and discount
    * def summaryStmt = conn.prepareStatement("SELECT customer_tier, total_amount, discount_applied FROM order_summary WHERE order_id = ?")
    * eval summaryStmt.setObject(1, java.util.UUID.fromString(orderId))
    * def summaryRs = summaryStmt.executeQuery()
    * eval summaryRs.next()
    * match summaryRs.getString('customer_tier') == 'GOLD'
    * match summaryRs.getBigDecimal('total_amount').doubleValue() == 500.00
    * match summaryRs.getBigDecimal('discount_applied').doubleValue() == 0.00
    * eval summaryRs.close()
    * eval summaryStmt.close()
    * eval conn.close()