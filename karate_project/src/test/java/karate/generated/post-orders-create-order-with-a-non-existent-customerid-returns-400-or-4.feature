Feature: Create Order with Non-Existent CustomerId Returns 400 or 404

  # Business Rule: orders.customer_id is a FK to customers.id.
  # Submitting a customerId that does not exist in the customers table must be rejected
  # by the API with a meaningful client error (400 or 404), not a 500 Internal Server Error.
  # Source: postgresql://public/orders — customer_id FK → customers.id ON DELETE CASCADE
  # Source: data/sample_specs/orders-api.yaml — 400 response schema: {code, message}

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @error_handling
  Scenario: Create order with a non-existent customerId returns 400 or 404 (FK violation)
    # Business Rule: Referential integrity must be enforced at the API layer.
    # A customerId that does not exist in the customers table should produce a
    # meaningful client error (400 or 404), not a 500 Internal Server Error.

    Given path '/orders'
    And request
      """
      {
        "customerId": "00000000-0000-0000-0000-000000000000",
        "customerTier": "STANDARD",
        "items": [
          {
            "productId": "prod-A",
            "quantity": 1,
            "price": 49.99
          }
        ]
      }
      """
    When method POST

    # Assert that the response is a client error (400 or 404), never a 500
    Then match responseStatus == 400 || responseStatus == 404

    # Assert the response body contains a meaningful error structure
    # per the orders-api.yaml 400 response schema: {code, message}
    And match response.code == '#notnull'
    And match response.message == '#notnull'
    And match response.message == '#present'

    # Assert the response is definitely not a 500 Internal Server Error
    And match responseStatus != 500

    # JDBC Verification: Confirm no order record was inserted into the database
    # for the non-existent customerId (referential integrity enforced at DB level too)
    * def jdbcUrl = dbUrl
    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def conn = java.sql.DriverManager.getConnection(jdbcUrl, props)
    * def stmt = conn.prepareStatement("SELECT COUNT(*) AS cnt FROM orders WHERE customer_id = ?")
    * eval stmt.setObject(1, java.util.UUID.fromString('00000000-0000-0000-0000-000000000000'))
    * def rs = stmt.executeQuery()
    * eval rs.next()
    # No order should have been persisted for the non-existent customerId
    * match rs.getInt('cnt') == 0
    * eval rs.close()
    * eval stmt.close()
    * eval conn.close()