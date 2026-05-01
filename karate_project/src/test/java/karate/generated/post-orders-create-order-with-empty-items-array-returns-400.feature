Feature: Create Order with Empty Items Array Returns 400

  # Tests the minItems: 1 constraint on the items array (orders-api.yaml POST /orders).
  # An order must have at least one line item. Submitting an empty array should be rejected
  # with HTTP 400. The order_items table also enforces NOT NULL on order_id and product_id,
  # meaning no partial record could survive even if the API allowed it.

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @boundary
  Scenario: Create order with empty items array returns 400

    # Business rule: items array must satisfy minItems: 1 (orders-api.yaml, POST /orders).
    # An order with zero line items is semantically invalid and must be rejected before
    # any persistence attempt. The order_items table (order_id NOT NULL, product_id NOT NULL)
    # would also prevent insertion of an item-less order at the DB level.

    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-001",
        "customerTier": "STANDARD",
        "items": []
      }
      """
    When method POST
    Then status 400

    # Verify the response body signals a validation error
    And match response == '#notnull'
    And match response.error == '#present'

    # DB verification: confirm that NO order record was persisted for this customer
    # as a result of the rejected request (error scenario — record must NOT exist).
    * def jdbcUrl = dbUrl
    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def conn = java.sql.DriverManager.getConnection(jdbcUrl, props)

    # Query orders table to assert no row was created for cust-001 by this failed request.
    # We scope the check to records created within the last 5 seconds to avoid false positives
    # from pre-existing test data.
    * def stmt = conn.prepareStatement("SELECT COUNT(*) AS cnt FROM orders WHERE customer_id = (SELECT id FROM customers WHERE external_id = ? LIMIT 1) AND created_at >= NOW() - INTERVAL '5 seconds'")
    * eval stmt.setString(1, 'cust-001')
    * def rs = stmt.executeQuery()
    * eval rs.next()
    * match rs.getInt('cnt') == 0

    * eval rs.close()
    * eval stmt.close()

    # Also confirm no orphaned order_items rows were created
    * def stmtItems = conn.prepareStatement("SELECT COUNT(*) AS cnt FROM order_items oi JOIN orders o ON oi.order_id = o.id JOIN customers c ON o.customer_id = c.id WHERE c.external_id = ? AND oi.id::text IN (SELECT id::text FROM order_items WHERE id IN (SELECT id FROM order_items ORDER BY (SELECT NULL) LIMIT 0))")
    # Simplified: verify order_items count for any order created in last 5 seconds is 0
    * def stmtItems2 = conn.prepareStatement("SELECT COUNT(*) AS cnt FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE created_at >= NOW() - INTERVAL '5 seconds' AND customer_id = (SELECT id FROM customers WHERE external_id = ? LIMIT 1))")
    * eval stmtItems2.setString(1, 'cust-001')
    * def rsItems = stmtItems2.executeQuery()
    * eval rsItems.next()
    * match rsItems.getInt('cnt') == 0

    * eval rsItems.close()
    * eval stmtItems2.close()
    * eval conn.close()