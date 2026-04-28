"""RAG (Retrieval-Augmented Generation) service.

MVP implementation using PostgreSQL full-text search.
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
            # Try to break at newline or period
            if end < len(text):
                # Look for a good break point within last 100 chars
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
        # Create document
        doc = Document(
            title=title,
            source=source,
            doc_type=doc_type,
            content=content,
            language=language,
        )
        self.db.add(doc)
        await self.db.flush()  # Get doc.id

        # Generate tsvector for full document
        await self.db.execute(
            text(
                "UPDATE documents SET search_vector = "
                "to_tsvector(:lang, :content) WHERE id = :id"
            ),
            {"lang": "simple" if language == "zh" else "english",
             "content": content, "id": str(doc.id)},
        )

        # Create chunks
        chunks = self._chunk_text(content)
        for idx, chunk_text in enumerate(chunks):
            chunk = DocumentChunk(
                document_id=doc.id,
                content=chunk_text,
                chunk_index=idx,
            )
            self.db.add(chunk)
            await self.db.flush()

            # Generate tsvector for chunk
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
        """Full-text search over documents and chunks.

        Returns ranked results with relevance scores.
        """
        # Use plainto_tsquery for natural language query parsing
        tsquery_expr = func.plainto_tsquery("simple", query)

        # Search chunks with ranking
        stmt = select(
            DocumentChunk.id,
            DocumentChunk.content,
            DocumentChunk.chunk_index,
            Document.id.label("doc_id"),
            Document.title,
            Document.doc_type,
            func.ts_rank(
                DocumentChunk.search_vector,
                tsquery_expr,
            ).label("rank"),
        ).join(Document).where(
            DocumentChunk.search_vector.op("@@")(tsquery_expr)
        )

        if doc_type:
            stmt = stmt.where(Document.doc_type == doc_type)

        stmt = stmt.order_by(text("rank DESC")).limit(top_k)
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
                "rank": float(row.rank),
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
        """Generate answer using retrieved context + LLM.

        Args:
            query: User question.
            context_chunks: Retrieved document chunks from search().
            system_prompt: Optional custom system prompt.
            provider: LLM provider override.

        Returns:
            Generated answer text.
        """
        # Build context string
        context = "\n\n---\n\n".join(
            f"[来源: {c['document_title']}]\n{c['content']}"
            for c in context_chunks
        )

        default_system = (
            "你是一位专业的医疗AI助手。请基于以下参考文献回答问题，"
            "如果参考文献不足以回答，请明确告知。"
            "回答要求：准确、简洁、专业。"
        )

        messages = [
            {
                "role": "system",
                "content": system_prompt or default_system,
            },
            {
                "role": "user",
                "content": f"问题：{query}\n\n参考文献：\n{context}",
            },
        ]

        llm = LLMService(provider=provider)  # type: ignore[arg-type]
        resp = await llm.chat(messages=messages, temperature=0.3, max_tokens=2048)
        return resp.content

    async def query(
        self,
        query: str,
        doc_type: DocType | None = None,
        top_k: int = 5,
        provider: str | None = None,
    ) -> dict[str, Any]:
        """End-to-end RAG pipeline: search + generate.

        Args:
            query: User question.
            doc_type: Filter by document type.
            top_k: Number of chunks to retrieve.
            provider: LLM provider override.

        Returns:
            Dict with answer, sources, and usage info.
        """
        chunks = await self.search(query, doc_type=doc_type, top_k=top_k)
        if not chunks:
            return {
                "answer": "未找到相关参考文献，无法回答该问题。",
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
                    "relevance": round(c["rank"], 4),
                }
                for c in chunks
            ],
            "retrieved_chunks": len(chunks),
        }
