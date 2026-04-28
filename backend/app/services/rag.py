"""RAG (Retrieval-Augmented Generation) service.

MVP implementation using PostgreSQL ILIKE for Chinese text search.
Phase 2: upgrade to pgvector for semantic search.
"""

import uuid
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rag import Document, DocumentChunk, DocType
from app.services.llm import LLMService

# Simple chunking strategy: split by paragraphs, max 1000 chars
_CHUNK_SIZE = 1000
_CHUNK_OVERLAP = 200


class RAGService:
    """Retrieval-Augmented Generation service."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
        """Split text into overlapping chunks."""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            if end < len(text):
                search_start = max(start, end - 100)
                for i in range(end, search_start, -1):
                    if text[i] in "\n\u3002\uff01\uff1f.!?":
                        end = i + 1
                        break
            chunks.append(text[start:end])
            start = end - overlap
            if start >= len(text):
                break
        return chunks

    async def create_document(
        self,
        title: str,
        content: str,
        doc_type: DocType = DocType.GUIDELINE,
        source: str | None = None,
        language: str = "zh",
    ) -> Document:
        """Create a document with auto-chunking."""
        doc = Document(
            title=title,
            source=source,
            doc_type=doc_type,
            content=content,
            language=language,
        )
        self.db.add(doc)
        await self.db.flush()

        # Generate tsvector for full document (kept for future use)
        await self.db.execute(
            text(
                "UPDATE documents SET search_vector = "
                "to_tsvector(:lang, :content) WHERE id = :id"
            ),
            {"lang": "simple" if language == "zh" else "english",
             "content": content, "id": str(doc.id)},
        )

        chunks = self._chunk_text(content)
        for idx, chunk_text in enumerate(chunks):
            chunk = DocumentChunk(
                document_id=doc.id,
                content=chunk_text,
                chunk_index=idx,
            )
            self.db.add(chunk)
            await self.db.flush()

            await self.db.execute(
                text(
                    "UPDATE document_chunks SET search_vector = "
                    "to_tsvector(:lang, :content) WHERE id = :id"
                ),
                {"lang": "simple" if language == "zh" else "english",
                 "content": chunk_text, "id": str(chunk.id)},
            )

        doc.chunk_count = len(chunks)
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def search(
        self,
        query: str,
        doc_type: DocType | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Search document chunks using ILIKE for Chinese compatibility.

        Returns ranked results with relevance scores.
        """
        # Extract key terms (2+ char substrings) from query for ILIKE matching
        search_terms = [query[i:i+3] for i in range(len(query)-2)]
        if not search_terms:
            search_terms = [query]

        # Use the longest term for primary matching
        primary_term = max(search_terms, key=len)

        stmt = select(
            DocumentChunk.id,
            DocumentChunk.content,
            DocumentChunk.chunk_index,
            Document.id.label("doc_id"),
            Document.title,
            Document.doc_type,
            func.length(DocumentChunk.content).label("rank"),
        ).join(Document).where(
            DocumentChunk.content.ilike(f"%{primary_term}%")
        )

        if doc_type:
            stmt = stmt.where(Document.doc_type == doc_type)

        stmt = stmt.order_by(func.length(DocumentChunk.content).desc()).limit(top_k)
        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "chunk_id": str(row.id),
                "content": row.content,
                "chunk_index": row.chunk_index,
                "document_id": str(row.doc_id),
                "document_title": row.title,
                "document_type": row.doc_type.value,
                "rank": 1.0,
            }
            for row in rows
        ]

    async def generate_answer(
        self,
        query: str,
        context_chunks: list[dict[str, Any]],
        system_prompt: str | None = None,
        provider: str | None = None,
    ) -> str:
        """Generate answer using retrieved context + LLM."""
        context = "\n\n---\n\n".join(
            f"[\u6765\u6e90: {c['document_title']}]\n{c['content']}"
            for c in context_chunks
        )

        # Try LLM generation; fallback to context summary if no API key
        try:
            default_system = (
                "\u4f60\u662f\u4e00\u4f4d\u4e13\u4e1a\u7684\u533b\u7597AI\u52a9\u624b\u3002\u8bf7\u57fa\u4e8e\u4ee5\u4e0b\u53c2\u8003\u6587\u732e\u56de\u7b54\u95ee\u9898\uff0c"
                "\u5982\u679c\u53c2\u8003\u6587\u732e\u4e0d\u8db3\u4ee5\u56de\u7b54\uff0c\u8bf7\u660e\u786e\u544a\u77e5\u3002"
                "\u56de\u7b54\u8981\u6c42\uff1a\u51c6\u786e\u3001\u7b80\u6d01\u3001\u4e13\u4e1a\u3002"
            )

            messages = [
                {"role": "system", "content": system_prompt or default_system},
                {"role": "user", "content": f"\u95ee\u9898\uff1a{query}\n\n\u53c2\u8003\u6587\u732e\uff1a\n{context}"},
            ]

            llm = LLMService(provider=provider)  # type: ignore[arg-type]
            resp = await llm.chat(messages=messages, temperature=0.3, max_tokens=2048)
            return resp.content
        except ValueError:
            # No API key configured — return context as-is with disclaimer
            return (
                "[LLM \u672a\u914d\u7f6e] \u4ee5\u4e0b\u662f\u68c0\u7d22\u5230\u7684\u76f8\u5173\u53c2\u8003\u6587\u732e\uff1a\n\n"
                + context
                + "\n\n\u6ce8\uff1a\u5f53\u524d\u672a\u914d\u7f6e LLM API Key\uff0c\u56e0\u6b64\u8fd4\u56de\u539f\u6587\u6458\u8981\u3002"
            )

    async def query(
        self,
        query: str,
        doc_type: DocType | None = None,
        top_k: int = 5,
        provider: str | None = None,
    ) -> dict[str, Any]:
        """End-to-end RAG pipeline: search + generate."""
        chunks = await self.search(query, doc_type=doc_type, top_k=top_k)
        if not chunks:
            return {
                "answer": "\u672a\u627e\u5230\u76f8\u5173\u53c2\u8003\u6587\u732e\uff0c\u65e0\u6cd5\u56de\u7b54\u8be5\u95ee\u9898\u3002",
                "sources": [],
                "retrieved_chunks": 0,
            }

        answer = await self.generate_answer(query, chunks, provider=provider)
        return {
            "answer": answer,
            "sources": [
                {
                    "title": c["document_title"],
                    "type": c["document_type"],
                    "relevance": 1.0,
                }
                for c in chunks
            ],
            "retrieved_chunks": len(chunks),
        }
