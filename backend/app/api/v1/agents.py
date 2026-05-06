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

import asyncio
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
# Helper: DiagnosisReport → Markdown
# ---------------------------------------------------------------------------

def _diagnosis_report_to_markdown(report: dict[str, Any]) -> str:
    """Convert DiagnosisReport dict to Markdown for frontend rendering."""
    lines: list[str] = []
    _unknown = "\u672a\u77e5"
    _pending = "\u5f85\u5b9a"

    lines.append("### \ud83c\udfe5 \u521d\u6b65\u8bca\u65ad")
    lines.append("**" + report.get("primary_diagnosis", _unknown) + "**")
    lines.append("")

    if report.get("differential_diagnoses"):
        lines.append("### \ud83d\udd0d \u9274\u522b\u8bca\u65ad")
        for d in report["differential_diagnoses"]:
            lines.append("- " + str(d))
        lines.append("")

    severity = report.get("severity", _unknown)
    severity_emoji = {"mild": "\ud83d\udfe2", "moderate": "\ud83d\udfe1", "severe": "\ud83d\udd34", "emergency": "\u26d4"}.get(severity, "")
    lines.append("**\u4e25\u91cd\u7a0b\u5ea6**: " + severity_emoji + " " + severity)
    lines.append("**\u7f6e\u4fe1\u5ea6**: " + report.get("confidence", _unknown))
    lines.append("")

    if report.get("key_findings"):
        lines.append("### \ud83d\udccb \u5173\u952e\u53d1\u73b0")
        for f in report["key_findings"]:
            lines.append("- " + str(f))
        lines.append("")

    if report.get("recommended_tests"):
        lines.append("### \ud83e\uddea \u63a8\u8350\u68c0\u67e5")
        for t in report["recommended_tests"]:
            lines.append("- " + str(t))
        lines.append("")

    if report.get("recommended_actions"):
        lines.append("### \ud83d\udc8a \u5efa\u8bae\u63aa\u65bd")
        for a in report["recommended_actions"]:
            lines.append("- " + str(a))
        lines.append("")

    if report.get("contraindications"):
        lines.append("### \u26a0\ufe0f \u7981\u5fcc\u4e8b\u9879")
        for c in report["contraindications"]:
            lines.append("- " + str(c))
        lines.append("")

    if report.get("red_flags"):
        lines.append("### \ud83d\udea8 \u5371\u9669\u4fe1\u53f7\uff08\u9700\u7acb\u5373\u5c31\u533b\uff09")
        for r in report["red_flags"]:
            lines.append("- " + str(r))
        lines.append("")

    if report.get("follow_up_required"):
        lines.append("### \ud83d\udcc5 \u968f\u8bbf")
        lines.append("\u9700\u8981\u968f\u8bbf\uff0c\u65f6\u95f4: " + report.get("follow_up_timeline", _pending))
        lines.append("")

    if report.get("knowledge_sources"):
        lines.append("### \ud83d\udcda \u77e5\u8bc6\u6765\u6e90")
        for s in report["knowledge_sources"]:
            lines.append("- " + str(s))
        lines.append("")

    disclaimer = report.get("disclaimer")
    if disclaimer:
        lines.append("> " + str(disclaimer))

    return "\n".join(lines)


