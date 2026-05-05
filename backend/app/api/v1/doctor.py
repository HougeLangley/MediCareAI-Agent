"""Doctor endpoints for patient management and case review.

Provides:
- Dashboard stats
- Patient list
- Case detail with Agent summary
- Natural language instructions
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUserContext, require_role
from app.db.session import get_db
from app.models.agent import AgentSession
from app.models.medical_case import MedicalCase, CaseStatus
from app.models.user import User, UserRole
from app.schemas.medical_case import MedicalCaseResponse

router = APIRouter()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class DoctorStatsResponse:
    """Dashboard statistics for doctor."""

    pending_count: int
    new_messages: int
    followup_due: int
    data_shares: int


class PatientSummaryResponse:
    """Patient summary for doctor list."""

    id: str
    name: str
    avatar: str | None
    last_activity: str
    agent_summary: str
    status: str
    risk_level: str | None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/stats")
async def get_dashboard_stats(
    ctx: CurrentUserContext = Depends(),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """Get doctor dashboard statistics."""
    if not ctx.user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Count pending cases assigned to this doctor
    stmt = select(func.count(MedicalCase.id)).where(
        MedicalCase.assigned_doctor_id == ctx.user.id,
        MedicalCase.status == CaseStatus.PENDING
    )
    result = await db.execute(stmt)
    pending_count = result.scalar() or 0

    # For now, return demo-like stats based on actual data
    return {
        "pending_count": pending_count,
        "new_messages": 0,  # TODO: implement message counting
        "followup_due": 0,  # TODO: implement follow-up tracking
        "data_shares": 0,   # TODO: implement data sharing tracking
    }


@router.get("/cases")
async def list_doctor_cases(
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    ctx: CurrentUserContext = Depends(),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """List patients/cases for doctor."""
    if not ctx.user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    stmt = select(MedicalCase).where(
        MedicalCase.assigned_doctor_id == ctx.user.id
    ).order_by(MedicalCase.updated_at.desc()).offset(skip).limit(limit)

    if status_filter:
        try:
            stmt = stmt.where(MedicalCase.status == CaseStatus(status_filter))
        except ValueError:
            pass

    result = await db.execute(stmt)
    cases = result.scalars().all()

    patients = []
    for case in cases:
        # Get patient info
        patient_stmt = select(User).where(User.id == case.patient_id)
        patient_result = await db.execute(patient_stmt)
        patient = patient_result.scalar_one_or_none()

        # Get latest Agent session for summary
        session_stmt = select(AgentSession).where(
            AgentSession.patient_id == str(case.patient_id)
        ).order_by(AgentSession.created_at.desc()).limit(1)
        session_result = await db.execute(session_stmt)
        latest_session = session_result.scalar_one_or_none()

        agent_summary = ""
        if latest_session and latest_session.structured_output:
            if isinstance(latest_session.structured_output, dict):
                agent_summary = latest_session.structured_output.get("summary", "")
            else:
                agent_summary = str(latest_session.structured_output)
        if not agent_summary:
            agent_summary = case.description[:100] + "..." if case.description else "暂无摘要"

        patients.append({
            "id": str(case.id),
            "name": patient.name if patient else "未知患者",
            "avatar": None,
            "last_activity": case.updated_at.isoformat() if case.updated_at else "",
            "agent_summary": agent_summary,
            "status": case.status.value if case.status else "pending",
            "risk_level": "medium",  # TODO: calculate from case data
        })

    return patients


@router.get("/cases/{case_id}")
async def get_case_detail(
    case_id: str,
    ctx: CurrentUserContext = Depends(),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get detailed case information for doctor review."""
    if not ctx.user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    import uuid
    stmt = select(MedicalCase).where(MedicalCase.id == uuid.UUID(case_id))
    result = await db.execute(stmt)
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Get patient info
    patient_stmt = select(User).where(User.id == case.patient_id)
    patient_result = await db.execute(patient_stmt)
    patient = patient_result.scalar_one_or_none()

    # Get Agent sessions for this patient
    session_stmt = select(AgentSession).where(
        AgentSession.patient_id == str(case.patient_id)
    ).order_by(AgentSession.created_at.desc())
    session_result = await db.execute(session_stmt)
    sessions = session_result.scalars().all()

    # Build timeline from sessions
    timeline = []
    for session in sessions:
        timeline.append({
            "time": session.created_at.isoformat() if session.created_at else "",
            "type": session.session_type.value if session.session_type else "unknown",
            "intent": session.intent,
            "summary": session.structured_output.get("summary", "") if isinstance(session.structured_output, dict) else "",
        })

    return {
        "id": str(case.id),
        "patient_id": str(case.patient_id),
        "patient_name": patient.name if patient else "未知患者",
        "title": case.title,
        "description": case.description,
        "diagnosis": case.diagnosis,
        "agent_summary": case.ai_summary or "",
        "structured_report": case.structured_data,
        "status": case.status.value if case.status else "pending",
        "timeline": timeline,
        "created_at": case.created_at.isoformat() if case.created_at else "",
        "updated_at": case.updated_at.isoformat() if case.updated_at else "",
    }


@router.post("/cases/{case_id}/plan")
async def send_plan_instruction(
    case_id: str,
    instruction: dict[str, str],
    ctx: CurrentUserContext = Depends(),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Send natural language instruction to Agent for case planning."""
    if not ctx.user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # TODO: Implement actual Agent instruction processing
    # For now, return a placeholder response
    return {
        "tasks_created": [
            {"description": f"已创建任务: {instruction.get('instruction', '')}", "due_date": None}
        ],
        "message": "指令已接收，Agent 正在处理中...",
    }
