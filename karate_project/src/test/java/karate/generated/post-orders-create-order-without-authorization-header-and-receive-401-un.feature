Feature: Order Creation Security - Authentication Enforcement
  # Tests that POST /orders enforces bearer token authentication
  # Business Rule: All order creation requests must include a valid Authorization header
  # Spec Reference: POST /orders - Authentication: http (bearer), 401 response defined

  Background:
    * url baseUrl
    # Intentionally NO Authorization header set in Background - this file tests unauthenticated requests

  @security
  Scenario: Create order without Authorization header and receive 401 Unauthorized
    # Business Rule: The POST /orders endpoint must reject requests that do not include
    # an Authorization header, returning HTTP 401 Unauthorized to enforce authentication.
    # Precondition: No Authorization header is present in the request.

    Given path '/orders'
    And request
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
    When method POST
    Then status 401
    # Verify the response signals an authentication failure, not a generic server error
    And match response == '#notnull'