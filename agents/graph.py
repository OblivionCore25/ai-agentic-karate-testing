"""
LangGraph workflow definition for the test generation pipeline.
"""
import logging
from typing import Dict, Any

from langgraph.graph import StateGraph, END

from agents.state import AgentState
from agents.scenario_generator import generate_scenarios
from agents.feature_writer import write_features
from agents.result_analyzer import analyze_results
from rag.retriever import ContextRetriever
from executor.runner import run_tests

logger = logging.getLogger("karate_ai")


def retrieve_context(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node: Retrieve multi-source context from the RAG knowledge base.
    """
    endpoint_tag = state.get("endpoint_tag", "")
    target_project = state.get("target_project", "")
    reasoning_chain = list(state.get("reasoning_chain", []))

    logger.info(f"Retrieving context for: {endpoint_tag}")

    retriever = ContextRetriever()
    package = retriever.retrieve(endpoint_tag, project=target_project)

    if package.is_empty():
        reasoning_chain.append(f"No context found for '{endpoint_tag}'")
        return {
            "context_package": package,
            "dominant_data_pattern": "inline_examples",
            "reasoning_chain": reasoning_chain,
            "error": f"No context found for '{endpoint_tag}'",
        }

    # Summarize what we found
    summary = (
        f"Retrieved context: "
        f"{len(package.spec_context)} spec, "
        f"{len(package.code_context)} code, "
        f"{len(package.test_context)} test, "
        f"{len(package.reference_context)} reference chunks"
    )
    reasoning_chain.append(summary)

    dominant_pattern = package.dominant_data_pattern
    reasoning_chain.append(f"Dominant data pattern: {dominant_pattern}")

    return {
        "context_package": package,
        "endpoint_tag": package.endpoint_tag or endpoint_tag,
        "dominant_data_pattern": dominant_pattern,
        "reasoning_chain": reasoning_chain,
    }


def execute_tests(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node: Execute generated features via Maven.
    """
    reasoning_chain = list(state.get("reasoning_chain", []))
    
    # We don't execute if there are no generated features
    if not state.get("feature_files"):
        reasoning_chain.append("Test execution skipped: no feature files generated")
        return {
            "execution_results": [],
            "reasoning_chain": reasoning_chain,
        }
        
    reasoning_chain.append("Executing generated tests via Maven...")
    
    # Run the tests
    # In a full setup we might isolate runs to specific files, 
    # but running all in generated is fine for this project.
    result = run_tests()
    
    # Extract scenario results
    scenario_results = [r.__dict__ for r in result.report.scenario_results]
    
    reasoning_chain.append(
        f"Execution complete: {result.report.passed} passed, "
        f"{result.report.failed} failed out of {result.report.total} scenarios"
    )
    
    return {
        "execution_results": scenario_results,
        "reasoning_chain": reasoning_chain,
    }


def should_retry(state: AgentState) -> str:
    """
    Conditional edge: determines whether to retry test generation based on analysis.
    """
    analysis = state.get("analysis", {})
    has_test_issues = analysis.get("has_test_issues", False)
    retry_count = state.get("retry_count", 0)
    
    from config.settings import get_settings
    max_retries = get_settings().max_retry_count
    
    if has_test_issues and retry_count < max_retries:
        logger.info(f"Test issues found. Triggering self-correction loop (retry {retry_count + 1}/{max_retries})")
        return "retry"
        
    return "done"


def build_graph() -> StateGraph:
    """
    Build the LangGraph workflow for test generation.
    
    Flow:
        retrieve_context → generate_scenarios → write_features → execute_tests → analyze_results → (conditional retry) → END
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("generate_scenarios", generate_scenarios)
    graph.add_node("write_features", write_features)
    graph.add_node("execute_tests", execute_tests)
    graph.add_node("analyze_results", analyze_results)

    # Define edges
    graph.set_entry_point("retrieve_context")
    graph.add_edge("retrieve_context", "generate_scenarios")
    graph.add_edge("generate_scenarios", "write_features")
    graph.add_edge("write_features", "execute_tests")
    graph.add_edge("execute_tests", "analyze_results")
    
    # Conditional edge
    graph.add_conditional_edges(
        "analyze_results",
        should_retry,
        {
            "retry": "write_features",
            "done": END
        }
    )

    return graph


def compile_graph():
    """Compile the graph into a runnable."""
    graph = build_graph()
    return graph.compile()
