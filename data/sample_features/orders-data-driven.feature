Feature: Data-driven Order Creation

Background:
  * url baseUrl
  * header Authorization = 'Bearer test-token'

Scenario Outline: Create orders with various customer tiers
  Given path '/orders'
  And def testData = read('testdata/order-data.csv')
  And request { customerId: '<customerId>', customerTier: '<customerTier>', items: [{ productId: '<productId>', quantity: <quantity>, price: <price> }] }
  When method POST
  Then status <expectedStatus>
  And if (responseStatus == 201) match response.discountApplied == <expectedDiscount>
