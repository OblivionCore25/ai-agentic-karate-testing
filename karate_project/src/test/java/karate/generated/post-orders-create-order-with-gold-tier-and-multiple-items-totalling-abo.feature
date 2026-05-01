Feature: Create Order - GOLD Tier Discount on Aggregated Total Above $500

  # Business Rule: GOLD tier customers receive a 10% discount when the aggregated order total exceeds $500.
  # This feature verifies that the discount is applied to the full order total (not per-item),
  # and that multiple items are correctly summed before the discount threshold is evaluated.

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @business_rule
  Scenario: Create order with GOLD tier and multiple items totalling above $500 receives correct 10% discount on full total

    # Business Rule: GOLD tier customers receive 10% discount when total > $500.
    # Two items: prod-A (2 x $150 = $300) + prod-B (1 x $250 = $250) = $550 total.
    # Expected discount: 10% of $550 = $55.00 applied to the full aggregated total.

    * def orderRequest =
      """
      {
        "customerId": "cust-gold-001",
        "customerTier": "GOLD",
        "items": [
          {
            "productId": "prod-A",
            "quantity": 2,
            "price": 150.0
          },
          {
            "productId": "prod-B",
            "quantity": 1,
            "price": 250.0
          }
        ]
      }
      """

    Given path '/orders'
    And request orderRequest
    When method POST
    Then status 201

    # Verify the response contains the correct order metadata
    And match response.id == '#notnull'
    And match response.customerId == 'cust-gold-001'
    And match response.status == '#present'

    # Verify the aggregated total is $550 (sum of all line items)
    And match response.totalAmount == 550.0

    # Verify the 10% GOLD discount is applied to the full aggregated total ($550 * 10% = $55)
    And match response.discountApplied == 55.0

    # Verify the final amount reflects the discount ($550 - $55 = $495)
    And match response.finalAmount == 495.0

    # Verify the items array is present and contains both submitted items
    And match response.items == '#[2]'
    And match response.items contains deep { "productId": "prod-A", "quantity": 2 }
    And match response.items contains deep { "productId": "prod-B", "quantity": 1 }

    # --- JDBC Database Verification ---
    # Confirm the order was persisted correctly in the orders table with the right discount

    * def orderId = response.id

    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def conn = java.sql.DriverManager.getConnection(dbUrl, props)

    # Verify the orders table has the correct total_amount and discount_applied
    * def stmtOrders = conn.prepareStatement("SELECT status, total_amount, discount_applied FROM orders WHERE id = ?")
    * eval stmtOrders.setObject(1, java.util.UUID.fromString(orderId))
    * def rsOrders = stmtOrders.executeQuery()
    * eval rsOrders.next()
    * match rsOrders.getString('status') == 'PENDING'
    * match rsOrders.getBigDecimal('total_amount').doubleValue() == 550.0
    * match rsOrders.getBigDecimal('discount_applied').doubleValue() == 55.0
    * eval rsOrders.close()
    * eval stmtOrders.close()

    # Verify both line items were persisted in order_items table
    * def stmtItems = conn.prepareStatement("SELECT COUNT(*) AS item_count FROM order_items WHERE order_id = ?")
    * eval stmtItems.setObject(1, java.util.UUID.fromString(orderId))
    * def rsItems = stmtItems.executeQuery()
    * eval rsItems.next()
    * match rsItems.getInt('item_count') == 2
    * eval rsItems.close()
    * eval stmtItems.close()

    # Verify prod-A line item: quantity=2, unit_price=150.00, line_total=300.00
    * def stmtProdA = conn.prepareStatement("SELECT quantity, unit_price, line_total FROM order_items WHERE order_id = ? AND product_id = ?")
    * eval stmtProdA.setObject(1, java.util.UUID.fromString(orderId))
    * eval stmtProdA.setString(2, 'prod-A')
    * def rsProdA = stmtProdA.executeQuery()
    * eval rsProdA.next()
    * match rsProdA.getInt('quantity') == 2
    * match rsProdA.getBigDecimal('unit_price').doubleValue() == 150.0
    * match rsProdA.getBigDecimal('line_total').doubleValue() == 300.0
    * eval rsProdA.close()
    * eval stmtProdA.close()

    # Verify prod-B line item: quantity=1, unit_price=250.00, line_total=250.00
    * def stmtProdB = conn.prepareStatement("SELECT quantity, unit_price, line_total FROM order_items WHERE order_id = ? AND product_id = ?")
    * eval stmtProdB.setObject(1, java.util.UUID.fromString(orderId))
    * eval stmtProdB.setString(2, 'prod-B')
    * def rsProdB = stmtProdB.executeQuery()
    * eval rsProdB.next()
    * match rsProdB.getInt('quantity') == 1
    * match rsProdB.getBigDecimal('unit_price').doubleValue() == 250.0
    * match rsProdB.getBigDecimal('line_total').doubleValue() == 250.0
    * eval rsProdB.close()
    * eval stmtProdB.close()

    # Verify the order_summary view reflects the correct denormalized state
    * def stmtSummary = conn.prepareStatement("SELECT customer_tier, total_amount, discount_applied, final_amount, item_count FROM order_summary WHERE order_id = ?")
    * eval stmtSummary.setObject(1, java.util.UUID.fromString(orderId))
    * def rsSummary = stmtSummary.executeQuery()
    * eval rsSummary.next()
    * match rsSummary.getString('customer_tier') == 'GOLD'
    * match rsSummary.getBigDecimal('total_amount').doubleValue() == 550.0
    * match rsSummary.getBigDecimal('discount_applied').doubleValue() == 55.0
    * match rsSummary.getBigDecimal('final_amount').doubleValue() == 495.0
    * match rsSummary.getLong('item_count') == 2
    * eval rsSummary.close()
    * eval stmtSummary.close()

    * eval conn.close()