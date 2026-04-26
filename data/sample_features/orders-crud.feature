Feature: Orders CRUD Operations

Background:
  * url baseUrl
  * header Authorization = 'Bearer test-token'

Scenario: Create a new standard order
  Given path '/orders'
  And request { customerId: 'cust-123', items: [{ productId: 'prod-1', quantity: 2, price: 100.0 }] }
  When method POST
  Then status 201
  And match response.totalAmount == 200.0
  And match response.status == 'PENDING'

Scenario: Get an existing order
  Given path '/orders/12345'
  When method GET
  Then status 200
  And match response.id == '12345'
