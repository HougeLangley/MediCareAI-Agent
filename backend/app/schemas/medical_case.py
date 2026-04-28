"""Medical case and document schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.medical_case import CaseStatus, DocumentType


# ─── MedicalDocument ───────────────────────────────────────────

class MedicalDocumentBase(BaseModel):
    """Base medical document schema."""

    document_type: DocumentType = DocumentType.OTHER
    title: str = Field(..., min_length=1, max_length=255)
    file_path: str | None = Field(None, max_length=500)
    file_size: int | None = None
    mime_type: str | None = Field(None, max_length=100)
    content_text: str | None = None


class MedicalDocumentCreate(MedicalDocumentBase):
    """Create medical document."""
    pass


class MedicalDocumentUpdate(BaseModel):
    """Update medical document."""

    document_type: DocumentType | None = None
    title: str | None = Field(None, max_length=255)
    content_text: str | None = None


class MedicalDocumentResponse(MedicalDocumentBase):
    """Medical document response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_id: uuid.UUID
    uploaded_by: uuid.UUID | None
    created_at: datetime


# ─── MedicalCase ───────────────────────────────────────────

class MedicalCaseBase(BaseModel):
    """Base medical case schema."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    status: CaseStatus = CaseStatus.ACTIVE


class MedicalCaseCreate(MedicalCaseBase):
    """Create medical case (patient creates their own case)."""
    pass


class MedicalCaseUpdate(BaseModel):
    """Update medical case."""

    title: str | None = Field(None, max_length=255)
    description: str | None = None
    status: CaseStatus | None = None
    diagnosis_doctor: str | None = None


class MedicalCaseDoctorUpdate(BaseModel):
    """Doctor-only update fields."""

    diagnosis_doctor: str | None = None
    status: CaseStatus | None = None
    doctor_id: uuid.UUID | None = None


class MedicalCaseResponse(MedicalCaseBase):
    """Medical case response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID | None
    diagnosis_ai: str | None
    diagnosis_doctor: str | None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
    documents: list[MedicalDocumentResponse] = []


class MedicalCaseListResponse(BaseModel):
    """Paginated list of medical cases."""

    total: int
    items: list[MedicalCaseResponse]
