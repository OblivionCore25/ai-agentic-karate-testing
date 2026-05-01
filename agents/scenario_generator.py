"""
Scenario Generator — LangGraph node that generates test scenarios from context.
"""
import json
import logging
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage

from agents.state import AgentState, ScenarioList
from agents.prompts.scenario_generation import SYSTEM_PROMPT, build_user_prompt
from config.settings import get_settings, get_llm

logger = logging.getLogger("karate_ai")

MAX_CONTEXT_CHARS = 12000  # Per-source truncation limit


def _truncate(text: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated]"


def _format_chunks(chunks) -> str:
    """Format a list of IngestedChunks into a single text block."""
    if not chunks:
        return "(no context available)"
    parts = []
    for i, chunk in enumerate(chunks):
        parts.append(f"--- Source {i+1}: {chunk.source_file} (tag: {chunk.endpoint_tag}) ---")
        parts.append(chunk.content)
        parts.append("")
    return "\n".join(parts)


def generate_scenarios(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node: Generate test scenarios from the context package.
    
    Reads context_package from state, calls Claude to generate scenarios,
    and returns updated state with scenarios populated.
    """
    settings = get_settings()
    context_package = state.get("context_package")
    endpoint_tag = state.get("endpoint_tag", "")
    dominant_data_pattern = state.get("dominant_data_pattern", "inline_examples")
    reasoning_chain = list(state.get("reasoning_chain", []))

    if context_package is None or context_package.is_empty():
        return {
            "scenarios": [],
            "reasoning_chain": reasoning_chain + ["No context available for scenario generation"],
            "error": "No context package available"
        }

    # Format context for the prompt
    spec_text = _truncate(_format_chunks(context_package.spec_context))
    code_text = _truncate(_format_chunks(context_package.code_context))
    test_text = _truncate(_format_chunks(context_package.test_context))
    schema_text = _truncate(_format_chunks(context_package.schema_context))

    user_prompt = build_user_prompt(
        endpoint_tag=endpoint_tag or context_package.endpoint_tag,
        spec_context=spec_text,
        code_context=code_text,
        test_context=test_text,
        dominant_data_pattern=dominant_data_pattern,
        schema_context=schema_text
    )

    # Track which sources were used
    source_files = set()
    for chunk in (context_package.spec_context + context_package.code_context + context_package.test_context + context_package.schema_context):
        source_files.add(chunk.source_file)
    reasoning_chain.append(f"Scenario generation using sources: {', '.join(sorted(source_files))}")

    logger.info(f"Generating scenarios for {endpoint_tag} using {settings.llm_provider} provider")

    try:
        llm = get_llm("generation")

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        # Use structured output for reliable parsing
        structured_llm = llm.with_structured_output(ScenarioList)
        result: ScenarioList = structured_llm.invoke(messages)

        scenarios = [s.model_dump() for s in result.scenarios]
        logger.info(f"Generated {len(scenarios)} scenarios")

        # Summarize categories
        categories = {}
        for s in scenarios:
            cat = s["category"]
            categories[cat] = categories.get(cat, 0) + 1
        reasoning_chain.append(f"Generated {len(scenarios)} scenarios: {categories}")

        return {
            "scenarios": scenarios,
            "reasoning_chain": reasoning_chain,
        }
    except Exception as e:
        logger.error(f"Scenario generation failed: {e}")
        return {
            "scenarios": [],
            "reasoning_chain": reasoning_chain + [f"Scenario generation failed: {str(e)}"],
            "error": str(e),
        }
