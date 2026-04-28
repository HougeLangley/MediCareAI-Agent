"""Multi-Agent Medical Collaboration System.

Implements the PROPOSAL.md Agent architecture:
- DiagnosisAgent: symptom analysis with Tool Use + structured output
- PlanningAgent: treatment planning with care plan persistence
- MonitoringAgent: follow-up tracking
- MasterAgent: intent recognition + task routing
- AgentOrchestrator: coordinates the full multi-agent workflow

All agents use the unified LLM service with Tool Use and JSON Schema output.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.models.agent import AgentSession, AgentSessionStatus, AgentSessionType, AgentTask
from app.services.llm import LLMResponse, LLMService
from app.tools.registry import GLOBAL_REGISTRY


# ---------------------------------------------------------------------------
# Structured Output Schemas
# ---------------------------------------------------------------------------

class DiagnosisReport(BaseModel):
    """Structured diagnosis report — PROPOSAL §5.2."""

    primary_diagnosis: str = Field(..., description="Most likely diagnosis")
    differential_diagnoses: list[str] = Field(default_factory=list)
    confidence: str = Field(..., pattern="^(high|medium|low)$")
    severity: str = Field(..., pattern="^(mild|moderate|severe|emergency)$")
    key_findings: list[str] = Field(default_factory=list)
    recommended_tests: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    contraindications: list[str] = Field(default_factory=list)
    follow_up_required: bool = Field(default=False)
    follow_up_timeline: str = Field(default="")
    red_flags: list[str] = Field(default_factory=list)
    knowledge_sources: list[str] = Field(default_factory=list)
    disclaimer: str = Field(
        default="本报告由 AI 生成，仅供参考，不能替代专业医疗诊断。"
    )


class TreatmentPlan(BaseModel):
    """Structured treatment plan."""

    title: str
    goals: list[str] = Field(default_factory=list)
    medications: list[dict[str, Any]] = Field(default_factory=list)
    non_pharmacological: list[str] = Field(default_factory=list)
    follow_up_schedule: list[dict[str, Any]] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    confidence: str = Field(default="medium", pattern="^(high|medium|low)$")


class MonitoringAssessment(BaseModel):
    """Structured monitoring assessment."""

    current_status: str = Field(..., pattern="^(stable|improving|deteriorating|critical)$")
    trend_analysis: str = ""
    alerts: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    next_follow_up: str = ""


# ---------------------------------------------------------------------------
# AgentResult
# ---------------------------------------------------------------------------

@dataclass
class AgentResult:
    """Standardized agent output."""

    agent_type: str
    content: str | dict[str, Any]
    confidence: str | None = None
    structured_output: BaseModel | None = None
    tool_calls_used: list[dict[str, Any]] | None = None
    session_id: str | None = None


# ---------------------------------------------------------------------------
# Master Agent — Intent Recognition + Task Routing
# ---------------------------------------------------------------------------

class MasterAgent:
    """The 'medical director' Agent.

    Receives natural language input, classifies intent, and routes
to the appropriate specialized Agent.
    """

    SYSTEM_PROMPT = """You are MasterAgent, the medical director of a multi-agent healthcare system.

ROLE:
- Analyze the user's message and determine their intent.
- Route to the correct specialized agent.
- If the input is ambiguous, ask clarifying questions.

INTENT CATEGORIES:
- "diagnosis": Patient reports symptoms, asks about a condition, or seeks a diagnosis
- "planning": Patient asks about treatment, medication, follow-up, or care plans
- "monitoring": Patient reports updates on an existing condition, asks about recovery
- "consultation": Complex multi-step request that may need diagnosis + planning
- "general": General medical knowledge question (not personal)
- "escalation": Patient expresses urgency, emergency, or requests a real doctor

OUTPUT FORMAT:
Respond with a JSON object:
{
  "intent": "diagnosis|planning|monitoring|consultation|general|escalation",
  "confidence": "high|medium|low",
  "reasoning": "brief explanation of why this intent was chosen",
  "clarifying_question": "null or a question if more info is needed"
}

