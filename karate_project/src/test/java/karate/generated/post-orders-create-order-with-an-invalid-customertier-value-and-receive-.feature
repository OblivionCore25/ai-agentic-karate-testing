Feature: Order Creation - customerTier Enum Validation

  # Business Rule: The POST /orders endpoint enforces a strict enum for customerTier.
  # Accepted values are: STANDARD, SILVER, GOLD.
  # Any unlisted value must be rejected with HTTP 400 and a structured error response.

  Background:
    * url baseUrl
    * header Authorization = 'Bearer test-token'
    * header Content-Type = 'application/json'

  @validation
  Scenario: Create order with an invalid customerTier value and receive 400 validation error

    # Business Rule: customerTier is defined as enum [STANDARD, SILVER, GOLD].
    # Submitting an unlisted value (PLATINUM) must fail validation and return HTTP 400
    # with a structured error body containing a code and message field.

    Given path '/orders'
    And request
      """
      {
        "customerId": "cust-123",
        "customerTier": "PLATINUM",
        "items": [
          {
            "productId": "prod-1",
            "quantity": 1,
            "price": 100.0
          }
        ]
      }
      """
    When method POST
    Then status 400
    And match response.code == '#notnull'
    And match response.message == '#notnull'
    And match response.message contains '#string'

  @validation
  Scenario Outline: Create orders with various customerTier values and validate enum enforcement

    # Business Rule: Only STANDARD, SILVER, and GOLD are valid customerTier values.
    # This data-driven scenario covers both valid enum values (expecting 201)
    # and invalid enum values (expecting 400), confirming the boundary of the enum constraint.

    * def testData = read('classpath:testdata/customer-tier-validation.csv')

    Given path '/orders'
    And request
      """
      {
        "customerId": "<customerId>",
        "customerTier": "<customerTier>",
        "items": [
          {
            "productId": "<productId>",
            "quantity": <quantity>,
            "price": <price>
          }
        ]
      }
      """
    When method POST
    Then status <expectedStatus>
    * if (<expectedStatus> == 400) karate.match(response, { code: '#notnull', message: '#notnull' })
    * if (<expectedStatus> == 201) karate.match(response.status, 'PENDING')

    Examples:
      | read('classpath:testdata/customer-tier-validation.csv') |