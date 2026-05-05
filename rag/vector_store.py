import chromadb
from chromadb.config import Settings
from config.settings import get_settings
from rag.embeddings import get_embedding_provider, ChromaDBEmbeddingAdapter
from ingestion.base_adapter import IngestedChunk
from typing import List, Dict, Any, Optional
import logging
import os

logger = logging.getLogger("karate_ai")

class VectorStore:
    def __init__(self):
        self.settings = get_settings()
        self.client = None
        self.embedding_provider = None
        self.embedding_function = None
        
        self.collection_names = {
            "spec": "api_specs",
            "code": "source_code",
            "test": "existing_tests",
            "reference": "karate_reference",
            "schema": "db_schemas",
            "utility": "project_utilities",
            "config": "project_configs",
        }

    def initialize(self):
        if self.client is not None:
            return
            
        logger.info(f"Initializing ChromaDB at {self.settings.chroma_persist_dir}")
        os.makedirs(self.settings.chroma_persist_dir, exist_ok=True)
        
        self.client = chromadb.PersistentClient(
            path=self.settings.chroma_persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        
        self.embedding_provider = get_embedding_provider()
        self.embedding_function = ChromaDBEmbeddingAdapter(self.embedding_provider)
        
        # Verify provider mismatch
        model_id = self.embedding_provider.get_model_id()
        
        for origin_type, coll_name in self.collection_names.items():
            collection = self.client.get_or_create_collection(
                name=coll_name,
                embedding_function=self.embedding_function,
                metadata={"origin_type": origin_type, "model_id": model_id}
            )
            
            # Check model mismatch if the collection already existed
            if collection.metadata and collection.metadata.get("model_id") and collection.metadata.get("model_id") != model_id:
                raise ValueError(
                    f"Embedding model mismatch in collection '{coll_name}'. "
                    f"Stored with '{collection.metadata['model_id']}', but configured for '{model_id}'. "
                    f"Please delete the chroma_data directory and re-ingest."
                )

    def add_documents(self, origin_type: str, chunks: List[IngestedChunk]):
        self.initialize()
        if not chunks:
            return
            
        coll_name = self.collection_names.get(origin_type)
        if not coll_name:
            raise ValueError(f"Unknown origin_type: {origin_type}")
            
        collection = self.client.get_collection(
            name=coll_name, 
            embedding_function=self.embedding_function
        )
        
        ids = []
        documents = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            basename = os.path.basename(chunk.source_file)
            chunk_id = f"{origin_type}_{basename}_{chunk.endpoint_tag}_{chunk.chunk_type}_{i}"
            # Replace spaces and slashes for a cleaner ID
            chunk_id = chunk_id.replace(" ", "_").replace("/", "_").replace(".", "_")
            
            ids.append(chunk_id)
            documents.append(chunk.content)
            
            # Combine standard metadata with chunk-specific metadata
            meta = {
                "origin_type": chunk.origin_type,
                "source_file": chunk.source_file,
                "endpoint_tag": chunk.endpoint_tag,
                "chunk_type": chunk.chunk_type
            }
            if chunk.metadata:
                # Chroma metadata must be strings, ints, or floats
                for k, v in chunk.metadata.items():
                    if isinstance(v, (str, int, float, bool)):
                        meta[k] = v
                    else:
                        meta[k] = str(v)
            
            metadatas.append(meta)
            
        logger.info(f"Adding {len(chunks)} chunks to collection {coll_name}")
        # Upsert allows overwriting if ids already exist
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    def query(
        self, 
        origin_type: str, 
        query_text: str, 
        top_k: int, 
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        self.initialize()
        
        coll_name = self.collection_names.get(origin_type)
        if not coll_name:
            raise ValueError(f"Unknown origin_type: {origin_type}")
            
        collection = self.client.get_collection(
            name=coll_name,
            embedding_function=self.embedding_function
        )
        
        where = metadata_filter if metadata_filter else None
        
        results = collection.query(
            query_texts=[query_text],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        formatted_results = []
        if not results["ids"] or not results["ids"][0]:
            return formatted_results
            
        # Parse ChromaDB output format
        for i in range(len(results["ids"][0])):
            formatted_results.append({
                "id": results["ids"][0][i],
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]  # Lower distance = higher similarity
            })
            
        return formatted_results

    def delete_collection(self, origin_type: str):
        self.initialize()
        coll_name = self.collection_names.get(origin_type)
        if not coll_name:
            raise ValueError(f"Unknown origin_type: {origin_type}")
            
        logger.info(f"Deleting collection: {coll_name}")
        try:
            self.client.delete_collection(name=coll_name)
        except ValueError:
            pass # Collection doesn't exist
            
    def get_stats(self) -> Dict[str, int]:
        self.initialize()
        stats = {}
        for origin_type, coll_name in self.collection_names.items():
            try:
                collection = self.client.get_collection(name=coll_name)
                stats[origin_type] = collection.count()
            except Exception: # Catch chromadb.errors.NotFoundError or ValueError
                stats[origin_type] = 0
        return stats
