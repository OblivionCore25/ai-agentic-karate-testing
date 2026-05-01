Feature: Create Order Validation - Missing Required 'items' Field

  # Tests that the POST /orders endpoint correctly rejects requests where the required
  # 'items' array is omitted, as mandated by the API spec (items: required, minItems: 1).

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @validation
  Scenario: Create order with missing required field 'items' returns 400

    # Business Rule: The 'items' field is marked as required with minItems: 1 in the
    # POST /orders spec. Omitting it entirely must result in a 400 Bad Request response
    # containing both a 'code' and a 'message' field in the error body.

    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-001",
        "customerTier": "STANDARD"
      }
      """
    When method POST
    Then status 400

    # Verify the error response body conforms to the 400 response schema
    And match response.code == '#present'
    And match response.message == '#present'
    And match response.code == '#notnull'
    And match response.message == '#notnull'

    # Verify that NO order record was persisted in the database for this rejected request
    * def props = new java.util.Properties()
    * eval props.setProperty('user', dbUser)
    * eval props.setProperty('password', dbPassword)
    * def conn = java.sql.DriverManager.getConnection(dbUrl, props)
    * def stmt = conn.prepareStatement("SELECT COUNT(*) AS cnt FROM orders o JOIN customers c ON o.customer_id = c.id WHERE c.id::text = ? AND o.created_at >= NOW() - INTERVAL '10 seconds'")
    * eval stmt.setString(1, 'cust-001')
    * def rs = stmt.executeQuery()
    * eval rs.next()
    * match rs.getInt('cnt') == 0
    * eval rs.close()
    * eval stmt.close()
    * eval conn.close()