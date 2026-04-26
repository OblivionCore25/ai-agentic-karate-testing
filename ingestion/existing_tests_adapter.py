import logging
import os
import re
from typing import List, Optional, Dict, Any
from ingestion.base_adapter import BaseAdapter, IngestedChunk
from ingestion.test_data_reader import read_data_file, format_data_summary, DataFileSummary
from rag.chunking import chunk_for_test

logger = logging.getLogger("karate_ai")

# Regex to detect Karate read() calls referencing data files
READ_PATTERN = re.compile(r"read\s*\(\s*['\"]([^'\"]+\.(csv|xlsx|xls))['\"]", re.IGNORECASE)


class ExistingTestsAdapter(BaseAdapter):
    def __init__(self):
        self._data_pattern_counts: Dict[str, int] = {
            "inline_examples": 0,
            "csv_read": 0,
            "excel_read": 0,
            "json_read": 0,
            "no_data": 0
        }

    def ingest(
        self,
        source_path: str,
        project: str = "",
        domain: str = ""
    ) -> List[IngestedChunk]:
        """
        Ingests all .feature files in the given directory or file path.
        
        Args:
            source_path: Path to a .feature file or directory containing them.
            project: Project identifier for multi-project metadata tagging.
            domain: Functional domain for metadata tagging.
        """
        chunks = []

        if os.path.isfile(source_path):
            if source_path.endswith(".feature"):
                chunks.extend(self._parse_feature_file(source_path, project, domain))
        elif os.path.isdir(source_path):
            for root, _, files in os.walk(source_path):
                for file in files:
                    if file.endswith(".feature"):
                        full_path = os.path.join(root, file)
                        chunks.extend(self._parse_feature_file(full_path, project, domain))
        else:
            logger.warning(f"Source path {source_path} is neither a file nor a directory.")

        logger.info(f"Extracted {len(chunks)} scenarios from Karate tests")
        if any(v > 0 for v in self._data_pattern_counts.values()):
            logger.info(f"Data pattern distribution: {self._data_pattern_counts}")
        return chunks

    @property
    def data_pattern_counts(self) -> Dict[str, int]:
        """Returns the count of each data pattern detected during ingestion."""
        return dict(self._data_pattern_counts)

    @property
    def dominant_data_pattern(self) -> str:
        """Returns the most common data-driven pattern found in ingested tests."""
        # Exclude "no_data" from dominant pattern detection
        data_patterns = {k: v for k, v in self._data_pattern_counts.items() if k != "no_data"}
        if not data_patterns or all(v == 0 for v in data_patterns.values()):
            return "inline_examples"  # default
        return max(data_patterns, key=data_patterns.get)

    def _parse_feature_file(
        self,
        file_path: str,
        project: str,
        domain: str
    ) -> List[IngestedChunk]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return []

        # Determine origin type based on directory
        origin_type = "reference" if "karate_syntax_examples" in file_path else "test"

        chunks = []
        current_scenario = None
        feature_name = "Unknown Feature"
        feature_tags = []
        pending_tags = []
        background_steps = []
        in_background = False
        in_examples = False

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if stripped.startswith("Feature:"):
                feature_name = stripped.replace("Feature:", "").strip()
                in_background = False
                in_examples = False
            elif stripped.startswith("Background:"):
                in_background = True
                in_examples = False
            elif stripped.startswith("Scenario:") or stripped.startswith("Scenario Outline:"):
                in_background = False
                in_examples = False
                if current_scenario:
                    self._finalize_scenario(
                        current_scenario, chunks, file_path,
                        origin_type, feature_name, project, domain
                    )

                name = stripped.replace("Scenario Outline:", "").replace("Scenario:", "").strip()
                is_outline = stripped.startswith("Scenario Outline:")
                current_scenario = {
                    "name": name,
                    "steps": list(background_steps),
                    "tags": list(pending_tags),
                    "url": "",
                    "method": "",
                    "is_outline": is_outline,
                    "has_examples_table": False,
                    "data_files": [],       # Referenced CSV/Excel files
                    "data_summaries": [],    # Parsed data file summaries
                }
                pending_tags = []
            elif stripped.startswith("@"):
                # Tags can appear before Feature or Scenario
                tags = [t.strip() for t in stripped.split() if t.startswith("@")]
                if current_scenario is None:
                    pending_tags.extend(tags)
                    feature_tags.extend(tags)
                else:
                    pending_tags.extend(tags)
            elif stripped.startswith("Examples:"):
                in_examples = True
                if current_scenario:
                    current_scenario["has_examples_table"] = True
            elif in_examples:
                # Skip example table rows (they're part of the scenario structure)
                if current_scenario:
                    current_scenario["steps"].append(stripped)
            elif current_scenario and not in_background:
                current_scenario["steps"].append(stripped)

                # Extract URL and Method for endpoint tagging
                if stripped.startswith("Given url") or stripped.startswith("Given path"):
                    match = re.search(r"'(.*?)'", stripped) or re.search(r'"(.*?)"', stripped)
                    if match:
                        current_scenario["url"] = match.group(1)
                elif stripped.startswith("When method"):
                    parts = stripped.split()
                    if len(parts) > 2:
                        current_scenario["method"] = parts[2].upper()

                # Detect read() calls referencing CSV/Excel files
                read_matches = READ_PATTERN.findall(stripped)
                for data_path, ext in read_matches:
                    resolved = self._resolve_data_file(file_path, data_path)
                    if resolved:
                        current_scenario["data_files"].append(data_path)
                        summary = read_data_file(resolved)
                        if summary:
                            current_scenario["data_summaries"].append(summary)

            elif in_background:
                background_steps.append(stripped)

        # Finalize the last scenario
        if current_scenario:
            self._finalize_scenario(
                current_scenario, chunks, file_path,
                origin_type, feature_name, project, domain
            )

        return chunks

    def _resolve_data_file(self, feature_path: str, data_ref: str) -> Optional[str]:
        """
        Resolves a Karate read() path relative to the feature file directory.
        Handles classpath: prefix and relative paths.
        """
        # Strip classpath: prefix if present
        clean_path = data_ref.replace("classpath:", "")

        feature_dir = os.path.dirname(os.path.abspath(feature_path))

        # Try relative to feature file directory
        candidate = os.path.join(feature_dir, clean_path)
        if os.path.isfile(candidate):
            return candidate

        # Try one level up (common in Karate projects where testdata/ is a sibling)
        candidate = os.path.join(os.path.dirname(feature_dir), clean_path)
        if os.path.isfile(candidate):
            return candidate

        logger.debug(f"Could not resolve data file '{data_ref}' relative to {feature_path}")
        return None

    def _determine_data_pattern(self, scenario: Dict[str, Any]) -> str:
        """Determine the data-driven pattern used by a scenario."""
        if scenario["data_summaries"]:
            # Has referenced CSV/Excel files
            for summary in scenario["data_summaries"]:
                if summary.file_type == "csv":
                    return "csv_read"
                elif summary.file_type == "excel":
                    return "excel_read"
        if scenario["has_examples_table"]:
            return "inline_examples"
        # Check for JSON read() patterns
        json_read = re.compile(r"read\s*\(\s*['\"]([^'\"]+\.json)['\"]")
        for step in scenario["steps"]:
            if json_read.search(step):
                return "json_read"
        return "no_data"

    def _finalize_scenario(
        self,
        scenario: Dict[str, Any],
        chunks: List[IngestedChunk],
        file_path: str,
        origin_type: str,
        feature_name: str,
        project: str,
        domain: str
    ):
        # Determine endpoint tag
        endpoint_tag = ""
        if scenario.get("method") and scenario.get("url"):
            url = scenario["url"]
            if not url.startswith("/"):
                url = "/" + url
            endpoint_tag = f"{scenario['method']} {url}"

        # Determine data pattern
        data_pattern = self._determine_data_pattern(scenario)
        self._data_pattern_counts[data_pattern] = self._data_pattern_counts.get(data_pattern, 0) + 1

        # Build content with optional data file info
        content = chunk_for_test(scenario)

        # Append data file summaries to content
        if scenario["data_summaries"]:
            content += "\n\n"
            for summary in scenario["data_summaries"]:
                content += format_data_summary(summary) + "\n"

        metadata = {
            "feature_name": feature_name,
            "scenario_name": scenario["name"],
            "data_pattern": data_pattern,
        }

        # Add project/domain metadata if provided
        if project:
            metadata["project"] = project
        if domain:
            metadata["domain"] = domain

        # Add data file references
        if scenario["data_files"]:
            metadata["data_files"] = ", ".join(scenario["data_files"])

        chunk = IngestedChunk(
            content=content,
            origin_type=origin_type,
            source_file=file_path,
            endpoint_tag=endpoint_tag,
            chunk_type="scenario",
            metadata=metadata
        )
        chunks.append(chunk)
