"""
Tests for the scenario generator (mocked LLM).
"""
import pytest
from unittest.mock import patch, MagicMock
from agents.scenario_generator import generate_scenarios
from agents.state import AgentState, ScenarioList, TestScenario
from rag.retriever import ContextPackage
from ingestion.base_adapter import IngestedChunk


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


def _make_context_package():
    return ContextPackage(
        endpoint_tag="POST /orders",
        query="POST /orders",
        spec_context=[_make_chunk("Endpoint: POST /orders\nSummary: Create order", "spec")],
        code_context=[_make_chunk(
            "[Class: OrderService] [Method: createOrder]\n"
            "if (customer.tier == 'GOLD' && total > 500) { discount = 0.10; }",
            "code"
        )],
        test_context=[_make_chunk("Scenario: Create order\nGiven path '/orders'\nWhen method POST", "test")],
        reference_context=[_make_chunk("Scenario: Basic POST\nGiven url 'http://example.com'", "reference")],
    )


MOCK_SCENARIOS = ScenarioList(scenarios=[
    TestScenario(
        name="Create standard order with valid data",
        category="happy_path",
        description="Test creating a basic order with valid customer and items",
        expected_outcome="Order created with status PENDING and 201 response",
        knowledge_sources=["POST /orders spec", "OrderService.createOrder()"],
        confidence="high",
        preconditions=["Valid auth token"],
        test_data={"customerId": "cust-123", "quantity": 2}
    ),
    TestScenario(
        name="Gold customer discount applied for orders over 500",
        category="business_rule",
        description="GOLD tier customers get 10% discount when total exceeds 500",
        expected_outcome="10% discount applied to total",
        knowledge_sources=["OrderService.createOrder() - discount branch"],
        confidence="high",
        preconditions=["Customer with GOLD tier"],
        test_data={"customerId": "gold-cust", "total": 600}
    ),
    TestScenario(
        name="Reject order with missing customer ID",
        category="validation",
        description="Orders without customerId should be rejected",
        expected_outcome="400 Bad Request",
        knowledge_sources=["POST /orders spec - required fields"],
        confidence="medium",
        preconditions=[],
        test_data={"customerId": "", "quantity": 1}
    ),
    TestScenario(
        name="Handle invalid product ID gracefully",
        category="error_handling",
        description="Non-existent product IDs should return 404",
        expected_outcome="404 Not Found",
        knowledge_sources=["OrderService.createOrder()"],
        confidence="medium",
        preconditions=[],
        test_data={"productId": "nonexistent"}
    ),
    TestScenario(
        name="Boundary: Order with zero quantity",
        category="boundary",
        description="Orders with zero quantity should be rejected",
        expected_outcome="400 Bad Request with validation error",
        knowledge_sources=["POST /orders spec"],
        confidence="low",
        preconditions=[],
        test_data={"quantity": 0}
    ),
])


@patch("agents.scenario_generator.ChatAnthropic")
def test_generate_scenarios_mocked(mock_llm_class):
    """Test scenario generation with mocked LLM."""
    # Setup mock
    mock_instance = MagicMock()
    mock_llm_class.return_value = mock_instance
    mock_structured = MagicMock()
    mock_instance.with_structured_output.return_value = mock_structured
    mock_structured.invoke.return_value = MOCK_SCENARIOS

    context_package = _make_context_package()

    state: AgentState = {
        "endpoint_tag": "POST /orders",
        "target_project": "",
        "context_package": context_package,
        "retry_count": 0,
        "reasoning_chain": [],
        "dominant_data_pattern": "inline_examples",
    }

    result = generate_scenarios(state)

    assert "scenarios" in result
    assert len(result["scenarios"]) == 5

    # Check categories
    categories = [s["category"] for s in result["scenarios"]]
    assert "happy_path" in categories
    assert "business_rule" in categories
    assert "validation" in categories

    # Check reasoning chain was updated
    assert len(result["reasoning_chain"]) > 0

    # Check the LLM was called
    mock_structured.invoke.assert_called_once()


@patch("agents.scenario_generator.ChatAnthropic")
def test_generate_scenarios_empty_context(mock_llm_class):
    """Test scenario generation with empty context package."""
    empty_package = ContextPackage(endpoint_tag="", query="POST /orders")

    state: AgentState = {
        "endpoint_tag": "POST /orders",
        "target_project": "",
        "context_package": empty_package,
        "retry_count": 0,
        "reasoning_chain": [],
        "dominant_data_pattern": "inline_examples",
    }

    result = generate_scenarios(state)

    assert result["scenarios"] == []
    assert "error" in result
    # LLM should NOT have been called
    mock_llm_class.assert_not_called()


@patch("agents.scenario_generator.ChatAnthropic")
def test_generate_scenarios_no_context_package(mock_llm_class):
    """Test scenario generation with no context package at all."""
    state: AgentState = {
        "endpoint_tag": "POST /orders",
        "target_project": "",
        "context_package": None,
        "retry_count": 0,
        "reasoning_chain": [],
        "dominant_data_pattern": "inline_examples",
    }

    result = generate_scenarios(state)

    assert result["scenarios"] == []
    mock_llm_class.assert_not_called()