RULES:
- Never assume emergency unless explicitly stated or clear red flags present.
- If the user says "我咳嗽一周了", intent is "diagnosis".
- If the user says "药吃完了怎么办", intent is "planning".
- If the user says "有没有好转", intent is "monitoring".
- If the user says "帮我安排复查并提醒我", intent is "consultation".
"""

    def __init__(self, provider: str | None = None) -> None:
        self.provider = provider

    async def classify_intent(self, user_input: str) -> dict[str, Any]:
        """Classify user intent and return routing decision."""
        async with async_session_maker() as db:
            llm = LLMService(provider=self.provider, db=db)
            resp = await llm.chat(
                messages=[{"role": "user", "content": user_input}],
                system_prompt=self.SYSTEM_PROMPT,
                temperature=0.1,
                max_tokens=512,
            )
            try:
                return json.loads(resp.content)
            except json.JSONDecodeError:
                # Fallback
                return {
                    "intent": "diagnosis",
                    "confidence": "low",
                    "reasoning": "Parse error, defaulting to diagnosis",
                    "clarifying_question": None,
                }


# ---------------------------------------------------------------------------
# Diagnosis Agent — Tool Use + Structured Output
# ---------------------------------------------------------------------------

class DiagnosisAgent:
    """Analyzes symptoms with Tool Use and produces structured diagnosis reports.

    Workflow:
    1. Receive symptoms
    2. Call LLM with tools (query_patient_history, search_medical_knowledge)
    3. LLM decides what info it needs; tools are executed
    4. Collect all context
    5. Generate structured DiagnosisReport via generate_structured()
    """

    SYSTEM_PROMPT = """You are DiagnosisAgent, an expert diagnostic AI.

ROLE:
- Analyze patient symptoms and available context
- Use tools to gather missing information (patient history, knowledge base)
- When you have enough information, generate a structured diagnosis

AVAILABLE TOOLS:
- search_medical_knowledge: Search clinical guidelines and literature
- query_patient_history: Retrieve patient's past medical cases
- check_drug_interactions: Check drug safety (if medications mentioned)
- generate_structured_diagnosis: Generate the final structured report

WORKFLOW:
1. First, gather context by calling tools if needed.
2. Then call generate_structured_diagnosis with ALL collected information.
3. Do NOT give a free-text diagnosis — always use the structured report tool.

SAFETY:
- Flag emergency conditions immediately
- Never dismiss patient concerns
- Include appropriate disclaimers
"""

    def __init__(self, provider: str | None = None) -> None:
        self.provider = provider

    async def analyze(
        self,
        symptoms: str,
        patient_id: str | None = None,
        patient_history: str | None = None,
        test_results: str | None = None,
        session_id: str | None = None,
    ) -> AgentResult:
        """Run full diagnostic analysis with Tool Use.

        Args:
            symptoms: Patient-reported symptoms
            patient_id: Optional patient UUID for history lookup
            patient_history: Free-text medical history
            test_results: Lab/imaging results
            session_id: Agent session ID for persistence

        Returns:
            AgentResult with structured DiagnosisReport
        """
        tool_schemas = GLOBAL_REGISTRY.list_schemas()

        # Build initial message
        user_msg = f"患者主诉: {symptoms}"
        if patient_history:
            user_msg += f"\n病史: {patient_history}"
        if test_results:
            user_msg += f"\n检查结果: {test_results}"
        if patient_id:
            user_msg += f"\n患者ID: {patient_id} (可调用 query_patient_history 查询)"

        messages: list[dict[str, str]] = [{"role": "user", "content": user_msg}]
        all_tool_calls: list[dict[str, Any]] = []

        # Multi-turn tool use loop (max 3 rounds)
        async with async_session_maker() as db:
            llm = LLMService(provider=self.provider, db=db)

            for _round in range(3):
                resp = await llm.chat_with_tools(
                    messages=messages,
                    tools=tool_schemas,
                    system_prompt=self.SYSTEM_PROMPT,
                    temperature=0.2,
                    max_tokens=2048,
                    tool_choice="auto",
                )

                if resp.tool_calls:
                    # Execute tools
                    messages.append({
                        "role": "assistant",
                        "content": resp.content or "",
                        "tool_calls": [
                            {
                                "id": tc["id"],
                                "type": "function",
                                "function": {
                                    "name": tc["name"],
                                    "arguments": json.dumps(tc["arguments"]),
                                },
                            }
                            for tc in resp.tool_calls
                        ],
                    })

                    for tc in resp.tool_calls:
                        result = await GLOBAL_REGISTRY.execute(
                            tc["name"], tc["arguments"]
                        )
                        all_tool_calls.append({
                            "tool": tc["name"],
                            "arguments": tc["arguments"],
                            "result": result,
                        })
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": json.dumps(result, ensure_ascii=False),
                        })
                else:
                    # No more tool calls — we have the final answer
                    break

            # Try to parse structured output from the final response
            content = resp.content or ""
            structured = None
            try:
                # The LLM should have called generate_structured_diagnosis,
                # but if not, try to parse JSON from content
                if content.strip().startswith("{"):
                    data = json.loads(content)
                    structured = DiagnosisReport.model_validate(data)
                else:
                    # Force structured generation
                    structured = await llm.generate_structured(
                        messages=messages,
                        output_schema=DiagnosisReport,
                        temperature=0.2,
                        max_tokens=2048,
                    )
            except Exception:
                structured = None

            # Persist session if requested
            if session_id:
                await self._update_session(
                    session_id=session_id,
                    messages=messages,
                    tool_calls=all_tool_calls,
                    structured=structured.model_dump() if structured else None,
                )

            return AgentResult(
                agent_type="diagnosis",
                content=structured.model_dump() if structured else content,
                structured_output=structured,
                tool_calls_used=all_tool_calls,
                session_id=session_id,
            )

    async def _update_session(
        self,
        session_id: str,
        messages: list[dict[str, str]],
        tool_calls: list[dict[str, Any]],
        structured: dict[str, Any] | None,
    ) -> None:
        """Persist session state to database."""
        async with async_session_maker() as db:
            from sqlalchemy import select
            stmt = select(AgentSession).where(AgentSession.id == uuid.UUID(session_id))
            result = await db.execute(stmt)
            session = result.scalar_one_or_none()
            if session:
                session.context = {
                    "messages": messages,
                    "collected_info": {},
                }
                session.tool_calls = tool_calls
                if structured:
                    session.structured_output = structured
                session.updated_at = datetime.now(timezone.utc)
                await db.commit()


# ---------------------------------------------------------------------------
# Planning Agent
# ---------------------------------------------------------------------------

class PlanningAgent:
    """Generates treatment plans with structured output."""

    SYSTEM_PROMPT = """You are PlanningAgent, an expert treatment planning AI.

