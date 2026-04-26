"""
Tests for the LangGraph workflow.
"""
import pytest
from unittest.mock import patch, MagicMock
from agents.graph import build_graph, compile_graph, retrieve_context
from agents.state import AgentState, ScenarioList, TestScenario


def test_graph_builds():
    """Test that the graph compiles without errors."""
    graph = build_graph()
    assert graph is not None


def test_graph_compiles():
    """Test that the compiled graph is runnable."""
    runnable = compile_graph()
    assert runnable is not None


def test_graph_has_correct_nodes():
    """Test that the graph has all expected nodes."""
    graph = build_graph()
    # Access the nodes dict on the StateGraph
    node_names = set(graph.nodes.keys())
    expected = {"retrieve_context", "generate_scenarios", "write_features", "execute_tests"}
    assert expected.issubset(node_names), f"Missing nodes: {expected - node_names}"


@patch("agents.graph.ContextRetriever")
def test_retrieve_context_node(mock_retriever_class):
    """Test the retrieve_context node in isolation."""
    from rag.retriever import ContextPackage
    from ingestion.base_adapter import IngestedChunk

    mock_instance = MagicMock()
    mock_retriever_class.return_value = mock_instance

    mock_package = ContextPackage(
        endpoint_tag="POST /orders",
        query="POST /orders",
        spec_context=[IngestedChunk(
            content="Endpoint: POST /orders",
            origin_type="spec",
            source_file="spec.yaml",
            endpoint_tag="POST /orders",
            chunk_type="endpoint_definition",
            metadata={"origin_type": "spec", "source_file": "spec.yaml",
                       "endpoint_tag": "POST /orders", "chunk_type": "endpoint_definition"}
        )],
    )
    mock_instance.retrieve.return_value = mock_package

    state: AgentState = {
        "endpoint_tag": "POST /orders",
        "target_project": "",
        "retry_count": 0,
        "reasoning_chain": [],
    }

    result = retrieve_context(state)

    assert result["context_package"] is not None
    assert "error" not in result or result.get("error") is None
    assert len(result["reasoning_chain"]) > 0
    mock_instance.retrieve.assert_called_once_with("POST /orders", project="")
