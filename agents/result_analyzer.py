"""
Result Analyzer — LangGraph node that classifies test failures and suggests fixes.
"""
import logging
from typing import Dict, Any, List

from langchain_core.messages import SystemMessage, HumanMessage

from agents.state import AgentState, FailureAnalysis, FailureReport
from agents.prompts.result_analysis import SYSTEM_PROMPT, build_user_prompt
from config.settings import get_settings, get_llm

logger = logging.getLogger("karate_ai.agents")

def _truncate(text: str, max_chars: int = 4000) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated]"

def _format_chunks(chunks) -> str:
    if not chunks:
        return "(no context available)"
    parts = []
    for i, chunk in enumerate(chunks):
        parts.append(f"--- {chunk.source_file} ---")
        parts.append(chunk.content)
        parts.append("")
    return "\n".join(parts)


def analyze_results(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph node: Analyzes execution results and classifies failures.
    """
    settings = get_settings()
    execution_results = state.get("execution_results", [])
    feature_files = state.get("feature_files", [])
    context_package = state.get("context_package")
    reasoning_chain = list(state.get("reasoning_chain", []))

    if not execution_results:
        reasoning_chain.append("No execution results to analyze.")
        return {
            "analysis": {"has_test_issues": False, "analyses": []},
            "reasoning_chain": reasoning_chain
        }

    # Filter only failed scenarios
    failed_results = [r for r in execution_results if not r.get("passed", True)]
    
    if not failed_results:
        reasoning_chain.append("All tests passed. No analysis needed.")
        return {
            "analysis": {"has_test_issues": False, "analyses": []},
            "reasoning_chain": reasoning_chain
        }

    # Prepare context string
    context_text = ""
    if context_package:
        spec_text = _truncate(_format_chunks(context_package.spec_context))
        code_text = _truncate(_format_chunks(context_package.code_context))
        context_text = f"## API Spec\n{spec_text}\n\n## Source Code\n{code_text}"

    # Setup LLM
    llm = get_llm("analysis").with_structured_output(FailureReport)

    analyses = []
    has_test_issues = False
    
    # We may have multiple failed scenarios.
    # Group failures by feature file to avoid analyzing the same file repeatedly
    # if it fails multiple times for the same reason.
    features_to_analyze = {}
    for r in failed_results:
        feat_name = r.get("feature_file")
        if feat_name not in features_to_analyze:
            features_to_analyze[feat_name] = []
        features_to_analyze[feat_name].append(r)

    # Convert generated features to a dict for easy lookup
    generated_features_map = {f.get("filename"): f for f in feature_files}

    for feat_name, scenario_failures in features_to_analyze.items():
        # Get the feature content
        feat_data = generated_features_map.get(feat_name)
        if not feat_data:
            logger.warning(f"Feature {feat_name} not found in state, skipping analysis.")
            continue
            
        feature_content = feat_data.get("content", "")
        
        # Analyze the first failure for this feature to keep token usage down
        # (Usually if a feature has multiple failures, fixing the first one or understanding the root cause applies to the whole file)
        primary_failure = scenario_failures[0]
        scenario_name = primary_failure.get("scenario_name", "Unknown")
        failed_step = primary_failure.get("failed_step", "Unknown")
        error_msg = primary_failure.get("failure_message", "Unknown error")
        
        user_prompt = build_user_prompt(
            feature_content=feature_content,
            scenario_name=scenario_name,
            failure_message=error_msg,
            failed_step=failed_step,
            context_text=context_text
        )

        logger.info(f"Analyzing failure in '{feat_name}' -> '{scenario_name}'")
        
        try:
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=user_prompt),
            ]
            
            # The LLM returns a FailureReport containing analyses
            result: FailureReport = llm.invoke(messages)
            
            if result and result.analyses:
                # Take the first analysis since we sent one failure
                analysis = result.analyses[0]
                analysis.scenario_name = scenario_name # ensure name matches
                analyses.append(analysis.model_dump())
                
                classification = analysis.classification
                reasoning_chain.append(f"Analyzed '{scenario_name}': {classification} ({analysis.confidence} confidence)")
                
                if classification == "test_issue":
                    has_test_issues = True
                    
        except Exception as e:
            logger.error(f"Failed to analyze scenario '{scenario_name}': {e}")
            reasoning_chain.append(f"Analysis failed for '{scenario_name}': {str(e)}")

    retry_count = state.get("retry_count", 0)

    analysis_result = {
        "has_test_issues": has_test_issues,
        "analyses": analyses
    }

    return {
        "analysis": analysis_result,
        "reasoning_chain": reasoning_chain,
        "retry_count": retry_count + 1 if has_test_issues else retry_count
    }