ROLE:
- Generate evidence-based treatment plans
- Recommend medications with dosing when appropriate
- Suggest lifestyle modifications
- Plan follow-up schedule

OUTPUT: Always use the structured treatment plan format.
"""

    def __init__(self, provider: str | None = None) -> None:
        self.provider = provider

    async def plan(
        self,
        diagnosis: str | dict[str, Any],
        patient_profile: dict[str, Any] | None = None,
        constraints: list[str] | None = None,
        session_id: str | None = None,
    ) -> AgentResult:
        """Generate structured treatment plan."""
        async with async_session_maker() as db:
            llm = LLMService(provider=self.provider, db=db)

            diag_text = json.dumps(diagnosis, ensure_ascii=False) if isinstance(diagnosis, dict) else diagnosis
            user_msg = f"诊断: {diag_text}"
            if patient_profile:
                user_msg += f"\n患者信息: {json.dumps(patient_profile, ensure_ascii=False)}"
            if constraints:
                user_msg += f"\n约束: {', '.join(constraints)}"

            structured = await llm.generate_structured(
                messages=[{"role": "user", "content": user_msg}],
                output_schema=TreatmentPlan,
                system_prompt=self.SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=2048,
            )

            return AgentResult(
                agent_type="planning",
                content=structured.model_dump(),
                structured_output=structured,
                session_id=session_id,
            )


# ---------------------------------------------------------------------------
# Monitoring Agent
# ---------------------------------------------------------------------------

class MonitoringAgent:
    """Tracks patient progress with structured assessment."""

    SYSTEM_PROMPT = """You are MonitoringAgent, a patient follow-up AI.

ROLE:
- Analyze patient-reported outcomes
- Detect deterioration or improvement trends
- Generate alerts when thresholds are crossed

