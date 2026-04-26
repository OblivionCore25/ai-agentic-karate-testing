import pytest
import os
import shutil
from rag.vector_store import VectorStore
from ingestion.base_adapter import IngestedChunk
from config.settings import get_settings

@pytest.fixture(autouse=True)
def setup_teardown(tmp_path):
    settings = get_settings()
    # Use a unique temporary directory for each test to avoid SQLite locks
    settings.chroma_persist_dir = str(tmp_path / "chroma_data")
    # VectorStore caches the client, so we must reset it to pick up the new dir
    # But since VectorStore is recreated per test, it might be fine.
    # However, get_settings() is a singleton, so settings are updated.

def test_vector_store_initialization():
    store = VectorStore()
    store.initialize()
    
    stats = store.get_stats()
    assert "spec" in stats
    assert "code" in stats
    assert "test" in stats
    assert "reference" in stats
    
    # Initial state should be empty
    for origin, count in stats.items():
        assert count == 0

def test_add_and_query_documents():
    store = VectorStore()
    
    chunks = [
        IngestedChunk(
            content="This is a test document about order creation.",
            origin_type="spec",
            source_file="orders-api.yaml",
            endpoint_tag="POST /orders",
            chunk_type="endpoint_definition",
            metadata={"priority": "high"}
        ),
        IngestedChunk(
            content="This is a completely unrelated document about login.",
            origin_type="spec",
            source_file="auth-api.yaml",
            endpoint_tag="POST /login",
            chunk_type="endpoint_definition",
            metadata={"priority": "low"}
        )
    ]
    
    store.add_documents("spec", chunks)
    
    stats = store.get_stats()
    assert stats["spec"] == 2
    
    # Semantic search query
    results = store.query("spec", "creating new orders", top_k=1)
    assert len(results) == 1
    assert "order creation" in results[0]["content"]
    assert results[0]["metadata"]["endpoint_tag"] == "POST /orders"

def test_metadata_filtering():
    store = VectorStore()
    
    chunks = [
        IngestedChunk(
            content="Order processing logic",
            origin_type="code",
            source_file="OrderService.java",
            endpoint_tag="POST /orders",
            chunk_type="service_method",
            metadata={"language": "java"}
        ),
        IngestedChunk(
            content="Order processing script",
            origin_type="code",
            source_file="process_order.py",
            endpoint_tag="POST /orders",
            chunk_type="script",
            metadata={"language": "python"}
        )
    ]
    
    store.add_documents("code", chunks)
    
    # Query with metadata filter
    results = store.query(
        "code", 
        "order logic", 
        top_k=2, 
        metadata_filter={"language": "python"}
    )
    
    assert len(results) == 1
    assert results[0]["metadata"]["language"] == "python"

def test_delete_collection():
    store = VectorStore()
    
    chunks = [
        IngestedChunk(
            content="Test content",
            origin_type="reference",
            source_file="example.feature",
            endpoint_tag="",
            chunk_type="scenario",
        )
    ]
    
    store.add_documents("reference", chunks)
    assert store.get_stats()["reference"] == 1
    
    store.delete_collection("reference")
    assert store.get_stats()["reference"] == 0
