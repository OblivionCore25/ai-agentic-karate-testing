from typing import List, Dict, Any, Optional
from config.settings import get_settings


class Reranker:
    def __init__(self, target_project: str = ""):
        self.settings = get_settings()
        self.target_project = target_project
        self.source_weights = {
            "code": 1.2,       # Highest priority
            "spec": 1.0,       # Baseline
            "test": 0.9,       # Secondary context
            "reference": 0.8   # General reference
        }

    def rerank_and_filter(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not results:
            return []

        scored_results = []
        for result in results:
            origin_type = result["metadata"].get("origin_type", "spec")
            weight = self.source_weights.get(origin_type, 1.0)

            # ChromaDB distance: lower is more similar (e.g., L2 or cosine distance)
            # We convert it to a similarity score where higher is better.
            distance = result.get("distance", 1.0)
            base_similarity = 1.0 / (1.0 + distance)

            # Apply weight
            final_score = base_similarity * weight

            # Include confidence from code mapping if present
            confidence = result["metadata"].get("mapping_confidence", "high")
            if confidence == "low":
                final_score *= 0.5

            # Project-affinity boosting:
            # Same-project test chunks get a 1.5x multiplier
            if self.target_project and origin_type in ("test", "reference"):
                chunk_project = result["metadata"].get("project", "")
                if chunk_project and chunk_project == self.target_project:
                    final_score *= 1.5

            # Filter by relevance threshold
            if final_score >= self.settings.relevance_threshold:
                result["relevance_score"] = final_score
                scored_results.append(result)

        # Sort descending by relevance score
        scored_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored_results
