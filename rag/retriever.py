from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from rag.vector_store import VectorStore
from rag.reranker import Reranker
from config.settings import get_settings
from ingestion.base_adapter import IngestedChunk


@dataclass
class ContextPackage:
    endpoint_tag: str
    query: str
    project: str = ""
    spec_context: List[IngestedChunk] = field(default_factory=list)
    code_context: List[IngestedChunk] = field(default_factory=list)
    test_context: List[IngestedChunk] = field(default_factory=list)
    reference_context: List[IngestedChunk] = field(default_factory=list)
    schema_context: List[IngestedChunk] = field(default_factory=list)
    utility_context: List[IngestedChunk] = field(default_factory=list)
    config_context: List[IngestedChunk] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (
            self.spec_context or self.code_context or self.test_context
            or self.reference_context or self.schema_context
            or self.utility_context or self.config_context
        )

    @property
    def dominant_data_pattern(self) -> str:
        """Determine the dominant data-driven pattern from ingested test context."""
        pattern_counts: Dict[str, int] = {}
        for chunk in self.test_context + self.reference_context:
            pattern = chunk.metadata.get("data_pattern", "no_data")
            if pattern != "no_data":
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        if not pattern_counts:
            return "inline_examples"
        return max(pattern_counts, key=pattern_counts.get)


class ContextRetriever:
    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.settings = get_settings()
        self.vector_store = vector_store or VectorStore()

    def _to_ingested_chunk(self, result: Dict[str, Any]) -> IngestedChunk:
        return IngestedChunk(
            content=result["content"],
            origin_type=result["metadata"]["origin_type"],
            source_file=result["metadata"]["source_file"],
            endpoint_tag=result["metadata"]["endpoint_tag"],
            chunk_type=result["metadata"]["chunk_type"],
            metadata=result["metadata"]
        )

    def retrieve(self, query: str, project: str = "") -> ContextPackage:
        """
        Retrieves relevant context from all sources for a given query or endpoint tag.
        
        Args:
            query: Endpoint tag or natural language query.
            project: Optional project identifier. When provided, test results from the
                     same project are boosted in ranking, while cross-project patterns
                     are still included at lower priority.
        """
        # Spec and code are project-agnostic (queried without project filter)
        spec_results = self.vector_store.query("spec", query, self.settings.retrieval_top_k_spec)
        code_results = self.vector_store.query("code", query, self.settings.retrieval_top_k_code)

        # Tests and references use two-pass retrieval when a project is specified
        if project:
            # Pass 1: Same-project results (high priority)
            test_results_same = self.vector_store.query(
                "test", query, self.settings.retrieval_top_k_test,
                metadata_filter={"project": project}
            )
            # Pass 2: Cross-project results
            test_results_cross = self.vector_store.query(
                "test", query, self.settings.retrieval_top_k_test
            )
            # Combine, dedup by ID
            seen_ids = {r["id"] for r in test_results_same}
            test_results = list(test_results_same)
            for r in test_results_cross:
                if r["id"] not in seen_ids:
                    test_results.append(r)
                    seen_ids.add(r["id"])
        else:
            test_results = self.vector_store.query(
                "test", query, self.settings.retrieval_top_k_test
            )

        reference_results = self.vector_store.query(
            "reference", query, self.settings.retrieval_top_k_reference
        )

        # Schema context (if available)
        schema_results = self.vector_store.query(
            "schema", query, self.settings.retrieval_top_k_schema
        )

        # Utility and config context — project infrastructure, always retrieved
        utility_results = self.vector_store.query(
            "utility", query, self.settings.retrieval_top_k_utility
        )
        config_results = self.vector_store.query(
            "config", query, self.settings.retrieval_top_k_config
        )

        all_results = (
            spec_results + code_results + test_results
            + reference_results + schema_results
            + utility_results + config_results
        )

        # Rerank with project affinity
        reranker = Reranker(target_project=project)
        filtered_results = reranker.rerank_and_filter(all_results)

        package = ContextPackage(endpoint_tag="", query=query, project=project)

        # Sort into the context package
        for result in filtered_results:
            chunk = self._to_ingested_chunk(result)

            # If we don't have an endpoint tag yet, use the one from the highest ranked spec/code chunk
            if not package.endpoint_tag and chunk.endpoint_tag and chunk.origin_type in ["spec", "code"]:
                package.endpoint_tag = chunk.endpoint_tag

            if chunk.origin_type == "spec":
                package.spec_context.append(chunk)
            elif chunk.origin_type == "code":
                package.code_context.append(chunk)
            elif chunk.origin_type == "test":
                package.test_context.append(chunk)
            elif chunk.origin_type == "reference":
                package.reference_context.append(chunk)
            elif chunk.origin_type == "schema":
                package.schema_context.append(chunk)
            elif chunk.origin_type == "utility":
                package.utility_context.append(chunk)
            elif chunk.origin_type == "config":
                package.config_context.append(chunk)

        return package
