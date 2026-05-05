"""
Project Context Adapter — Auto-discovers and ingests utility feature files
and configuration files from a Karate project directory.

Utility features (DB connections, date formatters, AWS auth helpers) are
classified separately from test scenarios so the LLM can generate tests
that *call* these utilities rather than reinventing them inline.
"""
import logging
import os
import re
from typing import List, Tuple, Dict, Any, Optional, Set
from fnmatch import fnmatch

from ingestion.base_adapter import BaseAdapter, IngestedChunk
from rag.chunking import chunk_for_utility, chunk_for_config

logger = logging.getLogger("karate_ai")

# Industry best-practice directory names for BDD/Karate utility features
UTILITY_DIR_PATTERNS = [
    "utils", "helpers", "common", "shared", "lib",
    "setup", "support", "fixtures", "infrastructure", "reusable",
]

CONFIG_FILE_PATTERNS = [
    "karate-config.js", "karate-config*.js",
    "karate-config.yml", "karate-config*.yml",
    "application*.yml", "application*.yaml",
    "bootstrap*.yml",
]

# Regex patterns for parameter and return value detection
ARG_PATTERN = re.compile(r"\*\s+def\s+(\w+)\s*=\s*__arg\.(\w+)", re.IGNORECASE)
RESULT_PATTERN = re.compile(r"\*\s+def\s+result\s*=", re.IGNORECASE)
DEF_PATTERN = re.compile(r"\*\s+def\s+(\w+)\s*=", re.IGNORECASE)
SCENARIO_PATTERN = re.compile(r"^\s*Scenario(?:\s+Outline)?:", re.MULTILINE)
FEATURE_PATTERN = re.compile(r"^\s*Feature:\s*(.+)", re.MULTILINE)
BACKGROUND_PATTERN = re.compile(r"^\s*Background:", re.MULTILINE)

# JS config parsing patterns
JS_CONFIG_VAR = re.compile(r"config\.(\w+)\s*=\s*(.+?)(?:;|$)", re.MULTILINE)
JS_ENV_BLOCK = re.compile(
    r"if\s*\(\s*env\s*==\s*['\"](\w+)['\"]\s*\)\s*\{([^}]+)\}",
    re.DOTALL,
)


