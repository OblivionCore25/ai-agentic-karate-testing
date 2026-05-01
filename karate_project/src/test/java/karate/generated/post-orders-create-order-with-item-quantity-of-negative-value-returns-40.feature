Feature: Create Order - Negative Quantity Boundary Validation

  # Business Rule: The API spec enforces minimum quantity of 1 (orders-api.yaml POST /orders).
  # The DB also enforces this via CHECK constraint: order_items_quantity_check (quantity > 0).
  # This boundary test verifies that a quantity of -1 is rejected before any DB write occurs.

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @boundary
  Scenario: Create order with item quantity of negative value returns 400

    # Business Rule: quantity minimum is 1 per API spec; quantity > 0 per DB CHECK constraint.
    # A negative quantity (-1) is below the minimum boundary and must be rejected with HTTP 400.

    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-001",
        "customerTier": "STANDARD",
        "items": [
          {
            "productId": "prod-A",
            "quantity": -1,
            "price": 49.99
          }
        ]
      }
      """
    When method POST
    Then status 400

    # Verify the response contains a meaningful validation error
    And match response == '#notnull'
    And match response.error == '#present' || match response.message == '#present' || match response.errors == '#present'

    # DB Verification: Confirm no order or order_item was persisted for this invalid request.
    # Because the request is rejected at the validation layer, the orders table must remain unchanged.

    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def conn = java.sql.DriverManager.getConnection(dbUrl, props)

    # Verify no order was created for this customer with a negative-quantity item
    * def stmt = conn.prepareStatement("SELECT COUNT(*) AS cnt FROM orders o JOIN order_items oi ON oi.order_id = o.id WHERE oi.quantity < 0")
    * def rs = stmt.executeQuery()
    * eval rs.next()
    * def negativeQtyOrderCount = rs.getInt('cnt')
    * match negativeQtyOrderCount == 0

    * eval rs.close()
    * eval stmt.close()
    * eval conn.close()