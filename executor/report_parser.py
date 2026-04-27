"""
Parser for Karate test execution JSON reports.
"""
import os
import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

logger = logging.getLogger("karate_ai.executor")

@dataclass
class ScenarioResult:
    feature_file: str
    scenario_name: str
    passed: bool
    duration_ms: float
    failure_message: Optional[str] = None
    failed_step: Optional[str] = None


@dataclass  
class TestReport:
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    duration_ms: float = 0.0
    scenario_results: List[ScenarioResult] = field(default_factory=list)


def parse_karate_reports(reports_dir: str) -> TestReport:
    """
    Parse all *.karate-json.txt files in the given directory and aggregate results.
    """
    report = TestReport()
    
    if not os.path.isdir(reports_dir):
        logger.warning(f"Reports directory not found: {reports_dir}")
        return report

    json_files = [f for f in os.listdir(reports_dir) if f.endswith(".karate-json.txt")]
    
    for filename in json_files:
        filepath = os.path.join(reports_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # The base name is roughly filename without .karate-json.txt 
            # and removing the package prefix (e.g. karate.generated.)
            feature_file_hint = filename.replace(".karate-json.txt", ".feature")
            if feature_file_hint.startswith("karate.generated."):
                feature_file_hint = feature_file_hint[len("karate.generated."):]
                
            scenario_results_data = data.get("scenarioResults", [])
            
            for scenario_data in scenario_results_data:
                report.total += 1
                
                scenario_name = scenario_data.get("name", "Unknown Scenario")
                failed = scenario_data.get("failed", False)
                duration_ms = scenario_data.get("durationMillis", 0.0)
                
                report.duration_ms += duration_ms
                
                if failed:
                    report.failed += 1
                    
                    error_msg = scenario_data.get("error")
                    failed_step_text = None
                    
                    # Try to find the exact failed step
                    for step_result_data in scenario_data.get("stepResults", []):
                        step_res = step_result_data.get("result", {})
                        if step_res.get("status") == "failed":
                            step_info = step_result_data.get("step", {})
                            failed_step_text = step_info.get("text", "Unknown Step")
                            if not error_msg:
                                error_msg = step_res.get("errorMessage")
                            break
                    
                    scenario_res = ScenarioResult(
                        feature_file=feature_file_hint,
                        scenario_name=scenario_name,
                        passed=False,
                        duration_ms=duration_ms,
                        failure_message=error_msg,
                        failed_step=failed_step_text
                    )
                else:
                    report.passed += 1
                    scenario_res = ScenarioResult(
                        feature_file=feature_file_hint,
                        scenario_name=scenario_name,
                        passed=True,
                        duration_ms=duration_ms
                    )
                    
                report.scenario_results.append(scenario_res)
                
        except Exception as e:
            logger.error(f"Failed to parse report {filename}: {e}")
            report.errors += 1
            
    return report
