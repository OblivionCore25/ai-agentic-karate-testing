from abc import ABC, abstractmethod
from typing import List
from chromadb import EmbeddingFunction, Documents, Embeddings
from config.settings import get_settings
import logging

logger = logging.getLogger("karate_ai")

class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        pass

    @abstractmethod
    def get_model_id(self) -> str:
        pass


class LocalEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None
        self._dimension = None

    def _load_model(self):
        if self._model is None:
            logger.info(f"Loading local embedding model: {self.model_name}")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded. Dimension: {self._dimension}")

    def embed_text(self, text: str) -> List[float]:
        self._load_model()
        return self._model.encode(text).tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        self._load_model()
        return self._model.encode(texts).tolist()

    def get_dimension(self) -> int:
        self._load_model()
        return self._dimension

    def get_model_id(self) -> str:
        return f"local/{self.model_name}"


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str, api_key: str):
        self.model_name = model_name
        self.api_key = api_key
        self._client = None
        # Known dimensions for OpenAI models
        self._dimensions_map = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536
        }
        if self.model_name not in self._dimensions_map:
            raise ValueError(f"Unknown OpenAI embedding model: {self.model_name}")

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY environment variable is missing.")
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def embed_text(self, text: str) -> List[float]:
        client = self._get_client()
        response = client.embeddings.create(input=[text], model=self.model_name)
        return response.data[0].embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        client = self._get_client()
        # OpenAI has limits, batching could be needed here for very large lists,
        # but ChromaDB usually chunks requests anyway.
        response = client.embeddings.create(input=texts, model=self.model_name)
        return [data.embedding for data in response.data]

    def get_dimension(self) -> int:
        return self._dimensions_map[self.model_name]

    def get_model_id(self) -> str:
        return f"openai/{self.model_name}"


def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    provider = settings.embedding_provider
    model_name = settings.embedding_model

    if provider == "local":
        return LocalEmbeddingProvider(model_name)
    elif provider == "openai":
        return OpenAIEmbeddingProvider(model_name, settings.openai_api_key)
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")


class ChromaDBEmbeddingAdapter(EmbeddingFunction):
    """Adapter to make our EmbeddingProvider compatible with ChromaDB's EmbeddingFunction interface"""
    def __init__(self, provider: EmbeddingProvider):
        self.provider = provider

    def __call__(self, input: Documents) -> Embeddings:
        # ChromaDB passes a list of strings (Documents is a list of strings)
        return self.provider.embed_batch(list(input))
