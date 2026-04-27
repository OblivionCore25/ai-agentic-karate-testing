"""
Tests for the feature writer (mocked LLM).
"""
import pytest
from unittest.mock import patch, MagicMock
from agents.feature_writer import write_features, _extract_companion_files, _slugify
from agents.state import AgentState
from rag.retriever import ContextPackage
from ingestion.base_adapter import IngestedChunk


MOCK_FEATURE_CONTENT = """Feature: Order Creation - Standard Order

Background:
  * url baseUrl
  * header Authorization = 'Bearer test-token'

# Tests the basic happy path for order creation
@happy_path
Scenario: Create standard order with valid data
  Given path '/orders'
  And request { customerId: 'cust-123', items: [{ productId: 'prod-1', quantity: 2, price: 100.0 }] }
  When method POST
  Then status 201
  And match response.status == 'PENDING'
  And match response.totalAmount == 200.0
"""


def _make_chunk(content, origin, tag="POST /orders"):
    return IngestedChunk(
        content=content,
        origin_type=origin,
        source_file=f"test_{origin}.file",
        endpoint_tag=tag,
        chunk_type="test",
        metadata={"origin_type": origin, "source_file": f"test_{origin}.file",
                   "endpoint_tag": tag, "chunk_type": "test"}
    )


def test_slugify():
    assert _slugify("Create standard order with valid data") == "create-standard-order-with-valid-data"
    assert _slugify("POST /orders") == "post-orders"
    assert _slugify("Gold customer — 10% discount!") == "gold-customer-10-discount"


def test_extract_companion_files():
    raw = """Feature: Test
Scenario: Test
  Given path '/test'
  When method POST
  Then status 200

COMPANION_CSV_START:test-data.csv
id,name,status
1,Test,ACTIVE
2,Test2,INACTIVE
COMPANION_CSV_END
"""
    cleaned, companions = _extract_companion_files(raw)
    assert len(companions) == 1
    assert companions[0]["filename"] == "test-data.csv"
    assert "id,name,status" in companions[0]["content"]
    assert "COMPANION_CSV" not in cleaned
    assert "Feature: Test" in cleaned


def test_extract_no_companions():
    raw = "Feature: Test\nScenario: Test\n  Given path '/test'"
    cleaned, companions = _extract_companion_files(raw)
    assert companions == []
    assert cleaned == raw


@patch("agents.feature_writer.get_llm")
def test_write_features_mocked(mock_llm_class):
    """Test feature writing with mocked LLM."""
    mock_instance = MagicMock()
    mock_llm_class.return_value = mock_instance
    mock_response = MagicMock()
    mock_response.content = MOCK_FEATURE_CONTENT
    mock_instance.invoke.return_value = mock_response

    context_package = ContextPackage(
        endpoint_tag="POST /orders",
        query="POST /orders",
        reference_context=[_make_chunk("Karate reference", "reference")],
        test_context=[_make_chunk("Existing test pattern", "test")],
    )

    scenarios = [{
        "name": "Create standard order with valid data",
        "category": "happy_path",
        "description": "Test creating a basic order",
        "expected_outcome": "201 Created",
        "knowledge_sources": ["POST /orders spec"],
        "confidence": "high",
        "preconditions": ["Valid auth"],
        "test_data": {"customerId": "cust-123"},
    }]

    state: AgentState = {
        "endpoint_tag": "POST /orders",
        "target_project": "",
        "context_package": context_package,
        "scenarios": scenarios,
        "retry_count": 0,
        "reasoning_chain": [],
        "dominant_data_pattern": "inline_examples",
    }

    result = write_features(state)

    assert "feature_files" in result
    assert len(result["feature_files"]) == 1

    feat = result["feature_files"][0]
    assert feat["filename"].endswith(".feature")
    assert "Feature:" in feat["content"]
    assert feat["scenario_name"] == "Create standard order with valid data"

    # LLM should have been called once
    mock_instance.invoke.assert_called_once()


@patch("agents.feature_writer.get_llm")
def test_write_features_empty_scenarios(mock_llm_class):
    """Test feature writing with no scenarios."""
    state: AgentState = {
        "endpoint_tag": "POST /orders",
        "target_project": "",
        "scenarios": [],
        "retry_count": 0,
        "reasoning_chain": [],
        "dominant_data_pattern": "inline_examples",
    }

    result = write_features(state)
    assert result["feature_files"] == []
    mock_llm_class.assert_not_called()
