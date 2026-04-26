import pytest
import os
import shutil
from rag.vector_store import VectorStore
from rag.retriever import ContextRetriever
from ingestion.openapi_adapter import OpenAPIAdapter
from ingestion.source_code_adapter import SourceCodeAdapter
from ingestion.existing_tests_adapter import ExistingTestsAdapter
from config.settings import get_settings

@pytest.fixture(autouse=True)
def setup_teardown(tmp_path):
    settings = get_settings()
    settings.chroma_persist_dir = str(tmp_path / "chroma_data")
    
    # Ingest data first
    store = VectorStore()
    
    openapi_adapter = OpenAPIAdapter()
    spec_chunks = openapi_adapter.ingest("data/sample_specs/orders-api.yaml")
    store.add_documents("spec", spec_chunks)
    
    code_adapter = SourceCodeAdapter()
    code_chunks = code_adapter.ingest("data/sample_source/")
    store.add_documents("code", code_chunks)
    
    test_adapter = ExistingTestsAdapter()
    test_chunks = test_adapter.ingest("data/sample_features/orders-crud.feature")
    store.add_documents("test", test_chunks)
    
    ref_chunks = test_adapter.ingest("data/karate_syntax_examples/examples.feature")
    store.add_documents("reference", ref_chunks)

def test_context_retriever():
    retriever = ContextRetriever()
    
    # Query for creating orders
    package = retriever.retrieve("create order discount")
    
    assert not package.is_empty()
    
    # Since we use sentence-transformers, it should find relevant things across the board
    assert len(package.spec_context) > 0
    assert len(package.code_context) > 0
    
    # Check if OrderService.createOrder was found (it handles discounts)
    found_service = False
    for chunk in package.code_context:
        if "OrderService" in chunk.metadata.get("class_name", ""):
            found_service = True
            break
            
    assert found_service, "OrderService was not retrieved despite querying for discounts"
    
    # The endpoint tag should be populated from the top results
    assert package.endpoint_tag != ""
