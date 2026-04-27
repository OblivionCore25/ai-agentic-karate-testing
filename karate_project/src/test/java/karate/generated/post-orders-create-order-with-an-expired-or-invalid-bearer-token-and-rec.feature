Feature: Order Creation Security - Invalid Bearer Token Authentication

  # Tests that the authentication layer validates token integrity, not just its presence.
  # Spec reference: POST /orders - Authentication: http (bearer), 401 response defined

  Background:
    * url baseUrl
    * def invalidOrderPayload =
      """
      {
        "customerId": "cust-123",
        "customerTier": "STANDARD",
        "items": [
          {
            "productId": "prod-1",
            "quantity": 1,
            "price": 100.0
          }
        ]
      }
      """

  @security
  Scenario: Create order with an expired or invalid bearer token and receive 401 Unauthorized
    # Business rule: Requests bearing a malformed or expired token must be rejected
    # at the authentication layer before any order processing occurs.
    # The server must validate token integrity, not merely check for the presence of an Authorization header.

    * header Authorization = 'Bearer invalid-or-expired-token'
    Given path '/orders'
    And request invalidOrderPayload
    When method POST
    Then status 401
    And match response == '#notnull'

  @security
  Scenario Outline: Create order with various invalid token formats and receive 401 Unauthorized
    # Business rule: All forms of invalid, expired, or malformed bearer tokens must be
    # uniformly rejected with HTTP 401, regardless of the specific token format or payload.

    * header Authorization = '<authorizationHeader>'
    Given path '/orders'
    And request invalidOrderPayload
    When method POST
    Then status <expectedStatus>
    And match response == '#notnull'

    Examples:
      | read('testdata/invalid-token-scenarios.csv') |