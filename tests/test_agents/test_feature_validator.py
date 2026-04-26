"""
Tests for the Karate feature validator.
"""
import pytest
from agents.feature_validator import validate_feature


VALID_FEATURE = """Feature: Order Creation

Background:
  * url baseUrl
  * header Authorization = 'Bearer test-token'

@happy_path
Scenario: Create a standard order
  Given path '/orders'
  And request { customerId: 'cust-123', items: [{ productId: 'prod-1', quantity: 2 }] }
  When method POST
  Then status 201
  And match response.status == 'PENDING'
"""

VALID_FEATURE_OUTLINE = """Feature: Data-driven Order Tests

Background:
  * url baseUrl

Scenario Outline: Create order with <tier> customer
  Given path '/orders'
  And request { customerId: '<customerId>', tier: '<tier>' }
  When method POST
  Then status <expectedStatus>

  Examples:
    | customerId | tier     | expectedStatus |
    | cust-001   | STANDARD | 201            |
    | cust-002   | GOLD     | 201            |
"""


def test_valid_feature():
    errors = validate_feature(VALID_FEATURE)
    assert errors == []


def test_valid_outline():
    errors = validate_feature(VALID_FEATURE_OUTLINE)
    assert errors == []


def test_missing_feature_keyword():
    content = """
Scenario: Test something
  Given path '/test'
  When method GET
  Then status 200
"""
    errors = validate_feature(content)
    assert any("Feature:" in e for e in errors)


def test_missing_scenario():
    content = """Feature: Empty Feature
"""
    errors = validate_feature(content)
    assert any("Scenario:" in e for e in errors)


def test_missing_given_path():
    content = """Feature: No Path
Scenario: Missing path
  When method GET
  Then status 200
"""
    errors = validate_feature(content)
    assert any("Given url" in e or "Given path" in e for e in errors)


def test_missing_when_method():
    content = """Feature: No Method
Scenario: Missing method
  Given path '/test'
  Then status 200
"""
    errors = validate_feature(content)
    assert any("When method" in e for e in errors)


def test_missing_then_status():
    content = """Feature: No Status
Scenario: Missing status assertion
  Given path '/test'
  When method GET
"""
    errors = validate_feature(content)
    assert any("Then status" in e for e in errors)


def test_empty_content():
    errors = validate_feature("")
    assert len(errors) > 0


def test_unbalanced_braces():
    content = """Feature: Bad JSON
Scenario: Malformed request
  Given path '/test'
  And request { name: 'test', items: [{ id: 1 }
  When method POST
  Then status 201
"""
    errors = validate_feature(content)
    assert any("Malformed" in e or "Unclosed" in e for e in errors)
