Feature: Create Order - STANDARD Tier Customer Receives No Discount

  # Business Rule: The 10% discount is exclusively for GOLD tier customers with order total > $500.
  # STANDARD tier customers must never receive a discount, regardless of order total.
  # Reference: postgresql://public/orders — discount rule is tier-specific to GOLD
  # Reference: data/sample_specs/orders-api.yaml — customerTier enum: STANDARD, SILVER, GOLD

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @business_rule
  Scenario: Create order for STANDARD tier customer with total above $500 receives no discount
    # Business Rule: STANDARD tier customers are not eligible for the 10% discount,
    # even when their order total exceeds the $500 threshold that would trigger
    # the discount for GOLD tier customers. discountApplied must be 0.00.

    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-std-001",
        "customerTier": "STANDARD",
        "items": [
          {
            "productId": "prod-003",
            "quantity": 3,
            "price": 300.00
          }
        ]
      }
      """
    When method POST
    Then status 201

    # Verify response structure and discount exclusion for STANDARD tier
    And match response.discountApplied == 0.00
    And match response.totalAmount == 900.00
    And match response.customerTier == 'STANDARD'
    And match response.id == '#notnull'
    And match response.status == '#present'

    # Confirm no discount was silently applied via a final amount check
    And match response.finalAmount == 900.00

    # --- JDBC Verification: Confirm database reflects zero discount for STANDARD tier ---
    # Verify the order was persisted with discount_applied = 0.00 in the orders table
    * def orderId = response.id
    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def conn = java.sql.DriverManager.getConnection(dbUrl, props)

    # Verify orders table: discount_applied must be 0.00 regardless of total exceeding $500
    * def stmt = conn.prepareStatement("SELECT status, total_amount, discount_applied FROM orders WHERE id = ?")
    * eval stmt.setObject(1, java.util.UUID.fromString(orderId))
    * def rs = stmt.executeQuery()
    * eval rs.next()
    * match rs.getString('status') == 'PENDING'
    * match rs.getBigDecimal('total_amount').doubleValue() == 900.00
    * match rs.getBigDecimal('discount_applied').doubleValue() == 0.00
    * eval rs.close()
    * eval stmt.close()

    # Verify order_summary view also reflects zero discount for STANDARD tier
    * def stmtSummary = conn.prepareStatement("SELECT customer_tier, discount_applied, final_amount FROM order_summary WHERE order_id = ?")
    * eval stmtSummary.setObject(1, java.util.UUID.fromString(orderId))
    * def rsSummary = stmtSummary.executeQuery()
    * eval rsSummary.next()
    * match rsSummary.getString('customer_tier') == 'STANDARD'
    * match rsSummary.getBigDecimal('discount_applied').doubleValue() == 0.00
    * match rsSummary.getBigDecimal('final_amount').doubleValue() == 900.00
    * eval rsSummary.close()
    * eval stmtSummary.close()
    * eval conn.close()