OUTPUT: Always use the structured monitoring assessment format.
"""

    def __init__(self, provider: str | None = None) -> None:
        self.provider = provider

    async def check(
        self,
        patient_updates: str,
        baseline_status: str | None = None,
        current_plan: str | None = None,
        session_id: str | None = None,
    ) -> AgentResult:
        """Run monitoring check with structured output."""
        async with async_session_maker() as db:
            llm = LLMService(provider=self.provider, db=db)

            user_msg = f"患者最新反馈: {patient_updates}"
            if baseline_status:
                user_msg += f"\n基线状态: {baseline_status}"
            if current_plan:
                user_msg += f"\n当前计划: {current_plan}"

            structured = await llm.generate_structured(
                messages=[{"role": "user", "content": user_msg}],
                output_schema=MonitoringAssessment,
                system_prompt=self.SYSTEM_PROMPT,
                temperature=0.2,
                max_tokens=1536,
            )

            return AgentResult(
                agent_type="monitoring",
                content=structured.model_dump(),
                structured_output=structured,
                session_id=session_id,
            )


# ---------------------------------------------------------------------------
# Agent Orchestrator
# ---------------------------------------------------------------------------

class AgentOrchestrator:
    """Orchestrates multi-agent workflow per PROPOSAL architecture.

    Typical flow:
    1. MasterAgent classifies intent
    2. DiagnosisAgent → analyze with Tool Use
    3. PlanningAgent → generate treatment plan
    4. MonitoringAgent → schedule follow-up
    """

    def __init__(self, provider: str | None = None) -> None:
        self.master = MasterAgent(provider=provider)
        self.diagnosis = DiagnosisAgent(provider=provider)
        self.planning = PlanningAgent(provider=provider)
        self.monitoring = MonitoringAgent(provider=provider)

    async def route(
        self,
        user_input: str,
        patient_id: str | None = None,
        patient_history: str | None = None,
    ) -> dict[str, Any]:
        """Route user input to the correct Agent based on intent.

        This is the main entry point for Agent interactions.
        """
        # Step 1: Intent classification
        intent_result = await self.master.classify_intent(user_input)
        intent = intent_result.get("intent", "diagnosis")

        # Create a session for tracking
        session = await self._create_session(
            user_id=uuid.UUID(patient_id) if patient_id else None,
            session_type=AgentSessionType(intent.upper()),
            intent=intent,
        )
        session_id = str(session.id) if session else None

        # Step 2: Route to appropriate Agent
        if intent == "diagnosis":
            result = await self.diagnosis.analyze(
                symptoms=user_input,
                patient_id=patient_id,
                patient_history=patient_history,
                session_id=session_id,
            )
            return {
                "intent": intent_result,
                "agent": "diagnosis",
                "session_id": session_id,
                "result": result.content if isinstance(result.content, dict) else {"raw": result.content},
                "tool_calls_used": result.tool_calls_used,
            }

        elif intent == "planning":
            result = await self.planning.plan(
                diagnosis=user_input,
                session_id=session_id,
            )
            return {
                "intent": intent_result,
                "agent": "planning",
                "session_id": session_id,
                "result": result.content if isinstance(result.content, dict) else {"raw": result.content},
            }

        elif intent == "monitoring":
            result = await self.monitoring.check(
                patient_updates=user_input,
                session_id=session_id,
            )
            return {
                "intent": intent_result,
                "agent": "monitoring",
                "session_id": session_id,
                "result": result.content if isinstance(result.content, dict) else {"raw": result.content},
            }

        elif intent == "escalation":
            await self._escalate_session(session_id, "Patient requested human doctor")
            return {
                "intent": intent_result,
                "agent": "escalation",
                "session_id": session_id,
                "message": "已为您转接人工医生，请稍候。",
            }

        else:
            # General or consultation — run full flow
            diag_result = await self.diagnosis.analyze(
                symptoms=user_input,
                patient_id=patient_id,
                patient_history=patient_history,
                session_id=session_id,
            )
            plan_result = await self.planning.plan(
                diagnosis=diag_result.content if isinstance(diag_result.content, dict) else {"diagnosis": str(diag_result.content)},
                session_id=session_id,
            )
            mon_result = await self.monitoring.check(
                patient_updates=f"初次诊断: {user_input}",
                baseline_status=diag_result.content if isinstance(diag_result.content, str) else None,
                current_plan=plan_result.content if isinstance(plan_result.content, str) else None,
                session_id=session_id,
            )
            return {
                "intent": intent_result,
                "agent": "consultation",
                "session_id": session_id,
                "diagnosis": diag_result.content if isinstance(diag_result.content, dict) else {"raw": diag_result.content},
                "treatment_plan": plan_result.content if isinstance(plan_result.content, dict) else {"raw": plan_result.content},
                "monitoring": mon_result.content if isinstance(mon_result.content, dict) else {"raw": mon_result.content},
                "disclaimer": (
                    "以上内容仅供参考，不能替代专业医疗建议。"
                    "请始终咨询合格的医疗专业人员。"
                ),
            }

    async def _create_session(
        self,
        user_id: uuid.UUID | None,
        session_type: AgentSessionType,
        intent: str | None = None,
    ) -> AgentSession | None:
        """Create a new AgentSession in the database."""
        try:
            async with async_session_maker() as db:
                session = AgentSession(
                    user_id=user_id,
                    session_type=session_type,
                    status=AgentSessionStatus.ACTIVE,
                    intent=intent,
                    context={"messages": [], "collected_info": {}},
                    tool_calls=[],
                )
                db.add(session)
                await db.commit()
                await db.refresh(session)
                return session
        except Exception:
            return None

    async def _escalate_session(self, session_id: str | None, reason: str) -> None:
        """Mark session as escalated to human doctor."""
        if not session_id:
            return
        try:
            async with async_session_maker() as db:
                from sqlalchemy import select
                stmt = select(AgentSession).where(AgentSession.id == uuid.UUID(session_id))
                result = await db.execute(stmt)
                session = result.scalar_one_or_none()
                if session:
                    session.status = AgentSessionStatus.ESCALATED
                    session.escalation_reason = reason
                    session.completed_at = datetime.now(timezone.utc)
                    await db.commit()
        except Exception:
            pass
