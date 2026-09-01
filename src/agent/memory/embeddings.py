"""
Provider-Agnostic Embedding Model Interface and Mock Implementation.
"""

from abc import ABC, abstractmethod
from typing import List
from agentscope.embedding import EmbeddingModelBase, OpenAIEmbeddingModel, OllamaEmbeddingModel

class EmbeddingModelInterface(ABC):
    """
    Abstract interface for generating vector embeddings.
    """

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Returns embedding vector for a given text."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Returns embedding vectors for a list of texts."""
        pass

class MockEmbeddingModel(EmbeddingModelInterface):
    """
    Deterministic Mock Embedding Model for testing and offline execution.
    Generates deterministic normalized 8-dimensional float vectors based on text hash.
    """

    def __init__(self, dimension: int = 8) -> None:
        self.dimension = dimension

    def embed_text(self, text: str) -> List[float]:
        val = sum(ord(c) for c in text) % 100
        vec = [round((val + i) / 100.0, 4) for i in range(self.dimension)]
        return vec

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]
