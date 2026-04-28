"""Multi-Agent Medical Collaboration endpoints.

Orchestrates DiagnosisAgent, PlanningAgent, and MonitoringAgent.
"""

from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.services.agents import AgentOrchestrator
from app.services.rag import RAGService

router = APIRouter()


class DiagnosisRequest(BaseModel):
    """Symptom analysis request."""

    symptoms: str = Field(..., min_length=5, max_length=2000)
    patient_history: str | None = Field(None, max_length=5000)
    test_results: str | None = Field(None, max_length=5000)
    provider: str | None = None


class PlanningRequest(BaseModel):
    """Treatment planning request."""

    diagnosis: str = Field(..., min_length=5, max_length=2000)
    patient_profile: dict[str, Any] | None = None
    constraints: list[str] | None = None
    provider: str | None = None


class MonitoringRequest(BaseModel):
    """Monitoring check request."""

    patient_updates: str = Field(..., min_length=5, max_length=3000)
    baseline_status: str | None = None
    current_plan: str | None = None
    provider: str | None = None


class ConsultationRequest(BaseModel):
    """Full multi-agent consultation request."""

    symptoms: str = Field(..., min_length=5, max_length=2000)
    patient_history: str | None = Field(None, max_length=5000)
    patient_profile: dict[str, Any] | None = None
    provider: str | None = None


@router.post("/diagnose", status_code=status.HTTP_200_OK)
async def diagnose(
    req: DiagnosisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> dict[str, Any]:
    """Run DiagnosisAgent on reported symptoms."""
    orchestrator = AgentOrchestrator(provider=req.provider)
    rag = RAGService(db)
    result = await orchestrator.diagnosis.analyze(
        symptoms=req.symptoms,
        patient_history=req.patient_history,
        test_results=req.test_results,
        use_rag=True,
        rag_service=rag,
    )
    return {
        "agent": "diagnosis",
        "content": result.content,
        "sources": result.sources_used,
    }


@router.post("/plan", status_code=status.HTTP_200_OK)
async def plan_treatment(
    req: PlanningRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> dict[str, Any]:
    """Run PlanningAgent to generate treatment plan."""
    orchestrator = AgentOrchestrator(provider=req.provider)
    rag = RAGService(db)
    result = await orchestrator.planning.plan(
        diagnosis=req.diagnosis,
        patient_profile=req.patient_profile,
        constraints=req.constraints,
        use_rag=True,
        rag_service=rag,
    )
    return {
        "agent": "planning",
        "content": result.content,
        "sources": result.sources_used,
    }


@router.post("/monitor", status_code=status.HTTP_200_OK)
async def monitor(
    req: MonitoringRequest,
    current_user: CurrentUser = None,
) -> dict[str, Any]:
    """Run MonitoringAgent on patient updates."""
    orchestrator = AgentOrchestrator(provider=req.provider)
    result = await orchestrator.monitoring.check(
        patient_updates=req.patient_updates,
        baseline_status=req.baseline_status,
        current_plan=req.current_plan,
    )
    return {
        "agent": "monitoring",
        "content": result.content,
        "confidence": result.confidence,
    }


@router.post("/consult", status_code=status.HTTP_200_OK)
async def full_consultation(
    req: ConsultationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> dict[str, Any]:
    """Run complete multi-agent consultation (diagnosis + plan + monitoring)."""
    orchestrator = AgentOrchestrator(provider=req.provider)
    rag = RAGService(db)
    return await orchestrator.full_consultation(
        symptoms=req.symptoms,
        patient_history=req.patient_history,
        patient_profile=req.patient_profile,
        rag_service=rag,
    )
