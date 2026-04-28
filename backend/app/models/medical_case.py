"""Medical case and document models.

A MedicalCase represents a patient’s single episode of care.
MedicalDocuments are attached files (reports, images, lab results).
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class CaseStatus(str, PyEnum):
    ACTIVE = "active"
    CLOSED = "closed"
    ARCHIVED = "archived"


class DocumentType(str, PyEnum):
    REPORT = "report"
    PRESCRIPTION = "prescription"
    IMAGE = "image"
    LAB_RESULT = "lab_result"
    DISCHARGE_SUMMARY = "discharge_summary"
    OTHER = "other"


class MedicalCase(Base):
    """A patient medical case (episode of care)."""

    __tablename__ = "medical_cases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus), default=CaseStatus.ACTIVE, nullable=False
    )

    # Diagnosis fields
    diagnosis_ai: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="AI-generated preliminary diagnosis"
    )
    diagnosis_doctor: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Doctor-confirmed diagnosis"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    documents: Mapped[list["MedicalDocument"]] = relationship(
        "MedicalDocument",
        back_populates="medical_case",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class MedicalDocument(Base):
    """A document attached to a medical case."""

    __tablename__ = "medical_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("medical_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType), default=DocumentType.OTHER, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="Storage path or URL"
    )
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="OCR-extracted or plain text content"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    medical_case: Mapped["MedicalCase"] = relationship(
        "MedicalCase", back_populates="documents"
    )
