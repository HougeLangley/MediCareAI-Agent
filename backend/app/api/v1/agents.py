"""Multi-Agent Medical Collaboration endpoints.

New design per PROPOSAL.md:
- /route      → MasterAgent intent classification + auto-routing
- /diagnose   → DiagnosisAgent with Tool Use + structured output
- /plan       → PlanningAgent with structured treatment plan
- /monitor    → MonitoringAgent with structured assessment
- /consult    → Full multi-agent consultation
- /sessions   → Agent session management
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, CurrentUserContext, require_role
from app.db.session import async_session_maker, get_db
from app.models.agent import AgentSession, AgentSessionStatus
from app.models.user import User, UserRole
from app.services.agents import AgentOrchestrator, DiagnosisAgent, MonitoringAgent, PlanningAgent
from app.services.llm import LLMService
from app.services.rag import RAGService

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class RouteRequest(BaseModel):
    """Natural language input for MasterAgent routing."""

    message: str = Field(..., min_length=1, max_length=2000, description="Patient message")
    patient_id: str | None = Field(None, description="Patient UUID if authenticated")
    patient_history: str | None = Field(None, max_length=5000)
    provider: str | None = None


class DiagnosisRequest(BaseModel):
    """Symptom analysis request with Tool Use."""

    symptoms: str = Field(..., min_length=5, max_length=2000)
    patient_id: str | None = Field(None, description="Patient UUID for history lookup")
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
    patient_id: str | None = Field(None)
    patient_history: str | None = Field(None, max_length=5000)
    patient_profile: dict[str, Any] | None = None
    provider: str | None = None


class SessionListResponse(BaseModel):
    """Agent session list item."""

    id: str
    session_type: str
    status: str
    intent: str | None
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/route", status_code=status.HTTP_200_OK)
async def route_request(
    req: RouteRequest,
    ctx: CurrentUserContext,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """MasterAgent: classify intent and route to the appropriate Agent."""
    orchestrator = AgentOrchestrator(provider=req.provider)
    patient_id = req.patient_id or (str(ctx.user.id) if ctx.user else None)
    return await orchestrator.route(
        user_input=req.message,
        patient_id=patient_id,
        patient_history=req.patient_history,
    )


@router.post("/diagnose", status_code=status.HTTP_200_OK)
async def diagnose(
    req: DiagnosisRequest,
    ctx: CurrentUserContext,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """DiagnosisAgent: structured diagnosis with Tool Use."""
    agent = DiagnosisAgent(provider=req.provider)
    result = await agent.analyze(
        symptoms=req.symptoms,
        patient_id=req.patient_id or (str(ctx.user.id) if ctx.user else None),
        patient_history=req.patient_history,
        test_results=req.test_results,
    )
    return {
        "agent": "diagnosis",
        "structured": result.structured_output.model_dump() if result.structured_output else None,
        "content": result.content,
        "tool_calls_used": result.tool_calls_used,
        "session_id": result.session_id,
    }


@router.post("/plan", status_code=status.HTTP_200_OK)
async def plan_treatment(
    req: PlanningRequest,
    ctx: CurrentUserContext,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """PlanningAgent: structured treatment plan."""
    agent = PlanningAgent(provider=req.provider)
    result = await agent.plan(
        diagnosis=req.diagnosis,
        patient_profile=req.patient_profile,
        constraints=req.constraints,
    )
    return {
        "agent": "planning",
        "structured": result.structured_output.model_dump() if result.structured_output else None,
        "content": result.content,
    }


@router.post("/monitor", status_code=status.HTTP_200_OK)
async def monitor(
    req: MonitoringRequest,
    ctx: CurrentUserContext,
) -> dict[str, Any]:
    """MonitoringAgent: structured monitoring assessment."""
    agent = MonitoringAgent(provider=req.provider)
    result = await agent.check(
        patient_updates=req.patient_updates,
        baseline_status=req.baseline_status,
        current_plan=req.current_plan,
    )
    return {
        "agent": "monitoring",
        "structured": result.structured_output.model_dump() if result.structured_output else None,
        "content": result.content,
    }


@router.post("/consult", status_code=status.HTTP_200_OK)
async def full_consultation(
    req: ConsultationRequest,
    ctx: CurrentUserContext,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Full multi-agent consultation (diagnosis + plan + monitoring)."""
    orchestrator = AgentOrchestrator(provider=req.provider)
    patient_id = req.patient_id or (str(ctx.user.id) if ctx.user else None)
    return await orchestrator.route(
        user_input=req.symptoms,
        patient_id=patient_id,
        patient_history=req.patient_history,
    )


