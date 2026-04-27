import json
import os
import time
from dataclasses import dataclass, asdict
from typing import Dict, Any

@dataclass
class GenerationRun:
    timestamp: str
    endpoint_tag: str
    scenarios_generated: int
    features_written: int
    syntactic_errors: int
    generation_time_seconds: float
    categories: Dict[str, int]
    knowledge_sources_used: int

@dataclass
class ExecutionRun:
    timestamp: str
    total_tests: int
    passed: int
    failed: int
    failure_classifications: Dict[str, int]
    self_corrections_attempted: int
    self_corrections_succeeded: int
    execution_time_seconds: float

class MetricsCollector:
    def __init__(self, log_path: str = "./metrics/generation_log.jsonl"):
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        
    def record_generation(self, run: GenerationRun):
        with open(self.log_path, "a") as f:
            record = {"type": "generation", **asdict(run)}
            f.write(json.dumps(record) + "\n")
            
    def record_execution(self, run: ExecutionRun):
        with open(self.log_path, "a") as f:
            record = {"type": "execution", **asdict(run)}
            f.write(json.dumps(record) + "\n")
            
    def get_all_records(self) -> list[Dict[str, Any]]:
        if not os.path.exists(self.log_path):
            return []
            
        records = []
        with open(self.log_path, "r") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        return records
