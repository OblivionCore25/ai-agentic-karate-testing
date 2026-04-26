Feature: Karate Syntax Examples

Scenario: Basic POST with matchers
  Given url 'https://httpbin.org/post'
  And request { name: 'Test' }
  When method POST
  Then status 200
  And match response.json.name == 'Test'
  And match response.headers contains { 'Content-Type': '#notnull' }

Scenario Outline: Data driven examples
  Given url 'https://example.com/api'
  And request { id: <id> }
  When method POST
  Then status <status>

  Examples:
    | id | status |
    | 1  | 200    |
    | -1 | 400    |
