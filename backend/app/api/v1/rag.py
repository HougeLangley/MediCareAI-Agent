"""RAG (Retrieval-Augmented Generation) endpoints.

Document management and medical Q&A with knowledge base retrieval.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, require_role
from app.db.session import get_db
from app.models.rag import DocType
from app.models.user import UserRole
from app.services.rag import RAGService

router = APIRouter()


class DocumentCreate(BaseModel):
    """Create a new knowledge document."""

    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=10)
    doc_type: DocType = DocType.PLATFORM_GUIDELINE
    source_url: str | None = Field(None, max_length=1000)
    department: str | None = Field(None, max_length=100)
    disease_tags: list[str] = Field(default_factory=list)
    drug_name: str | None = Field(None, max_length=200)
    language: str = "zh"


class DocumentResponse(BaseModel):
    """Document creation response."""

    id: str
    title: str
    doc_type: str
    chunk_count: int
    message: str = "Document indexed successfully"


class RAGQueryRequest(BaseModel):
    """RAG query request."""

    query: str = Field(..., min_length=1, max_length=2000)
    doc_type: DocType | None = None
    top_k: int = Field(5, ge=1, le=20)
    provider: str | None = None


class RAGQueryResponse(BaseModel):
    """RAG query response."""

    answer: str
    sources: list[dict[str, Any]]
    retrieved_chunks: int


@router.post("/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    data: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    _admin=Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> DocumentResponse:
    """Upload and index a medical knowledge document.

    Requires doctor or admin role.
    """
    service = RAGService(db)
    doc = await service.create_document(
        title=data.title,
        content=data.content,
        doc_type=data.doc_type,
        source_url=data.source_url,
        department=data.department,
        disease_tags=data.disease_tags,
        drug_name=data.drug_name,
        language=data.language,
    )
    return DocumentResponse(
        id=str(doc.id),
        title=doc.title,
        doc_type=doc.doc_type.value,
        chunk_count=doc.chunk_count,
    )


@router.post("/query", response_model=RAGQueryResponse)
async def rag_query(
    req: RAGQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> RAGQueryResponse:
    """Ask a medical question — retrieves from knowledge base + LLM answer.

    Available to all authenticated users and guests.
    """
    service = RAGService(db)
    result = await service.query(
        query=req.query,
        doc_type=req.doc_type,
        top_k=req.top_k,
        provider=req.provider,
    )
    return RAGQueryResponse(**result)


@router.get("/search")
async def search_documents(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    doc_type: DocType | None = None,
    top_k: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> list[dict[str, Any]]:
    """Full-text search over knowledge base (raw results, no LLM)."""
    service = RAGService(db)
    return await service.search(q, doc_type=doc_type, top_k=top_k)
