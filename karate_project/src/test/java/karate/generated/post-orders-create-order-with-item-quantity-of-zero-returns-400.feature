Feature: Create Order - Item Quantity Zero Boundary Validation

  # Tests the minimum quantity boundary defined in the OpenAPI spec (quantity: minimum 1)
  # and enforced by the DB CHECK constraint (order_items_quantity_check: quantity > 0).
  # Submitting quantity=0 must be rejected at the API layer before reaching the DB.

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @boundary
  Scenario: Create order with item quantity of zero returns 400

    # Business rule: quantity field has a minimum value of 1 per the OpenAPI spec.
    # A quantity of 0 is at the boundary (one below the minimum) and must be rejected
    # with HTTP 400 before any DB write occurs.

    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-001",
        "customerTier": "STANDARD",
        "items": [
          {
            "productId": "prod-A",
            "quantity": 0,
            "price": 49.99
          }
        ]
      }
      """
    When method POST
    Then status 400

    # Verify the response contains a meaningful validation error
    And match response == '#notnull'
    And match response.error == '#present'

    # DB verification: confirm no order record was inserted for this rejected request.
    # Since the request was rejected at the API layer, neither orders nor order_items
    # should contain any record associated with this attempted submission.
    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def conn = java.sql.DriverManager.getConnection(dbUrl, props)

    # Check that no order_items row with quantity=0 was persisted (DB constraint: quantity > 0)
    * def stmt = conn.prepareStatement("SELECT COUNT(*) AS cnt FROM order_items WHERE product_id = ? AND quantity = 0")
    * eval stmt.setString(1, 'prod-A')
    * def rs = stmt.executeQuery()
    * eval rs.next()
    * match rs.getInt('cnt') == 0
    * eval rs.close()
    * eval stmt.close()

    # Check that no pending order was created for this customer from this rejected request
    * def stmt2 = conn.prepareStatement("SELECT COUNT(*) AS cnt FROM orders o JOIN customers c ON o.customer_id = c.id WHERE c.id::text = (SELECT id::text FROM customers WHERE id::text = 'cust-001' LIMIT 1) AND o.created_at >= NOW() - INTERVAL '10 seconds'")
    * def rs2 = stmt2.executeQuery()
    * eval rs2.next()
    * match rs2.getInt('cnt') == 0
    * eval rs2.close()
    * eval stmt2.close()
    * eval conn.close()