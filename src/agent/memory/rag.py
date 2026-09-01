"""
RAG Engine Document Ingestion and Vector Knowledge Retrieval Foundation.
"""

from typing import List, Dict, Any, Optional
from agentscope.rag import ApproxTokenChunker, Section, Chunk
from agentscope.message import TextBlock
from agent.memory.embeddings import EmbeddingModelInterface, MockEmbeddingModel

class DocumentKnowledgeRecord:
    """Document knowledge record stored in RAG engine."""

    def __init__(self, doc_id: str, title: str, chunks: List[Chunk]):
        self.doc_id = doc_id
        self.title = title
        self.chunks = chunks

class RAGEngine:
    """
    RAG Knowledge Foundation using AgentScope ApproxTokenChunker and embedding search.
    """

    def __init__(
        self,
        embedding_model: Optional[EmbeddingModelInterface] = None,
        chunk_size: int = 250,
    ) -> None:
        self.embedding_model = embedding_model or MockEmbeddingModel()
        params = ApproxTokenChunker.Parameters(chunk_size=chunk_size)
        self.chunker = ApproxTokenChunker(parameters=params)
        self.documents: Dict[str, DocumentKnowledgeRecord] = {}

    async def ingest_document(self, doc_id: str, title: str, content: str) -> int:
        """Ingests a text document, chunks it asynchronously, and indexes its contents."""
        section = Section(content=TextBlock(type="text", text=content), source=doc_id)
        chunks: List[Chunk] = await self.chunker.chunk([section])
        record = DocumentKnowledgeRecord(doc_id=doc_id, title=title, chunks=chunks)
        self.documents[doc_id] = record
        return len(chunks)

    def retrieve_knowledge(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves relevant document chunks for a query.
        """
        results: List[Dict[str, Any]] = []
        if not self.documents:
            return results

        query_terms = set(query.lower().split())

        for doc_id, doc_rec in self.documents.items():
            for chunk in doc_rec.chunks:
                chunk_text = getattr(chunk.content, "text", str(chunk.content))
                chunk_terms = set(chunk_text.lower().split())
                overlap = len(query_terms.intersection(chunk_terms))
                if overlap > 0:
                    results.append(
                        {
                            "doc_id": doc_id,
                            "title": doc_rec.title,
                            "content": chunk_text,
                            "score": float(overlap),
                        }
                    )

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]
