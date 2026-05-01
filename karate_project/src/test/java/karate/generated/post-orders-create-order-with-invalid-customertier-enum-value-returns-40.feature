Feature: Create Order - Invalid customerTier Enum Validation

  # Business Rule: The POST /orders endpoint enforces a strict enum for customerTier.
  # Accepted values are: STANDARD, SILVER, GOLD.
  # Any unrecognized value (e.g., PLATINUM) must be rejected with HTTP 400.

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @validation
  Scenario: Create order with invalid customerTier enum value returns 400

    # Business Rule: customerTier must be one of ['STANDARD', 'SILVER', 'GOLD'].
    # Submitting 'PLATINUM' (an unrecognized enum value) must trigger a 400 validation error.
    # The order must NOT be persisted to the database.

    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-001",
        "customerTier": "PLATINUM",
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
    Then status 400

    # Verify the response body contains a meaningful validation error
    And match response == '#object'
    And match response.error == '#present'

    # The error message or field reference should indicate the invalid enum value
    And match response.error == '#notnull'

    # JDBC Verification: Confirm that NO order record was inserted into the database
    # for this rejected request (customerTier = 'PLATINUM' is invalid and must not persist)
    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def conn = java.sql.DriverManager.getConnection(dbUrl, props)
    * def stmt = conn.prepareStatement("SELECT COUNT(*) AS cnt FROM orders o JOIN customers c ON o.customer_id = c.id WHERE c.external_id = ? AND o.created_at >= NOW() - INTERVAL '10 seconds'")
    * eval stmt.setString(1, 'cust-001')
    * def rs = stmt.executeQuery()
    * eval rs.next()
    * def rowCount = rs.getInt('cnt')
    * eval rs.close()
    * eval stmt.close()
    * eval conn.close()

    # Assert that no record was created in the orders table for this invalid request
    * match rowCount == 0

  @validation
  Scenario Outline: Create order with various invalid customerTier values returns 400

    # Business Rule: Only STANDARD, SILVER, and GOLD are valid customerTier enum values.
    # All other strings must be rejected with HTTP 400.

    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-001",
        "customerTier": "<invalidTier>",
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
    Then status 400
    And match response == '#object'
    And match response.error == '#notnull'

    Examples:
      | invalidTier |
      | PLATINUM    |
      | BRONZE      |
      | VIP         |
      | standard    |
      | gold        |
      |             |