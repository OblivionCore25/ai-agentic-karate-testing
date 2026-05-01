"""
Tests for the database schema adapter (mocked SQLAlchemy Inspector).
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from ingestion.db_schema_adapter import DatabaseSchemaAdapter
from rag.chunking import chunk_for_schema


# ─── Mock data ───────────────────────────────────────────────

MOCK_COLUMNS = [
    {
        "name": "id",
        "type": "UUID",
        "nullable": False,
        "default": "gen_random_uuid()",
        "comment": None,
    },
    {
        "name": "customer_id",
        "type": "UUID",
        "nullable": False,
        "default": None,
        "comment": "References the customers table",
    },
    {
        "name": "status",
        "type": "VARCHAR(20)",
        "nullable": False,
        "default": "'PENDING'",
        "comment": None,
    },
    {
        "name": "total_amount",
        "type": "NUMERIC(12, 2)",
        "nullable": False,
        "default": None,
        "comment": None,
    },
    {
        "name": "discount_applied",
        "type": "NUMERIC(12, 2)",
        "nullable": True,
        "default": "0.00",
        "comment": None,
    },
    {
        "name": "created_at",
        "type": "TIMESTAMP WITH TIME ZONE",
        "nullable": False,
        "default": "now()",
        "comment": None,
    },
]

MOCK_PK = {"constrained_columns": ["id"]}

MOCK_FKS = [
    {
        "constrained_columns": ["customer_id"],
        "referred_table": "customers",
        "referred_columns": ["id"],
        "referred_schema": "public",
        "options": {"ondelete": "CASCADE"},
    }
]

MOCK_UNIQUES = []

MOCK_CHECKS = [
    {"name": "orders_status_check", "sqltext": "status IN ('PENDING', 'SHIPPED', 'CANCELLED')"},
    {"name": "orders_total_check", "sqltext": "total_amount >= 0"},
]

MOCK_INDEXES = [
    {"name": "idx_orders_customer_id", "column_names": ["customer_id"], "unique": False},
    {"name": "idx_orders_status", "column_names": ["status"], "unique": False},
]

MOCK_TABLE_COMMENT = {"text": "Stores customer order records"}


# ─── Tests: chunk_for_schema ─────────────────────────────────

def test_chunk_for_schema_basic():
    """Test that chunk_for_schema produces readable output."""
    table_info = {
        "table_name": "orders",
        "schema": "public",
        "comment": "Stores customer order records",
        "columns": [
            {"name": "id", "type": "UUID", "nullable": False, "default": "gen_random_uuid()",
             "is_primary_key": True, "is_unique": False, "is_foreign_key": False,
             "foreign_key_ref": None, "comment": ""},
            {"name": "customer_id", "type": "UUID", "nullable": False, "default": None,
             "is_primary_key": False, "is_unique": False, "is_foreign_key": True,
             "foreign_key_ref": {"referred_table": "customers", "referred_column": "id"},
             "comment": "References the customers table"},
        ],
        "primary_key_columns": ["id"],
        "foreign_keys": MOCK_FKS,
        "check_constraints": MOCK_CHECKS,
        "indexes": MOCK_INDEXES,
        "unique_constraints": [],
    }

    result = chunk_for_schema(table_info)

    assert "Table: orders" in result
    assert "Stores customer order records" in result
    assert "id: UUID [PK, NOT NULL" in result
    assert "FK → customers.id" in result
    assert "orders_status_check" in result
    assert "idx_orders_customer_id" in result
    assert "ON DELETE CASCADE" in result


def test_chunk_for_schema_empty_table():
    """Test chunk formatting for a table with no constraints."""
    table_info = {
        "table_name": "audit_log",
        "schema": "public",
        "comment": "",
        "columns": [
            {"name": "id", "type": "SERIAL", "nullable": False, "default": None,
             "is_primary_key": True, "is_unique": False, "is_foreign_key": False,
             "foreign_key_ref": None, "comment": ""},
            {"name": "message", "type": "TEXT", "nullable": True, "default": None,
             "is_primary_key": False, "is_unique": False, "is_foreign_key": False,
             "foreign_key_ref": None, "comment": ""},
        ],
        "primary_key_columns": ["id"],
        "foreign_keys": [],
        "check_constraints": [],
        "indexes": [],
        "unique_constraints": [],
    }

    result = chunk_for_schema(table_info)

    assert "Table: audit_log" in result
    assert "id: SERIAL [PK, NOT NULL]" in result
    assert "message: TEXT" in result
    # No constraints sections
    assert "Check Constraints:" not in result
    assert "Foreign Keys:" not in result


# ─── Tests: DatabaseSchemaAdapter ─────────────────────────────

@patch("ingestion.db_schema_adapter.create_engine")
@patch("ingestion.db_schema_adapter.sa_inspect")
def test_adapter_ingest(mock_inspect_fn, mock_create_engine):
    """Test that the adapter produces correct chunks from mocked DB."""
    mock_engine = MagicMock()
    mock_create_engine.return_value = mock_engine

    mock_inspector = MagicMock()
    mock_inspect_fn.return_value = mock_inspector

    mock_inspector.get_table_names.return_value = ["orders", "customers"]
    mock_inspector.get_columns.return_value = MOCK_COLUMNS
    mock_inspector.get_pk_constraint.return_value = MOCK_PK
    mock_inspector.get_foreign_keys.return_value = MOCK_FKS
    mock_inspector.get_unique_constraints.return_value = MOCK_UNIQUES
    mock_inspector.get_check_constraints.return_value = MOCK_CHECKS
    mock_inspector.get_indexes.return_value = MOCK_INDEXES
    mock_inspector.get_table_comment.return_value = MOCK_TABLE_COMMENT

    adapter = DatabaseSchemaAdapter(
        connection_string="postgresql://test:test@localhost/testdb",
        schema="public",
    )

    chunks = adapter.ingest()

    assert len(chunks) == 2
    assert chunks[0].origin_type == "schema"
    assert chunks[0].chunk_type == "table_definition"
    assert chunks[0].metadata["table_name"] == "customers"  # sorted alphabetically
    assert chunks[1].metadata["table_name"] == "orders"
    assert "id: UUID" in chunks[1].content


@patch("ingestion.db_schema_adapter.create_engine")
@patch("ingestion.db_schema_adapter.sa_inspect")
def test_adapter_table_filter(mock_inspect_fn, mock_create_engine):
    """Test that table_filter restricts which tables are introspected."""
    mock_engine = MagicMock()
    mock_create_engine.return_value = mock_engine

    mock_inspector = MagicMock()
    mock_inspect_fn.return_value = mock_inspector

    mock_inspector.get_table_names.return_value = ["orders", "customers", "audit_log"]
    mock_inspector.get_columns.return_value = MOCK_COLUMNS
    mock_inspector.get_pk_constraint.return_value = MOCK_PK
    mock_inspector.get_foreign_keys.return_value = []
    mock_inspector.get_unique_constraints.return_value = []
    mock_inspector.get_check_constraints.return_value = []
    mock_inspector.get_indexes.return_value = []
    mock_inspector.get_table_comment.return_value = {"text": ""}

    adapter = DatabaseSchemaAdapter(
        connection_string="postgresql://test:test@localhost/testdb",
        table_filter=["orders"],
    )

    chunks = adapter.ingest()

    assert len(chunks) == 1
    assert chunks[0].metadata["table_name"] == "orders"


@patch("ingestion.db_schema_adapter.create_engine")
@patch("ingestion.db_schema_adapter.sa_inspect")
def test_adapter_endpoint_tag_inference(mock_inspect_fn, mock_create_engine):
    """Test that table names are mapped to endpoint tags."""
    mock_engine = MagicMock()
    mock_create_engine.return_value = mock_engine

    mock_inspector = MagicMock()
    mock_inspect_fn.return_value = mock_inspector

    mock_inspector.get_table_names.return_value = ["order_items"]
    mock_inspector.get_columns.return_value = [
        {"name": "id", "type": "SERIAL", "nullable": False, "default": None, "comment": ""}
    ]
    mock_inspector.get_pk_constraint.return_value = {"constrained_columns": ["id"]}
    mock_inspector.get_foreign_keys.return_value = []
    mock_inspector.get_unique_constraints.return_value = []
    mock_inspector.get_check_constraints.return_value = []
    mock_inspector.get_indexes.return_value = []
    mock_inspector.get_table_comment.return_value = {"text": ""}

    adapter = DatabaseSchemaAdapter(
        connection_string="postgresql://test:test@localhost/testdb",
    )

    chunks = adapter.ingest()

    assert chunks[0].endpoint_tag == "POST /order-items"


@patch("ingestion.db_schema_adapter.create_engine")
@patch("ingestion.db_schema_adapter.sa_inspect")
def test_adapter_explicit_endpoint_map(mock_inspect_fn, mock_create_engine):
    """Test that explicit table-to-endpoint mapping takes priority."""
    mock_engine = MagicMock()
    mock_create_engine.return_value = mock_engine

    mock_inspector = MagicMock()
    mock_inspect_fn.return_value = mock_inspector

    mock_inspector.get_table_names.return_value = ["orders"]
    mock_inspector.get_columns.return_value = [
        {"name": "id", "type": "UUID", "nullable": False, "default": None, "comment": ""}
    ]
    mock_inspector.get_pk_constraint.return_value = {"constrained_columns": ["id"]}
    mock_inspector.get_foreign_keys.return_value = []
    mock_inspector.get_unique_constraints.return_value = []
    mock_inspector.get_check_constraints.return_value = []
    mock_inspector.get_indexes.return_value = []
    mock_inspector.get_table_comment.return_value = {"text": ""}

    adapter = DatabaseSchemaAdapter(
        connection_string="postgresql://test:test@localhost/testdb",
        table_endpoint_map={"orders": "POST /api/v1/orders"},
    )

    chunks = adapter.ingest()

    assert chunks[0].endpoint_tag == "POST /api/v1/orders"
