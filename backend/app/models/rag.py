"""RAG document models.

Simplified MVP implementation using PostgreSQL full-text search (tsvector).
Vector-based retrieval with pgvector planned for Phase 2.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class DocType(str, PyEnum):
    """Document types for medical knowledge base."""

    GUIDELINE = "guideline"      # 临床指南
    PAPER = "paper"              # 研究论文
    CASE_REPORT = "case_report"  # 病例报告
    DRUG_INFO = "drug_info"      # 药物资料
    TEXTBOOK = "textbook"        # 教材/专著


class Document(Base):
    """Medical knowledge document."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str | None] = mapped_column(String(500), nullable=True)
    doc_type: Mapped[DocType] = mapped_column(Enum(DocType), default=DocType.GUIDELINE)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Full-text search vector
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    
    # Metadata
    language: Mapped[str] = mapped_column(String(10), default="zh")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_documents_search_vector", "search_vector", postgresql_using="gin"),
    )


class DocumentChunk(Base):
    """Chunk of a document for retrieval."""

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    
    # Full-text search vector for chunk-level retrieval
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("ix_chunks_search_vector", "search_vector", postgresql_using="gin"),
    )
