import pytest
import os
from ingestion.openapi_adapter import OpenAPIAdapter

def test_openapi_adapter_ingestion():
    adapter = OpenAPIAdapter()
    spec_path = "data/sample_specs/orders-api.yaml"
    
    # Check if file exists, else skip
    if not os.path.exists(spec_path):
        pytest.skip(f"{spec_path} not found")
        
    chunks = adapter.ingest(spec_path)
    
    # 5 endpoints in the sample spec:
    # GET /orders, POST /orders, GET /orders/{id}, DELETE /orders/{id}, PUT /orders/{id}/status
    assert len(chunks) == 5
    
    # Verify a specific chunk
    post_orders = next((c for c in chunks if c.endpoint_tag == "POST /orders"), None)
    assert post_orders is not None
    assert post_orders.origin_type == "spec"
    assert post_orders.chunk_type == "endpoint_definition"
    assert post_orders.metadata["summary"] == "Create order"
    assert post_orders.metadata["has_request_body"] is True
    
    # Check that $ref was resolved
    assert "customerId" in post_orders.content
    assert "customerTier" in post_orders.content
    assert "GOLD" in post_orders.content
    
    # Check auth parsing
    assert "bearer" in post_orders.content.lower()

def test_openapi_adapter_invalid_file():
    adapter = OpenAPIAdapter()
    with pytest.raises(Exception):
        adapter.ingest("non_existent_file.yaml")
