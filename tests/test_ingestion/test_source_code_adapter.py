import pytest
import os
from ingestion.source_code_adapter import SourceCodeAdapter

def test_source_code_adapter_ingestion():
    adapter = SourceCodeAdapter()
    source_path = "data/sample_source/"
    
    if not os.path.exists(source_path):
        pytest.skip(f"{source_path} not found")
        
    chunks = adapter.ingest(source_path)
    
    assert len(chunks) > 0
    
    # Check that OrderController.createOrder is parsed and tagged with POST /orders
    create_order_controller = next((c for c in chunks if "createOrder" in c.metadata["method_name"] and "OrderController" in c.metadata["class_name"]), None)
    assert create_order_controller is not None
    assert create_order_controller.endpoint_tag == "POST /orders"
    assert "OrderRequest" in create_order_controller.content
    
    # Check that OrderService.createOrder is parsed
    create_order_service = next((c for c in chunks if "createOrder" in c.metadata["method_name"] and "OrderService" in c.metadata["class_name"]), None)
    assert create_order_service is not None
    # Since there's no mapping annotation on the service, it falls back to the heuristic
    assert "Method: OrderService.createOrder" in create_order_service.endpoint_tag
    assert "GOLD" in create_order_service.content
    assert "discount" in create_order_service.content

def test_source_code_adapter_invalid_path():
    adapter = SourceCodeAdapter()
    chunks = adapter.ingest("non_existent_path")
    assert len(chunks) == 0
