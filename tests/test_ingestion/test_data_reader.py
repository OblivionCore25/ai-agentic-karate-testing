import pytest
import os
from ingestion.test_data_reader import read_csv, read_excel, read_data_file, format_data_summary


def test_read_csv():
    csv_path = "data/sample_features/testdata/order-data.csv"
    if not os.path.exists(csv_path):
        pytest.skip(f"{csv_path} not found")

    summary = read_csv(csv_path)
    assert summary is not None
    assert summary.file_type == "csv"
    assert summary.row_count == 8
    assert len(summary.columns) == 7

    # Check column names
    col_names = [c["name"] for c in summary.columns]
    assert "customerId" in col_names
    assert "customerTier" in col_names
    assert "expectedStatus" in col_names

    # Check sample rows (default 5)
    assert len(summary.sample_rows) == 5
    assert summary.sample_rows[0]["customerId"] == "cust-001"


def test_read_excel():
    xlsx_path = "data/sample_features/testdata/customer-tiers.xlsx"
    if not os.path.exists(xlsx_path):
        pytest.skip(f"{xlsx_path} not found")

    summary = read_excel(xlsx_path)
    assert summary is not None
    assert summary.file_type == "excel"
    assert summary.row_count == 3

    col_names = [c["name"] for c in summary.columns]
    assert "tier" in col_names
    assert "discountPercent" in col_names


def test_read_data_file_csv():
    csv_path = "data/sample_features/testdata/order-data.csv"
    if not os.path.exists(csv_path):
        pytest.skip(f"{csv_path} not found")

    summary = read_data_file(csv_path)
    assert summary is not None
    assert summary.file_type == "csv"


def test_read_data_file_excel():
    xlsx_path = "data/sample_features/testdata/customer-tiers.xlsx"
    if not os.path.exists(xlsx_path):
        pytest.skip(f"{xlsx_path} not found")

    summary = read_data_file(xlsx_path)
    assert summary is not None
    assert summary.file_type == "excel"


def test_read_data_file_unsupported():
    summary = read_data_file("some_file.txt")
    assert summary is None


def test_format_data_summary():
    csv_path = "data/sample_features/testdata/order-data.csv"
    if not os.path.exists(csv_path):
        pytest.skip(f"{csv_path} not found")

    summary = read_csv(csv_path)
    text = format_data_summary(summary)

    assert "order-data.csv" in text
    assert "Data Schema:" in text
    assert "customerId" in text
    assert "Sample Data:" in text
    assert "Total Rows: 8" in text
