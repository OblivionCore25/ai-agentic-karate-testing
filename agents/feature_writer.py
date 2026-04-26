"""
Feature Writer — LangGraph node that converts test scenarios to Karate .feature files.
"""
import json
import logging
import re
from typing import Dict, Any, List

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from agents.state import AgentState, TestScenario, GeneratedFeature
from agents.feature_validator import validate_feature
from agents.prompts.feature_writing import SYSTEM_PROMPT, build_user_prompt
from config.settings import get_settings

logger = logging.getLogger("karate_ai")

MAX_CONTEXT_CHARS = 6000


def _truncate(text: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated]"


def _format_chunks(chunks) -> str:
    if not chunks:
        return "(no examples available)"
    parts = []
    for i, chunk in enumerate(chunks):
        parts.append(f"--- Example {i+1}: {chunk.source_file} ---")
        parts.append(chunk.content)
        parts.append("")
    return "\n".join(parts)


def _slugify(name: str) -> str:
    """Convert scenario name to a valid filename slug."""
    slug = name.lower()
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    slug = slug.strip('-')
    return slug[:60]  # Cap length


def _extract_companion_files(raw_content: str) -> tuple:
    """
    Extract companion CSV files from the LLM response.
    Returns (cleaned_feature_content, list_of_companion_files).
    """
    companions = []
    pattern = re.compile(
        r'COMPANION_CSV_START:(.+?)\n(.*?)COMPANION_CSV_END',
        re.DOTALL
    )
    
    for match in pattern.finditer(raw_content):
        filename = match.group(1).strip()
        csv_content = match.group(2).strip()
        companions.append({
            "filename": filename,
            "content": csv_content,
            "file_type": "csv"
        })
    
    # Remove companion sections from the feature content
    cleaned = pattern.sub('', raw_content).strip()
    return cleaned, companions


def write_features(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node: Convert test scenarios into Karate .feature files.
    
    Reads scenarios from state, calls Claude to generate feature files,
    validates syntax, and returns updated state with feature_files populated.
    """
    settings = get_settings()
    scenarios = state.get("scenarios", [])
    context_package = state.get("context_package")
    endpoint_tag = state.get("endpoint_tag", "")
    dominant_data_pattern = state.get("dominant_data_pattern", "inline_examples")
    reasoning_chain = list(state.get("reasoning_chain", []))

    if not scenarios:
        return {
            "feature_files": [],
            "reasoning_chain": reasoning_chain + ["No scenarios to write features for"],
        }

    # Get reference and test patterns for the prompt
    reference_text = ""
    test_patterns_text = ""
    if context_package:
        reference_text = _truncate(_format_chunks(context_package.reference_context))
        test_patterns_text = _truncate(_format_chunks(context_package.test_context))

    llm = ChatAnthropic(
        model=settings.claude_model_generation,
        api_key=settings.anthropic_api_key,
        temperature=settings.llm_temperature_analysis,  # Lower temp for deterministic syntax
        max_tokens=settings.llm_max_tokens_generation,
    )

    feature_files = []

    for scenario_dict in scenarios:
        scenario = TestScenario(**scenario_dict)
        scenario_json = scenario.model_dump_json(indent=2)

        user_prompt = build_user_prompt(
            scenario_json=scenario_json,
            karate_reference=reference_text,
            existing_test_patterns=test_patterns_text,
            dominant_data_pattern=dominant_data_pattern,
            endpoint_tag=endpoint_tag,
        )

        logger.info(f"Writing feature for scenario: {scenario.name}")

        try:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]

            response = llm.invoke(messages)
            raw_content = response.content.strip()

            # Strip markdown code fences if present
            if raw_content.startswith("```"):
                lines = raw_content.split("\n")
                # Remove first and last lines (fences)
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                raw_content = "\n".join(lines)

            # Extract companion data files
            feature_content, companions = _extract_companion_files(raw_content)

            # Validate syntax
            errors = validate_feature(feature_content)

            if errors:
                logger.warning(f"Validation errors for '{scenario.name}': {errors}")
                # Auto-retry once with error feedback
                retry_prompt = (
                    f"{user_prompt}\n\n"
                    f"IMPORTANT: Your previous attempt had these syntax errors:\n"
                    + "\n".join(f"- {e}" for e in errors)
                    + "\n\nPlease fix these issues and return a corrected .feature file."
                )

                retry_messages = [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=retry_prompt),
                ]

                retry_response = llm.invoke(retry_messages)
                retry_content = retry_response.content.strip()

                if retry_content.startswith("```"):
                    lines = retry_content.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    retry_content = "\n".join(lines)

                retry_content, retry_companions = _extract_companion_files(retry_content)

                retry_errors = validate_feature(retry_content)
                if not retry_errors or len(retry_errors) < len(errors):
                    feature_content = retry_content
                    companions = retry_companions
                    errors = retry_errors
                    reasoning_chain.append(
                        f"Feature '{scenario.name}' auto-corrected after validation retry"
                    )

            filename = f"{_slugify(endpoint_tag)}-{_slugify(scenario.name)}.feature"

            feature = GeneratedFeature(
                filename=filename,
                content=feature_content,
                scenario_name=scenario.name,
                knowledge_sources=scenario.knowledge_sources,
                reasoning=scenario.description,
                companion_data_files=companions,
            )
            feature_files.append(feature.model_dump())

            status = "VALID" if not errors else f"WARNINGS: {errors}"
            reasoning_chain.append(
                f"Feature '{scenario.name}' -> {filename} [{status}]"
            )

        except Exception as e:
            logger.error(f"Feature writing failed for '{scenario.name}': {e}")
            reasoning_chain.append(f"Feature writing failed for '{scenario.name}': {str(e)}")

    logger.info(f"Generated {len(feature_files)} feature files")

    return {
        "feature_files": feature_files,
        "reasoning_chain": reasoning_chain,
    }
