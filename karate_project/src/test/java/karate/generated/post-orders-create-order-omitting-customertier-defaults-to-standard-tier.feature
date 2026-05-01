Feature: Create Order - Default Customer Tier Business Rule

  # Business Rule: When customerTier is omitted from the request, the API defaults to STANDARD tier.
  # STANDARD tier customers receive no discount regardless of order size.
  # Source: orders-api.yaml POST /orders — customerTier default: 'STANDARD'
  # Source: postgresql://public/orders — discount_applied DEFAULT 0.00, status DEFAULT 'PENDING'

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @business_rule
  Scenario: Create order omitting customerTier defaults to STANDARD tier with no discount applied

    # Business Rule: Omitting customerTier should cause the API to apply the STANDARD tier default.
    # A large order (5 x $200 = $1000 total) under STANDARD tier must yield discountApplied = 0.00.
    # This confirms the default tier is not GOLD (which would grant a 10% discount on orders > $500).

    * def orderRequest =
      """
      {
        "customerId": "cust-std-002",
        "items": [
          {
            "productId": "prod-005",
            "quantity": 5,
            "price": 200.00
          }
        ]
      }
      """

    Given path '/orders'
    And request orderRequest
    When method POST
    Then status 201

    # Verify response reflects STANDARD tier defaults: no discount, PENDING status
    And match response.discountApplied == 0.00
    And match response.status == 'PENDING'
    And match response.id == '#notnull'
    And match response.id == '#present'

    # Verify the total amount reflects the full order value (5 x $200 = $1000) with no discount
    And match response.totalAmount == '#notnull'

    # JDBC Verification: Confirm the database record reflects correct defaults
    # Verifies: discount_applied DEFAULT 0.00 and status DEFAULT 'PENDING' in public.orders table
    * def orderId = response.id

    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def conn = java.sql.DriverManager.getConnection(dbUrl, props)

    # Query the orders table to verify discount_applied and status defaults were persisted
    * def stmt = conn.prepareStatement("SELECT status, discount_applied, total_amount FROM orders WHERE id = ?")
    * eval stmt.setObject(1, java.util.UUID.fromString(orderId))
    * def rs = stmt.executeQuery()
    * eval rs.next()

    # Business Rule assertion: STANDARD tier — no discount applied
    * match rs.getString('status') == 'PENDING'
    * match rs.getBigDecimal('discount_applied').doubleValue() == 0.00

    # Verify total_amount stored matches expected full price (no discount deducted)
    * match rs.getBigDecimal('total_amount').doubleValue() == 1000.00

    * eval rs.close()
    * eval stmt.close()
    * eval conn.close()

    # Cross-check via order_summary view to confirm customer_tier was stored as STANDARD
    * def props2 = new java.util.Properties()
    * eval props2.setProperty('user', dbUser)
    * eval props2.setProperty('password', dbPassword)
    * def conn2 = java.sql.DriverManager.getConnection(dbUrl, props2)

    * def stmt2 = conn2.prepareStatement("SELECT customer_tier, discount_applied, status FROM order_summary WHERE order_id = ?")
    * eval stmt2.setObject(1, java.util.UUID.fromString(orderId))
    * def rs2 = stmt2.executeQuery()
    * eval rs2.next()

    # Business Rule assertion: default tier must be STANDARD (not GOLD or PREMIUM)
    * match rs2.getString('customer_tier') == 'STANDARD'
    * match rs2.getBigDecimal('discount_applied').doubleValue() == 0.00
    * match rs2.getString('status') == 'PENDING'

    * eval rs2.close()
    * eval stmt2.close()
    * eval conn2.close()