def _chunk_text(text: str, chunk_size: int = 80) -> list[str]:
    """Split text into chunks for SSE streaming simulation."""
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]


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
    """MasterAgent intent classification + streaming multi-agent response via SSE.

    Frontend connects via:
        const es = new EventSource(`/api/v1/agents/route/stream?message=...`)

    SSE Events:
        intent          →  MasterAgent 意图分类结果
        agent_switch    →  切换到专科 Agent
        thinking        →  Agent 分析思考过程
        tool_call       →  调用工具
        tool_result     →  工具返回结果
        text            →  流式文本片段
        structured      →  结构化诊断报告
        complete        →  流结束
        error           →  错误
    """
    async def event_generator():
        # ─── Step 1: MasterAgent 意图分类 ───
        master = AgentOrchestrator(provider=provider)
        actual_patient_id = patient_id or (str(ctx.user.id) if ctx.user else None)

        yield f"event: thinking\ndata: {json.dumps({'step': 'master', 'message': '🧠 MasterAgent 正在分析您的需求...'})}\n\n"

        intent_result = await master.master.classify_intent(message)
        intent = intent_result.get("intent", "diagnosis")
        confidence = intent_result.get("confidence", "medium")
        reasoning = intent_result.get("reasoning", "")

        yield f"event: intent\ndata: {json.dumps(intent_result)}\n\n"
        yield f"event: thinking\ndata: {json.dumps({'step': 'master_done', 'message': f'✅ 意图识别完成: {intent} (置信度: {confidence})', 'detail': reasoning})}\n\n"

        # ─── Step 2: Agent 切换 ───
        agent_name_map = {
            "diagnosis": "DiagnosisAgent 诊断专家",
            "planning": "PlanningAgent 治疗规划",
            "monitoring": "MonitoringAgent 随访监测",
            "research": "ResearchAgent 医学研究",
            "consultation": "Consultation 综合诊疗",
            "escalation": "Escalation 人工转接",
            "general": "General 通用医疗",
        }
        agent_display = agent_name_map.get(intent, agent_name_map["general"])

        yield f"event: agent_switch\ndata: {json.dumps({'agent': intent, 'agent_display': agent_display, 'message': f'🔄 正在切换到 {agent_display}...'})}\n\n"

        # ─── Step 3: 专科 Agent 处理 + 流式输出 ───
        async with async_session_maker() as db_stream:
            llm = LLMService(provider=provider, platform=ctx.platform, db=db_stream)

            # 根据意图构建专属 system prompt
            system_prompts = {
                "diagnosis": """You are DiagnosisAgent, an expert diagnostic AI physician.

ROLE:
- Analyze patient symptoms thoroughly
- Consider differential diagnoses
- Ask clarifying questions when needed
- Flag emergency conditions immediately

OUTPUT FORMAT:
Use Markdown formatting:
- **bold** for important medical terms
- bullet lists for findings/suggestions
- numbered lists for step-by-step advice
- ### headers for sections

Always include:
1. Possible causes analysis
2. Key questions to narrow down
3. Self-care recommendations
4. Red flags requiring immediate medical attention
5. Disclaimer

SAFETY: Never dismiss patient concerns. Flag emergencies.""",

                "planning": """You are PlanningAgent, an expert treatment planning AI.

ROLE:
- Generate evidence-based treatment plans
- Recommend medications with dosing when appropriate
- Suggest lifestyle modifications
- Plan follow-up schedule

OUTPUT FORMAT:
Use Markdown formatting with clear sections.""",

                "monitoring": """You are MonitoringAgent, a patient follow-up AI.

ROLE:
- Analyze patient-reported outcomes
- Detect deterioration or improvement trends
- Generate alerts when thresholds are crossed

OUTPUT FORMAT:
Use Markdown formatting.""",

                "research": """You are ResearchAgent, a medical research assistant.

ROLE:
- Synthesize medical knowledge into clear answers
- Cite sources when possible
- Distinguish evidence levels

OUTPUT FORMAT:
Use Markdown formatting.""",

                "escalation": """You are handling an escalation to human medical staff.

ROLE:
- Acknowledge the patient's request
- Provide immediate safety guidance if needed
- Explain the handoff process

Be empathetic and professional.""",

                "general": """You are MediCareAI-Agent, a helpful medical AI assistant.

ROLE:
- Provide accurate, evidence-based medical information
- Be clear and compassionate
- Always include appropriate disclaimers

OUTPUT FORMAT:
Use Markdown formatting for readability.""",
            }

            system_prompt = system_prompts.get(intent, system_prompts["general"])

            # 添加患者上下文
            messages: list[dict[str, str]] = [{"role": "user", "content": message}]
            if patient_history:
                messages.insert(0, {"role": "system", "content": f"Patient history context: {patient_history}"})

            # 真实工具调用 + 流式输出
            if intent == "diagnosis":
                _msg_start = "\ud83e\udde0 DiagnosisAgent \u6b63\u5728\u542f\u52a8\u771f\u5b9e\u8bca\u65ad\u5206\u6790..."
                yield f"event: thinking\ndata: {json.dumps({'step': 'diagnosis', 'message': _msg_start})}\n\n"

                try:
                    diag_agent = DiagnosisAgent(provider=provider)
                    result = await diag_agent.analyze(
                        symptoms=message,
                        patient_id=actual_patient_id,
                        patient_history=patient_history,
                    )

                    # 流式展示真实工具调用记录
                    if result.tool_calls_used:
                        for tc in result.tool_calls_used:
                            tool_name = tc.get("tool", "unknown")
                            args = tc.get("arguments", {})
                            _tc_msg = "\ud83d\udd0d \u6b63\u5728\u6267\u884c " + tool_name + "..."
                            yield f"event: tool_call\ndata: {json.dumps({'tool': tool_name, 'params': args, 'message': _tc_msg})}\n\n"
                            await asyncio.sleep(0.2)
                            result_data = tc.get("result", {})
                            _tr_msg = "\u2705 " + tool_name + " \u6267\u884c\u5b8c\u6210"
                            yield f"event: tool_result\ndata: {json.dumps({'tool': tool_name, 'result': result_data, 'message': _tr_msg})}\n\n"

                    _msg_analyze = "\ud83e\udde0 DiagnosisAgent \u6b63\u5728\u7efc\u5408\u5206\u6790\u5e76\u751f\u6210\u7ed3\u6784\u5316\u62a5\u544a..."
                    yield f"event: thinking\ndata: {json.dumps({'step': 'diagnosis', 'message': _msg_analyze})}\n\n"

                    # 输出结构化报告
                    if result.structured_output:
                        structured_data = result.structured_output.model_dump()
                        yield f"event: structured\ndata: {json.dumps(structured_data)}\n\n"

                        report_md = _diagnosis_report_to_markdown(structured_data)
                        for chunk in _chunk_text(report_md, chunk_size=80):
                            yield f"event: text\ndata: {json.dumps({'text': chunk})}\n\n"
                    else:
                        content = result.content if isinstance(result.content, str) else json.dumps(result.content, ensure_ascii=False)
                        for chunk in _chunk_text(content, chunk_size=80):
                            yield f"event: text\ndata: {json.dumps({'text': chunk})}\n\n"
                except Exception as e:
                    _err_msg = "\u8bca\u65ad\u5206\u6790\u5931\u8d25: " + str(e)
                    yield f"event: error\ndata: {json.dumps({'error': _err_msg})}\n\n"
                    return

            else:
                # 其他意图走通用 LLM 流
                try:
                    async for chunk in llm.chat_stream(
                        messages=messages,
                        system_prompt=system_prompt,
                        temperature=0.3,
                        max_tokens=2048,
                    ):
                        yield f"event: text\ndata: {json.dumps({'text': chunk})}\n\n"
                except Exception as e:
                    yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                    return

        yield f"event: complete\ndata: {json.dumps({'message': '✅ 响应完成'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
