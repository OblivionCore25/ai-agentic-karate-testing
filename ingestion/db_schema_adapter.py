"""
Database Schema Adapter — Introspects a PostgreSQL database and produces
IngestedChunks for the RAG knowledge base.

Uses SQLAlchemy inspect() for portability across database engines.
"""
import logging
import re
from typing import List, Dict, Any, Optional

from sqlalchemy import create_engine, inspect as sa_inspect, text
from sqlalchemy.engine import Engine, Inspector

from ingestion.base_adapter import BaseAdapter, IngestedChunk
from rag.chunking import chunk_for_schema

logger = logging.getLogger("karate_ai")

# Default mapping of table name patterns to HTTP methods.
# Used to infer endpoint_tag when no explicit mapping is provided.
DEFAULT_TABLE_ENDPOINT_PATTERNS = {
    # Plural table names → REST resource
    # e.g. "orders" → "POST /orders", "GET /orders", etc.
}


class DatabaseSchemaAdapter(BaseAdapter):
    """
    Adapter that introspects a live PostgreSQL database (or any SQLAlchemy-supported
    engine) and produces one IngestedChunk per table containing column definitions,
    constraints, foreign keys, and indexes.
    """

    def __init__(
        self,
        connection_string: str,
        schema: str = "public",
        table_filter: Optional[List[str]] = None,
        table_endpoint_map: Optional[Dict[str, str]] = None,
    ):
        """
        Args:
            connection_string: SQLAlchemy connection URL.
            schema: Database schema to introspect (default: public).
            table_filter: Optional list of table names to include. If None, all tables.
            table_endpoint_map: Optional dict mapping table names to endpoint tags,
                                e.g. {"orders": "POST /orders"}.
        """
        self.connection_string = connection_string
        self.schema = schema
        self.table_filter = table_filter
        self.table_endpoint_map = table_endpoint_map or {}
        self._engine: Optional[Engine] = None

    def _get_engine(self) -> Engine:
        if self._engine is None:
            self._engine = create_engine(
                self.connection_string,
                pool_pre_ping=True,
                connect_args={"options": "-c statement_timeout=10000"},  # 10s safety
            )
        return self._engine

    def ingest(self, source_path: str = "") -> List[IngestedChunk]:
        """
        Introspect the database and return one chunk per table and per view.

        Args:
            source_path: Ignored for DB adapter (connection string is used instead).
                         Kept for BaseAdapter interface compatibility.
        """
        engine = self._get_engine()
        inspector: Inspector = sa_inspect(engine)

        # ── Tables ──
        table_names = inspector.get_table_names(schema=self.schema)
        if self.table_filter:
            table_names = [t for t in table_names if t in self.table_filter]

        # ── Views ──
        try:
            view_names = inspector.get_view_names(schema=self.schema)
            if self.table_filter:
                view_names = [v for v in view_names if v in self.table_filter]
        except Exception:
            view_names = []

        logger.info(
            f"Introspecting {len(table_names)} tables and {len(view_names)} views "
            f"in schema '{self.schema}'"
        )

        chunks = []

        # Process tables
        for table_name in sorted(table_names):
            try:
                table_info = self._introspect_table(inspector, table_name)
                content = chunk_for_schema(table_info)
                endpoint_tag = self._infer_endpoint_tag(table_name)

                chunk = IngestedChunk(
                    content=content,
                    origin_type="schema",
                    source_file=f"postgresql://{self.schema}/{table_name}",
                    endpoint_tag=endpoint_tag,
                    chunk_type="table_definition",
                    metadata={
                        "table_name": table_name,
                        "schema": self.schema,
                        "column_count": len(table_info["columns"]),
                        "has_foreign_keys": len(table_info["foreign_keys"]) > 0,
                        "object_type": "table",
                        "origin_type": "schema",
                        "source_file": f"postgresql://{self.schema}/{table_name}",
                        "endpoint_tag": endpoint_tag,
                        "chunk_type": "table_definition",
                    },
                )
                chunks.append(chunk)
            except Exception as e:
                logger.error(f"Failed to introspect table '{table_name}': {e}")

        # Process views
        for view_name in sorted(view_names):
            try:
                view_info = self._introspect_view(inspector, view_name)
                content = chunk_for_schema(view_info)
                endpoint_tag = self._infer_endpoint_tag(view_name)

                chunk = IngestedChunk(
                    content=content,
                    origin_type="schema",
                    source_file=f"postgresql://{self.schema}/{view_name}",
                    endpoint_tag=endpoint_tag,
                    chunk_type="view_definition",
                    metadata={
                        "table_name": view_name,
                        "schema": self.schema,
                        "column_count": len(view_info["columns"]),
                        "has_foreign_keys": False,
                        "object_type": "view",
                        "origin_type": "schema",
                        "source_file": f"postgresql://{self.schema}/{view_name}",
                        "endpoint_tag": endpoint_tag,
                        "chunk_type": "view_definition",
                    },
                )
                chunks.append(chunk)
            except Exception as e:
                logger.error(f"Failed to introspect view '{view_name}': {e}")

        logger.info(f"Extracted {len(chunks)} table/view schemas from database")
        return chunks

    def _introspect_table(
        self, inspector: Inspector, table_name: str
    ) -> Dict[str, Any]:
        """Extract full metadata for a single table."""

        # Columns
        columns = inspector.get_columns(table_name, schema=self.schema)

        # Primary key
        pk = inspector.get_pk_constraint(table_name, schema=self.schema)
        pk_columns = set(pk.get("constrained_columns", []))

        # Foreign keys
        fks = inspector.get_foreign_keys(table_name, schema=self.schema)

        # Build FK lookup: column_name -> reference info
        fk_map: Dict[str, Dict[str, str]] = {}
        for fk in fks:
            for i, col in enumerate(fk.get("constrained_columns", [])):
                ref_table = fk.get("referred_table", "")
                ref_col = (
                    fk["referred_columns"][i]
                    if i < len(fk.get("referred_columns", []))
                    else ""
                )
                fk_map[col] = {
                    "referred_table": ref_table,
                    "referred_column": ref_col,
                    "referred_schema": fk.get("referred_schema", self.schema),
                    "options": fk.get("options", {}),
                }

        # Unique constraints
        uniques = inspector.get_unique_constraints(table_name, schema=self.schema)
        unique_columns: set = set()
        for uc in uniques:
            for col in uc.get("column_names", []):
                unique_columns.add(col)

        # Check constraints
        check_constraints = inspector.get_check_constraints(
            table_name, schema=self.schema
        )

        # Indexes
        indexes = inspector.get_indexes(table_name, schema=self.schema)

        # Table comment (PostgreSQL-specific)
        table_comment = ""
        try:
            comment_info = inspector.get_table_comment(table_name, schema=self.schema)
            table_comment = comment_info.get("text", "") or ""
        except Exception:
            pass

        # Enrich columns with constraint info
        enriched_columns = []
        for col in columns:
            col_name = col["name"]
            enriched = {
                "name": col_name,
                "type": str(col["type"]),
                "nullable": col.get("nullable", True),
                "default": str(col.get("default")) if col.get("default") else None,
                "is_primary_key": col_name in pk_columns,
                "is_unique": col_name in unique_columns,
                "is_foreign_key": col_name in fk_map,
                "foreign_key_ref": fk_map.get(col_name),
                "comment": col.get("comment", ""),
            }
            enriched_columns.append(enriched)

        return {
            "table_name": table_name,
            "schema": self.schema,
            "comment": table_comment,
            "columns": enriched_columns,
            "primary_key_columns": list(pk_columns),
            "foreign_keys": fks,
            "check_constraints": check_constraints,
            "indexes": indexes,
            "unique_constraints": uniques,
        }

    def _introspect_view(
        self, inspector: Inspector, view_name: str
    ) -> Dict[str, Any]:
        """Extract metadata for a database view (columns only, no constraints)."""

        columns = inspector.get_columns(view_name, schema=self.schema)

        # View comment (PostgreSQL-specific)
        view_comment = ""
        try:
            comment_info = inspector.get_table_comment(view_name, schema=self.schema)
            view_comment = comment_info.get("text", "") or ""
        except Exception:
            pass

        enriched_columns = []
        for col in columns:
            enriched = {
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col.get("nullable", True),
                "default": None,
                "is_primary_key": False,
                "is_unique": False,
                "is_foreign_key": False,
                "foreign_key_ref": None,
                "comment": col.get("comment", ""),
            }
            enriched_columns.append(enriched)

        return {
            "table_name": view_name,
            "schema": self.schema,
            "comment": view_comment,
            "columns": enriched_columns,
            "primary_key_columns": [],
            "foreign_keys": [],
            "check_constraints": [],
            "indexes": [],
            "unique_constraints": [],
        }

    def _infer_endpoint_tag(self, table_name: str) -> str:
        """
        Attempt to map a table name to an API endpoint tag.

        Priority:
        1. Explicit table_endpoint_map (user-provided)
        2. Convention-based: pluralize and prefix with HTTP method
        """
        # Check explicit map
        if table_name in self.table_endpoint_map:
            return self.table_endpoint_map[table_name]

        # Convention: convert snake_case table name to /kebab-or-snake path
        # e.g. "order_items" → "POST /order-items"
        path = "/" + table_name.replace("_", "-")
        return f"POST {path}"

    def close(self):
        """Dispose of the engine connection pool."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
