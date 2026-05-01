Feature: Create Order - SILVER Tier Customer Discount Exclusion

  # Business Rule: GOLD tier discount (10% when total > $500) must NOT apply to SILVER tier customers.
  # Even when a SILVER tier customer's order total exceeds $500, discountApplied must remain 0.00.
  # Source: postgresql://public/orders — "GOLD tier customers receive 10% discount when total > $500"
  # Source: data/sample_specs/orders-api.yaml — customerTier enum includes SILVER as a distinct tier

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @business_rule
  Scenario: Create order for SILVER tier customer with total above $500 receives no discount

    # Business Rule Under Test:
    # The 10% discount is exclusively for GOLD tier customers with order total > $500.
    # A SILVER tier customer ordering $800 worth of goods must receive discountApplied = 0.00.
    # This guards against accidental tier promotion or discount logic bleed-through.

    * def orderRequest =
      """
      {
        "customerId": "cust-silver-001",
        "customerTier": "SILVER",
        "items": [
          {
            "productId": "prod-004",
            "quantity": 2,
            "price": 400.00
          }
        ]
      }
      """

    Given path '/orders'
    And request orderRequest
    When method POST
    Then status 201

    # Verify the response confirms no discount was applied
    And match response.customerId == 'cust-silver-001'
    And match response.customerTier == 'SILVER'
    And match response.totalAmount == 800.00
    And match response.discountApplied == 0.00
    And match response.id == '#notnull'
    And match response.status == '#notnull'

    # Capture the created order ID for database verification
    * def createdOrderId = response.id

    # JDBC Verification: Confirm the database record reflects no discount for SILVER tier
    # Verifying against: postgresql://public/orders (discount_applied column)
    # Also cross-checking: postgresql://public/order_summary (customer_tier, discount_applied)
    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def conn = java.sql.DriverManager.getConnection(dbUrl, props)

    # Verify orders table: discount_applied must be 0.00 and total_amount must be 800.00
    * def stmt = conn.prepareStatement("SELECT status, total_amount, discount_applied FROM orders WHERE id = ?")
    * eval stmt.setObject(1, java.util.UUID.fromString(createdOrderId))
    * def rs = stmt.executeQuery()
    * eval rs.next()
    * match rs.getString('status') == 'PENDING'
    * match rs.getBigDecimal('total_amount').doubleValue() == 800.00
    * match rs.getBigDecimal('discount_applied').doubleValue() == 0.00
    * eval rs.close()
    * eval stmt.close()

    # Verify order_summary view: customer_tier must be SILVER and discount_applied must be 0.00
    * def stmtSummary = conn.prepareStatement("SELECT customer_tier, total_amount, discount_applied, final_amount FROM order_summary WHERE order_id = ?")
    * eval stmtSummary.setObject(1, java.util.UUID.fromString(createdOrderId))
    * def rsSummary = stmtSummary.executeQuery()
    * eval rsSummary.next()
    * match rsSummary.getString('customer_tier') == 'SILVER'
    * match rsSummary.getBigDecimal('total_amount').doubleValue() == 800.00
    * match rsSummary.getBigDecimal('discount_applied').doubleValue() == 0.00
    * match rsSummary.getBigDecimal('final_amount').doubleValue() == 800.00
    * eval rsSummary.close()
    * eval stmtSummary.close()

    # Verify order_items table: line item was persisted correctly
    * def stmtItems = conn.prepareStatement("SELECT product_id, quantity, unit_price, line_total FROM order_items WHERE order_id = ?")
    * eval stmtItems.setObject(1, java.util.UUID.fromString(createdOrderId))
    * def rsItems = stmtItems.executeQuery()
    * eval rsItems.next()
    * match rsItems.getString('product_id') == 'prod-004'
    * match rsItems.getInt('quantity') == 2
    * match rsItems.getBigDecimal('unit_price').doubleValue() == 400.00
    * match rsItems.getBigDecimal('line_total').doubleValue() == 800.00
    * eval rsItems.close()
    * eval stmtItems.close()

    * eval conn.close()