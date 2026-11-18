"""RAG service — ChromaDB-backed retrieval for proposal context and reference docs."""
from __future__ import annotations
import os
from pathlib import Path

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")


class RAGService:
    _client = None
    _embedder = None

    def _get_client(self):
        if self._client is None:
            import chromadb
            self._client = chromadb.PersistentClient(path=CHROMA_PATH)
        return self._client

    def _get_embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(EMBED_MODEL)
        return self._embedder

    def _collection(self, name: str):
        return self._get_client().get_or_create_collection(name)

    def index_proposal_context(self, review_run_id: str, chunks: list[str]) -> None:
        col = self._collection("proposal_context")
        embedder = self._get_embedder()
        embeddings = embedder.encode(chunks).tolist()
        col.upsert(
            ids=[f"{review_run_id}_{i}" for i in range(len(chunks))],
            documents=chunks,
            embeddings=embeddings,
            metadatas=[{"review_run_id": review_run_id} for _ in chunks],
        )

    def query_proposal_context(self, review_run_id: str, query: str, n: int = 5) -> list[str]:
        col = self._collection("proposal_context")
        embedder = self._get_embedder()
        embedding = embedder.encode([query]).tolist()
        results = col.query(
            query_embeddings=embedding,
            n_results=n,
            where={"review_run_id": review_run_id},
        )
        return results["documents"][0] if results["documents"] else []

    def index_reference_template(self, template_id: str, chunks: list[str]) -> None:
        col = self._collection("reference_templates")
        embedder = self._get_embedder()
        embeddings = embedder.encode(chunks).tolist()
        col.upsert(
            ids=[f"{template_id}_{i}" for i in range(len(chunks))],
            documents=chunks,
            embeddings=embeddings,
            metadatas=[{"template_id": template_id} for _ in chunks],
        )

    def query_reference_template(self, template_id: str, query: str, n: int = 3) -> list[str]:
        col = self._collection("reference_templates")
        embedder = self._get_embedder()
        embedding = embedder.encode([query]).tolist()
        results = col.query(
            query_embeddings=embedding,
            n_results=n,
            where={"template_id": template_id},
        )
        return results["documents"][0] if results["documents"] else []
