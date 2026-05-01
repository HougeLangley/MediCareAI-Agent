"""RAG document models.

Simplified knowledge base with 3 document types:
- platform_guideline: 平台沉淀指南（科室指南、国家公布指南）
- case_report: 审核后的医生 UGC 病例
- drug_reference: 核心药物参考

External knowledge is retrieved via SearXNG, not stored here.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class DocType(str, PyEnum):
    """Document types for medical knowledge base.

    Simplified from 5 to 3 types. External knowledge (papers, textbooks,
    general guidelines) is retrieved via SearXNG, not stored here.
    """

    PLATFORM_GUIDELINE = "platform_guideline"  # 平台沉淀指南：科室指南、国家公布指南、诊疗规范
    CASE_REPORT = "case_report"                # 审核后的医生 UGC 病例
    DRUG_REFERENCE = "drug_reference"          # 核心药物参考（管理员维护的常用药物）


class ReviewStatus(str, PyEnum):
    """Review status for documents (mainly case_report)."""

    PENDING = "pending"              # 待审核
    AGENT_REVIEWED = "agent_reviewed"  # Agent 已初审
    DOCTOR_REVIEWED = "doctor_reviewed"  # 医生已复审
    APPROVED = "approved"            # 已通过
    REJECTED = "rejected"            # 已拒绝
    REVISION_REQUESTED = "revision_requested"  # 需要修改


class Document(Base):
    """Medical knowledge document."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    doc_type: Mapped[DocType] = mapped_column(
        Enum(DocType, values_callable=lambda x: [e.value for e in x]),
        default=DocType.PLATFORM_GUIDELINE,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Source tracking
    source_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        doc="admin_upload / doctor_ugc / agent_import"
    )
    source_url: Mapped[str | None] = mapped_column(
        String(1000), nullable=True,
        doc="原始来源 URL（如国家指南官网）"
    )
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True,
        doc="上传者（管理员或医生）"
    )

    # Review workflow (for case_report and doctor_ugc)
    review_status: Mapped[ReviewStatus] = mapped_column(
        String(50), default=ReviewStatus.APPROVED.value,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True,
        doc="审核医生"
    )
    agent_review_score: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        doc="Agent 自动评分 (0-100)"
    )
    agent_review_notes: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        doc="Agent 审核意见"
    )

    # Metadata
    department: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        doc="科室（指南类）"
    )
    disease_tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(100)), nullable=True,
        doc="相关疾病标签"
    )
    drug_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
        doc="药物名（药物类）"
    )
    language: Mapped[str] = mapped_column(String(10), default="zh")
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    # Activation & curation
    is_active: Mapped[bool] = mapped_column(default=True)
    is_featured: Mapped[bool] = mapped_column(
        default=False,
        doc="精选置顶"
    )

    # Vectorization status
    vectorized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        doc="完成向量化的时间"
    )
    embedding_model: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        doc="使用的 embedding 模型"
    )

    # Full-text search vector
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)

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
        Index("ix_documents_doc_type", "doc_type"),
        Index("ix_documents_review_status", "review_status"),
        Index("ix_documents_is_active", "is_active"),
        Index("ix_documents_disease_tags", "disease_tags", postgresql_using="gin"),
    )


class DocumentChunk(Base):
    """Chunk of a document for retrieval."""

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)

    # Vector embedding (for future pgvector upgrade)
    # embedding: Mapped[any] = mapped_column(Vector(1024), nullable=True)

    # Full-text search vector for chunk-level retrieval
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("ix_chunks_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_chunks_document_id", "document_id"),
    )


class DocumentReview(Base):
    """Review log for documents (case_report review workflow)."""

    __tablename__ = "document_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    reviewer_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        doc="agent / doctor / admin"
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(
        String(50), nullable=False,
        doc="submit / agent_review / doctor_review / approve / reject / request_revision"
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)

    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_doc_reviews_document_id", "document_id"),
        Index("ix_doc_reviews_reviewer_type", "reviewer_type"),
    )
