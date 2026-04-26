import pytest
import os
from ingestion.existing_tests_adapter import ExistingTestsAdapter


def test_existing_tests_adapter_ingestion():
    adapter = ExistingTestsAdapter()

    feature_path = "data/sample_features/orders-crud.feature"
    if not os.path.exists(feature_path):
        pytest.skip(f"{feature_path} not found")

    chunks = adapter.ingest(feature_path)

    assert len(chunks) == 2

    create_scenario = next(
        (c for c in chunks if "Create a new standard order" in c.metadata["scenario_name"]),
        None
    )
    assert create_scenario is not None
    assert create_scenario.origin_type == "test"
    assert create_scenario.endpoint_tag == "POST /orders"
    assert "status 201" in create_scenario.content

    get_scenario = next(
        (c for c in chunks if "Get an existing order" in c.metadata["scenario_name"]),
        None
    )
    assert get_scenario is not None
    assert get_scenario.endpoint_tag == "GET /orders/12345"


def test_karate_syntax_examples_ingestion():
    adapter = ExistingTestsAdapter()

    example_path = "data/karate_syntax_examples/examples.feature"
    if not os.path.exists(example_path):
        pytest.skip(f"{example_path} not found")

    chunks = adapter.ingest(example_path)

    assert len(chunks) == 2

    for chunk in chunks:
        assert chunk.origin_type == "reference"


def test_project_metadata_tagging():
    adapter = ExistingTestsAdapter()

    feature_path = "data/sample_features/orders-crud.feature"
    if not os.path.exists(feature_path):
        pytest.skip(f"{feature_path} not found")

    chunks = adapter.ingest(feature_path, project="orders-api", domain="orders")

    assert len(chunks) == 2

    for chunk in chunks:
        assert chunk.metadata["project"] == "orders-api"
        assert chunk.metadata["domain"] == "orders"


def test_csv_read_detection():
    adapter = ExistingTestsAdapter()

    feature_path = "data/sample_features/orders-data-driven.feature"
    if not os.path.exists(feature_path):
        pytest.skip(f"{feature_path} not found")

    chunks = adapter.ingest(feature_path)

    assert len(chunks) == 1
    chunk = chunks[0]

    # Should detect CSV data pattern
    assert chunk.metadata["data_pattern"] == "csv_read"

    # Should include data file reference
    assert "data_files" in chunk.metadata
    assert "order-data.csv" in chunk.metadata["data_files"]

    # Should include data schema in content
    assert "Data Source: order-data.csv" in chunk.content
    assert "Data Schema:" in chunk.content
    assert "customerId" in chunk.content


def test_data_pattern_tracking():
    adapter = ExistingTestsAdapter()

    # Ingest both regular and data-driven features
    adapter.ingest("data/sample_features/", project="orders-api")

    counts = adapter.data_pattern_counts
    assert counts["csv_read"] >= 1
    assert counts["no_data"] >= 2  # The two scenarios from orders-crud.feature


def test_dominant_data_pattern():
    adapter = ExistingTestsAdapter()

    # With only non-data-driven features
    adapter.ingest("data/sample_features/orders-crud.feature")
    assert adapter.dominant_data_pattern == "inline_examples"  # default when no data patterns found

    # Reset and ingest data-driven features
    adapter2 = ExistingTestsAdapter()
    adapter2.ingest("data/sample_features/")
    # With 1 csv_read and 2 no_data, csv_read should still be dominant
    # (no_data is excluded from dominant pattern calculation)
    pattern = adapter2.dominant_data_pattern
    assert pattern == "csv_read"