@router.get("/sessions", response_model=list[SessionListResponse])
async def list_sessions(
    status_filter: str | None = Query(None, alias="status"),
    type_filter: str | None = Query(None, alias="type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> list[SessionListResponse]:
    """List Agent sessions (admin/doctor only).

    Query params:
    - status: active, completed, escalated, failed
    - type: diagnosis, planning, monitoring, consultation
    """
    stmt = select(AgentSession).order_by(AgentSession.created_at.desc())

    if status_filter:
        stmt = stmt.where(AgentSession.status == AgentSessionStatus(status_filter))
    if type_filter:
        from app.models.agent import AgentSessionType
        stmt = stmt.where(AgentSession.session_type == AgentSessionType(type_filter.upper()))

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    return [
        SessionListResponse(
            id=str(s.id),
            session_type=s.session_type.value,
            status=s.status.value,
            intent=s.intent,
            created_at=s.created_at.isoformat() if s.created_at else "",
            updated_at=s.updated_at.isoformat() if s.updated_at else "",
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(require_role(UserRole.ADMIN, UserRole.DOCTOR)),
) -> dict[str, Any]:
    """Get full Agent session details."""
    import uuid as uuid_module

    stmt = select(AgentSession).where(AgentSession.id == uuid_module.UUID(session_id))
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "id": str(session.id),
        "session_type": session.session_type.value,
        "status": session.status.value,
        "intent": session.intent,
        "context": session.context,
        "tool_calls": session.tool_calls,
        "structured_output": session.structured_output,
        "escalation_reason": session.escalation_reason,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }


# ---------------------------------------------------------------------------
# Streaming SSE endpoints (backend-ready, frontend to integrate later)
# ---------------------------------------------------------------------------

@router.get("/route/stream")
async def route_stream(
    message: str,
    ctx: CurrentUserContext,
    db: AsyncSession = Depends(get_db),
    patient_id: str | None = None,
    patient_history: str | None = None,
    provider: str | None = None,
) -> StreamingResponse:
    """MasterAgent intent classification + streaming response via SSE (GET for EventSource).

    Frontend connects via:
        const es = new EventSource(`/api/v1/agents/route/stream?message=...`)

    Events:
        1. intent classification result (JSON)
        2. streaming LLM response chunks
        3. [DONE] marker
    """
    async def event_generator():
        # Step 1: Intent classification (non-streaming)
        master = AgentOrchestrator(provider=provider)
        actual_patient_id = patient_id or (str(ctx.user.id) if ctx.user else None)
        intent_result = await master.master.classify_intent(message)
        intent = intent_result.get("intent", "diagnosis")

        yield f"event: intent\ndata: {json.dumps(intent_result)}\n\n"

        # Step 2: Streaming response via LLM
        async with async_session_maker() as db_stream:
            llm = LLMService(provider=provider, platform=ctx.platform, db=db_stream)

            system_prompt = (
                "You are MediCareAI-Agent, a medical AI assistant. "
                "Provide helpful, accurate medical information. "
                "Always include a disclaimer that this is not a substitute for professional medical advice."
            )

            messages = [{"role": "user", "content": message}]
            if patient_history:
                messages.insert(0, {"role": "system", "content": f"Patient history: {patient_history}"})

            try:
                async for chunk in llm.chat_stream(
                    messages=messages,
                    system_prompt=system_prompt,
                    temperature=0.3,
                    max_tokens=2048,
                ):
                    yield f"data: {chunk}\n\n"
            except Exception as e:
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