class ProjectContextAdapter(BaseAdapter):
    """
    Adapter that auto-discovers and classifies utility features and config
    files from a Karate project directory using convention-based patterns.

    Classification rules:
    1. Feature files in directories matching UTILITY_DIR_PATTERNS → utility
    2. Feature files matching content heuristics (no Scenario, has __arg) → utility
    3. Files matching CONFIG_FILE_PATTERNS → config
    4. Everything else → ignored (handled by ExistingTestsAdapter)
    """

    def __init__(self, extra_utility_dirs: Optional[str] = None):
        """
        Args:
            extra_utility_dirs: Comma-separated additional directory names to
                                treat as utility directories (supplements defaults).
        """
        self.utility_dir_names: Set[str] = set(UTILITY_DIR_PATTERNS)
        if extra_utility_dirs:
            for d in extra_utility_dirs.split(","):
                d = d.strip().lower()
                if d:
                    self.utility_dir_names.add(d)

    def ingest(self, source_path: str, **kwargs) -> List[IngestedChunk]:
        """
        Discovers and ingests utility features and configs from a project dir.

        Returns a flat list of IngestedChunks. Callers should separate by
        origin_type ("utility" vs "config") before storing.

        Args:
            source_path: Root directory of the Karate project test sources.
        """
        utility_chunks, config_chunks = self.ingest_separated(source_path)
        return utility_chunks + config_chunks

    def ingest_separated(
        self, source_path: str
    ) -> Tuple[List[IngestedChunk], List[IngestedChunk]]:
        """
        Discovers and returns (utility_chunks, config_chunks) separately.
        """
        if not os.path.isdir(source_path):
            logger.warning(f"Source path {source_path} is not a directory.")
            return [], []

        utility_chunks: List[IngestedChunk] = []
        config_chunks: List[IngestedChunk] = []

        for root, dirs, files in os.walk(source_path):
            for filename in files:
                full_path = os.path.join(root, filename)

                # Check config files first (exact name or glob match)
                if self._is_config_file(filename):
                    chunks = self._parse_config_file(full_path, source_path)
                    config_chunks.extend(chunks)
                    continue

                # Check feature files for utility classification
                if filename.endswith(".feature"):
                    if self._is_utility_feature(full_path, root):
                        scope = self._determine_scope(full_path, source_path)
                        chunks = self._parse_utility_feature(
                            full_path, source_path, scope
                        )
                        utility_chunks.extend(chunks)

        logger.info(
            f"Project context: {len(utility_chunks)} utilities, "
            f"{len(config_chunks)} configs discovered"
        )
        return utility_chunks, config_chunks

    # ──────────────────────────────────────────────
    # Classification
    # ──────────────────────────────────────────────

    def _is_config_file(self, filename: str) -> bool:
        """Check if a file matches any config file pattern."""
        for pattern in CONFIG_FILE_PATTERNS:
            if fnmatch(filename, pattern):
                return True
        return False

    def _is_utility_feature(self, file_path: str, parent_dir: str) -> bool:
        """
        Classify a .feature file as a utility based on:
        1. Directory-based: parent dir name matches UTILITY_DIR_PATTERNS
        2. Content-based: no Scenario keyword + has callable indicators
        """
        # Rule 1: Directory name match
        dir_name = os.path.basename(parent_dir).lower()
        if dir_name in self.utility_dir_names:
            return True

        # Rule 2: Content-based heuristics
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (IOError, UnicodeDecodeError):
            return False

        has_scenario = bool(SCENARIO_PATTERN.search(content))

        # No Scenario keyword at all → likely a callable feature
        if not has_scenario:
            # Must have at least some Karate steps to be a utility
            if "* def " in content or "* url " in content or "* call " in content:
                return True

        # Has __arg → explicit callable feature
        if ARG_PATTERN.search(content):
            return True

        # Has def result but no Scenario → returns a value
        if RESULT_PATTERN.search(content) and not has_scenario:
            return True

        return False

    def _determine_scope(self, file_path: str, project_root: str) -> str:
        """
        Determine if a utility is global or project-specific based on depth.

        Global: utility dir is at the top or second level of the test tree
        Project: utility dir is nested within a feature-specific directory
        """
        rel_path = os.path.relpath(file_path, project_root)
        parts = rel_path.split(os.sep)

        # Count how many levels deep the utility directory is
        # e.g., "utils/db.feature" → depth 1 (global)
        # e.g., "orders/utils/db.feature" → depth 2 (project)
        # e.g., "api/orders/utils/db.feature" → depth 3 (project)
        if len(parts) <= 2:
            return "global"

        return "project"

    # ──────────────────────────────────────────────
    # Utility feature parsing
    # ──────────────────────────────────────────────

    def _parse_utility_feature(
        self, file_path: str, project_root: str, scope: str
    ) -> List[IngestedChunk]:
        """Parse a utility feature and extract its callable signature."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (IOError, UnicodeDecodeError) as e:
            logger.warning(f"Cannot read utility feature {file_path}: {e}")
            return []

        filename = os.path.basename(file_path)
        rel_path = os.path.relpath(file_path, project_root)
        classpath = f"classpath:{rel_path.replace(os.sep, '/')}"

        # Extract purpose from Feature: line
        purpose = ""
        feature_match = FEATURE_PATTERN.search(content)
        if feature_match:
            purpose = feature_match.group(1).strip()

        # Extract parameters (dual detection)
        parameters = self._extract_parameters(content)

        # Extract return values
        return_values = self._extract_return_values(content)

        # Determine if this is a setup utility (should use callonce)
        is_setup = any(
            keyword in content.lower()
            for keyword in ["connection", "login", "auth", "setup", "init"]
        )

        utility_info = {
            "name": filename,
            "classpath": classpath,
            "purpose": purpose,
            "scope": scope,
            "parameters": parameters,
            "return_values": return_values,
            "is_setup": is_setup,
            "content": content,
        }

        chunk_content = chunk_for_utility(utility_info)

        chunk = IngestedChunk(
            content=chunk_content,
            origin_type="utility",
            source_file=file_path,
            endpoint_tag="*",  # Utilities are endpoint-agnostic
            chunk_type="callable_feature",
            metadata={
                "name": filename,
                "classpath": classpath,
                "purpose": purpose,
                "scope": scope,
                "parameter_count": len(parameters),
                "return_count": len(return_values),
                "is_setup": is_setup,
            },
        )
        return [chunk]

    def _extract_parameters(self, content: str) -> List[Dict[str, str]]:
        """
        Extract parameters using dual detection:
        1. Explicit: * def param = __arg.param
        2. Inferred: variables referenced but not defined locally
        """
        params = []
        seen_names: Set[str] = set()

        # Strategy 1: Explicit __arg parameters
        for match in ARG_PATTERN.finditer(content):
            var_name = match.group(2)
            if var_name not in seen_names:
                params.append({"name": var_name, "detection": "explicit"})
                seen_names.add(var_name)

        # Strategy 2: Scope-based inference
        # Find all variables *defined* in this file
        defined_vars: Set[str] = set()
        for match in DEF_PATTERN.finditer(content):
            defined_vars.add(match.group(1))

        # Common Karate built-in variables to exclude from inference
        builtins = {
            "response", "responseStatus", "responseHeaders", "responseType",
            "karate", "self", "result", "__arg", "read", "call", "callonce",
        }
        defined_vars.update(builtins)

        # Look for variable references in karate.get(), or unresolved refs
        karate_get_pattern = re.compile(r"karate\.get\s*\(\s*['\"](\w+)['\"]")
        for match in karate_get_pattern.finditer(content):
            var_name = match.group(1)
            if var_name not in seen_names and var_name not in defined_vars:
                params.append({"name": var_name, "detection": "inferred"})
                seen_names.add(var_name)

        return params

    def _extract_return_values(self, content: str) -> List[str]:
        """Extract variables that are returned (def result = ...)."""
        returns = []

        # Check for explicit result assignment
        if RESULT_PATTERN.search(content):
            returns.append("result")

        # Also capture top-level def statements that might be returned
        # (in Karate, all variables defined in a called feature are accessible)
        for match in DEF_PATTERN.finditer(content):
            var_name = match.group(1)
            if var_name not in ("result",) and not var_name.startswith("_"):
                # Only include meaningful return values, not internal helpers
                if var_name not in ("conn", "stmt", "rs", "props", "query"):
                    returns.append(var_name)

        return returns

    # ──────────────────────────────────────────────
    # Config file parsing
    # ──────────────────────────────────────────────

    def _parse_config_file(
        self, file_path: str, project_root: str
    ) -> List[IngestedChunk]:
        """Parse a karate-config.js or YAML config file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (IOError, UnicodeDecodeError) as e:
            logger.warning(f"Cannot read config file {file_path}: {e}")
            return []

        filename = os.path.basename(file_path)

        if filename.endswith(".js"):
            config_info = self._parse_js_config(filename, content)
        else:
            config_info = self._parse_yaml_config(filename, content)

        config_info["content"] = content
        chunk_content = chunk_for_config(config_info)

        chunk = IngestedChunk(
            content=chunk_content,
            origin_type="config",
            source_file=file_path,
            endpoint_tag="*",  # Config applies to all endpoints
            chunk_type="karate_config",
            metadata={
                "name": filename,
                "config_type": config_info.get("config_type", "unknown"),
                "variable_count": len(config_info.get("variables", [])),
                "env_count": len(config_info.get("environment_blocks", [])),
            },
        )
        return [chunk]

    def _parse_js_config(self, filename: str, content: str) -> Dict[str, Any]:
        """Parse karate-config.js and extract config variables."""
        variables = []
        env_blocks = []

        # Extract top-level config.xxx = ... assignments
        for match in JS_CONFIG_VAR.finditer(content):
            var_name = match.group(1)
            var_value = match.group(2).strip().rstrip(";")
            variables.append({"name": var_name, "default": var_value})

        # Extract environment-specific blocks
        for match in JS_ENV_BLOCK.finditer(content):
            env_name = match.group(1)
            block_content = match.group(2)
            env_vars = []
            for var_match in JS_CONFIG_VAR.finditer(block_content):
                env_vars.append({
                    "name": var_match.group(1),
                    "default": var_match.group(2).strip().rstrip(";"),
                })
            if env_vars:
                env_blocks.append({"env": env_name, "variables": env_vars})

        return {
            "name": filename,
            "config_type": "karate-config-js",
            "variables": variables,
            "environment_blocks": env_blocks,
        }

    def _parse_yaml_config(self, filename: str, content: str) -> Dict[str, Any]:
        """Parse YAML config files and extract top-level keys."""
        variables = []

        # Simple line-based parsing (avoids yaml dependency for robustness)
        for line in content.split("\n"):
            line = line.rstrip()
            # Top-level keys (no leading whitespace, has colon)
            if line and not line.startswith(" ") and not line.startswith("#"):
                if ":" in line:
                    key, _, value = line.partition(":")
                    key = key.strip()
                    value = value.strip()
                    if key and not key.startswith("---"):
                        variables.append({
                            "name": key,
                            "default": value if value else None,
                        })

        return {
            "name": filename,
            "config_type": "yaml",
            "variables": variables,
            "environment_blocks": [],
        }
