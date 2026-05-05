from dataclasses import dataclass, field
from typing import Dict, Any, List
from abc import ABC, abstractmethod

@dataclass
class IngestedChunk:
    content: str
    origin_type: str        # "spec", "code", "test", "reference", "utility", "config"
    source_file: str
    endpoint_tag: str       # e.g., "POST /orders"
    chunk_type: str         # e.g., "endpoint_definition", "service_method", "feature_scenario"
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseAdapter(ABC):
    @abstractmethod
    def ingest(self, source_path: str) -> List[IngestedChunk]:
        pass
