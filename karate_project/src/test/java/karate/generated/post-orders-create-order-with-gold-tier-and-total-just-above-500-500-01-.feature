Feature: Create Order - GOLD Tier Boundary Discount at $500.01

  # Business Rule: GOLD tier customers receive 10% discount when total > $500
  # This feature tests the exact boundary condition where total = $500.01 (just above threshold)
  # Expected: discount_applied = 50.001, rounded to 50.00 per NUMERIC(12,2) DB precision

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @boundary @business_rule
  Scenario: Create order with GOLD tier and total just above $500 ($500.01) receives 10% discount

    # Business Rule: GOLD tier discount threshold uses strict '>' condition.
    # An order total of $500.01 is just above $500 and must trigger the 10% discount.
    # discountApplied = 500.01 * 0.10 = 50.001, stored as 50.00 per NUMERIC(12,2) precision.

    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-gold-001",
        "customerTier": "GOLD",
        "items": [
          {
            "productId": "prod-boundary",
            "quantity": 1,
            "price": 500.01
          }
        ]
      }
      """
    When method POST
    Then status 201

    # Validate top-level response fields are present and well-formed
    And match response.id == '#notnull'
    And match response.id == '#present'
    And match response.customerId == 'cust-gold-001'
    And match response.customerTier == 'GOLD'

    # Validate total amount matches the submitted order value
    And match response.totalAmount == 500.01

    # Business Rule: 10% discount applied because total ($500.01) > $500 threshold
    # 500.01 * 0.10 = 50.001 → rounded to 50.00 by NUMERIC(12,2) storage precision
    And match response.discountApplied == 50.00

    # Validate order status defaults to PENDING on creation
    And match response.status == 'PENDING'

    # Capture the created order ID for downstream DB verification
    * def createdOrderId = response.id

    # -------------------------------------------------------------------------
    # JDBC Verification: Confirm the database record reflects the correct values
    # after the API successfully created the order.
    # -------------------------------------------------------------------------

    # Establish JDBC connection using config from karate-config.js
    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def conn = java.sql.DriverManager.getConnection(dbUrl, props)

    # Query the orders table for the newly created record
    * def stmt = conn.prepareStatement("SELECT status, total_amount, discount_applied FROM orders WHERE id = ?")
    * eval stmt.setObject(1, java.util.UUID.fromString(createdOrderId))
    * def rs = stmt.executeQuery()
    * eval rs.next()

    # Verify order status was persisted as PENDING (default)
    * match rs.getString('status') == 'PENDING'

    # Verify total_amount was persisted correctly as 500.01
    * match rs.getBigDecimal('total_amount').doubleValue() == 500.01

    # Business Rule DB check: discount_applied must be 50.00 (NUMERIC(12,2) rounds 50.001)
    # This confirms the API applied the GOLD tier >$500 discount rule and the DB stored it correctly
    * match rs.getBigDecimal('discount_applied').doubleValue() == 50.00

    # Clean up JDBC resources
    * eval rs.close()
    * eval stmt.close()

    # Also verify via order_items table that the line item was persisted correctly
    * def itemStmt = conn.prepareStatement("SELECT product_id, quantity, unit_price, line_total FROM order_items WHERE order_id = ?")
    * eval itemStmt.setObject(1, java.util.UUID.fromString(createdOrderId))
    * def itemRs = itemStmt.executeQuery()
    * eval itemRs.next()

    # Verify the boundary-test product line item was stored correctly
    * match itemRs.getString('product_id') == 'prod-boundary'
    * match itemRs.getInt('quantity') == 1
    * match itemRs.getBigDecimal('unit_price').doubleValue() == 500.01
    * match itemRs.getBigDecimal('line_total').doubleValue() == 500.01

    # Clean up remaining JDBC resources
    * eval itemRs.close()
    * eval itemStmt.close()
    * eval conn.close()