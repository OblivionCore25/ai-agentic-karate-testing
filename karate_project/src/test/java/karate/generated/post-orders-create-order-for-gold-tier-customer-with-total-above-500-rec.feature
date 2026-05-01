Feature: Create Order - GOLD Tier Customer Discount Business Rule

  # Business Rule: GOLD tier customers receive a 10% discount when order total exceeds $500.
  # Source: postgresql://public/orders — DB comment on discount_applied column
  # Source: data/sample_specs/orders-api.yaml — POST /orders discountApplied response field

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @business_rule @happy_path
  Scenario: Create order for GOLD tier customer with total above $500 receives 10% discount
    # Business Rule: GOLD tier + total > $500 => discountApplied = totalAmount * 0.10
    # Test Data: 2 x $300.00 items => totalAmount = $600.00, expectedDiscount = $60.00

    * def orderRequest =
      """
      {
        "customerId": "cust-gold-001",
        "customerTier": "GOLD",
        "items": [
          {
            "productId": "prod-001",
            "quantity": 2,
            "price": 300.00
          }
        ]
      }
      """

    Given path '/orders'
    And request orderRequest
    When method POST
    Then status 201

    # Verify top-level response fields are present and correctly typed
    And match response.id == '#notnull'
    And match response.id == '#present'
    And match response.status == 'PENDING'
    And match response.totalAmount == 600.00
    # Core business rule assertion: discountApplied must equal 10% of totalAmount
    And match response.discountApplied == 60.00
    And match response.customerId == 'cust-gold-001'
    And match response.customerTier == 'GOLD'

    # Capture the created order ID for DB verification
    * def createdOrderId = response.id

    # -------------------------------------------------------------------------
    # JDBC Verification: Confirm the discount was correctly persisted in the DB
    # Table: public.orders — columns: id, status, total_amount, discount_applied
    # -------------------------------------------------------------------------
    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def conn = java.sql.DriverManager.getConnection(dbUrl, props)

    # Verify orders table: status, total_amount, and discount_applied
    * def stmt = conn.prepareStatement('SELECT status, total_amount, discount_applied FROM orders WHERE id = ?')
    * eval stmt.setObject(1, java.util.UUID.fromString(createdOrderId))
    * def rs = stmt.executeQuery()
    * eval rs.next()

    # DB column: status — should default to PENDING
    * match rs.getString('status') == 'PENDING'

    # DB column: total_amount — should be 600.00
    * match rs.getBigDecimal('total_amount').doubleValue() == 600.00

    # DB column: discount_applied — core business rule: must be 60.00 (10% of 600.00)
    * match rs.getBigDecimal('discount_applied').doubleValue() == 60.00

    * eval rs.close()
    * eval stmt.close()

    # Verify order_items table: confirm line items were persisted correctly
    * def itemStmt = conn.prepareStatement('SELECT product_id, quantity, unit_price, line_total FROM order_items WHERE order_id = ?')
    * eval itemStmt.setObject(1, java.util.UUID.fromString(createdOrderId))
    * def itemRs = itemStmt.executeQuery()
    * eval itemRs.next()

    # DB column: product_id
    * match itemRs.getString('product_id') == 'prod-001'

    # DB column: quantity — must be positive per CHECK constraint
    * match itemRs.getInt('quantity') == 2

    # DB column: unit_price
    * match itemRs.getBigDecimal('unit_price').doubleValue() == 300.00

    # DB column: line_total — auto-computed: quantity * unit_price = 600.00
    * match itemRs.getBigDecimal('line_total').doubleValue() == 600.00

    * eval itemRs.close()
    * eval itemStmt.close()
    * eval conn.close()