"""Multi-Agent Medical Collaboration System.

Three specialized agents:
1. DiagnosisAgent — symptom analysis & differential diagnosis
2. PlanningAgent — treatment planning & drug recommendations
3. MonitoringAgent — follow-up tracking & alert generation

All agents use the unified LLM service with role-specific prompts.
"""

from dataclasses import dataclass
from typing import Any

from app.services.llm import LLMService
from app.services.rag import RAGService


@dataclass
class AgentResult:
    """Standardized agent output."""

    agent_type: str
    content: str
    confidence: str | None = None
    recommendations: list[str] | None = None
    warnings: list[str] | None = None
    sources_used: list[str] | None = None


class DiagnosisAgent:
    """Analyzes patient symptoms and provides differential diagnosis."""

    SYSTEM_PROMPT = """You are DiagnosisAgent, an expert diagnostic AI in a multi-agent medical system.

ROLE:
- Analyze patient symptoms, history, and test results
- Provide structured differential diagnosis
- Flag urgent / emergency conditions requiring immediate attention
- Suggest appropriate diagnostic tests to confirm/rule out conditions

OUTPUT FORMAT:
1. **Primary Diagnosis** (most likely)
2. **Differential Diagnoses** (ranked by probability)
3. **Red Flags** (urgent symptoms requiring immediate care)
4. **Recommended Tests** (to confirm diagnosis)
5. **Confidence Level**: High / Medium / Low

RULES:
- Always include a disclaimer that this is AI-assisted analysis, not a definitive diagnosis
- Be specific about what information would increase confidence
- Never dismiss patient concerns
- Use medical terminology but explain for patient understanding
"""

    def __init__(self, provider: str | None = None) -> None:
        self.llm = LLMService(provider=provider)  # type: ignore[arg-type]

    async def analyze(
        self,
        symptoms: str,
        patient_history: str | None = None,
        test_results: str | None = None,
        use_rag: bool = True,
        rag_service: RAGService | None = None,
    ) -> AgentResult:
        """Run diagnostic analysis.

        Args:
            symptoms: Patient-reported symptoms.
            patient_history: Medical history (optional).
            test_results: Lab/imaging results (optional).
            use_rag: Whether to retrieve from knowledge base.
            rag_service: RAG service instance for retrieval.

        Returns:
            AgentResult with diagnosis content.
        """
        context = ""
        sources: list[str] = []

        if use_rag and rag_service:
            rag_result = await rag_service.query(
                query=f"症状: {symptoms}",
                doc_type=None,
                top_k=3,
            )
            if rag_result["retrieved_chunks"] > 0:
                context = f"\n\n参考知识库资料：\n{rag_result['answer']}"
                sources = [s["title"] for s in rag_result["sources"]]

        user_msg = f"""症状: {symptoms}
"""
        if patient_history:
            user_msg += f"\n病史: {patient_history}"
        if test_results:
            user_msg += f"\n检查结果: {test_results}"
        if context:
            user_msg += context

        resp = await self.llm.chat(
            messages=[{"role": "user", "content": user_msg}],
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=2048,
        )

        return AgentResult(
            agent_type="diagnosis",
            content=resp.content,
            sources_used=sources or None,
        )


class PlanningAgent:
    """Generates treatment plans and drug recommendations."""

    SYSTEM_PROMPT = """You are PlanningAgent, an expert treatment planning AI.

ROLE:
- Generate evidence-based treatment plans
- Recommend medications with dosing (when appropriate)
- Suggest lifestyle modifications
- Plan follow-up schedule

OUTPUT FORMAT:
1. **Treatment Goals**
2. **Medication Plan** (if applicable): drug name, dosage, frequency, duration
3. **Non-Pharmacological Interventions**
4. **Follow-up Plan**: when and what to monitor
5. **Red Flags**: when to seek immediate care
6. **Confidence Level**: High / Medium / Low

RULES:
- Always verify drug interactions when multiple medications suggested
- Include contraindications and side effect warnings
- Adapt recommendations to patient age, pregnancy status, comorbidities
- This is AI-assisted planning — must be reviewed by a licensed physician
"""

    def __init__(self, provider: str | None = None) -> None:
        self.llm = LLMService(provider=provider)  # type: ignore[arg-type]

    async def plan(
        self,
        diagnosis: str,
        patient_profile: dict[str, Any] | None = None,
        constraints: list[str] | None = None,
        use_rag: bool = True,
        rag_service: RAGService | None = None,
    ) -> AgentResult:
        """Generate treatment plan.

        Args:
            diagnosis: Confirmed or suspected diagnosis.
            patient_profile: Age, weight, allergies, comorbidities, etc.
            constraints: Treatment constraints (e.g., "pregnant", "diabetic").
            use_rag: Whether to retrieve guidelines.
            rag_service: RAG service for guideline retrieval.

        Returns:
            AgentResult with treatment plan.
        """
        context = ""
        sources: list[str] = []

        if use_rag and rag_service:
            rag_result = await rag_service.query(
                query=f"治疗方案: {diagnosis}",
                doc_type=None,
                top_k=3,
            )
            if rag_result["retrieved_chunks"] > 0:
                context = f"\n\n参考指南：\n{rag_result['answer']}"
                sources = [s["title"] for s in rag_result["sources"]]

        user_msg = f"诊断: {diagnosis}"
        if patient_profile:
            user_msg += f"\n患者信息: {patient_profile}"
        if constraints:
            user_msg += f"\n约束条件: {', '.join(constraints)}"
        if context:
            user_msg += context

        resp = await self.llm.chat(
            messages=[{"role": "user", "content": user_msg}],
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=2048,
        )

        return AgentResult(
            agent_type="planning",
            content=resp.content,
            sources_used=sources or None,
        )


class MonitoringAgent:
    """Tracks patient progress and generates follow-up alerts."""

    SYSTEM_PROMPT = """You are MonitoringAgent, a patient follow-up and monitoring AI.

ROLE:
- Analyze patient-reported outcomes between visits
- Detect deterioration or improvement trends
- Generate alerts for healthcare providers when thresholds are crossed
- Adjust monitoring frequency based on risk level

OUTPUT FORMAT:
1. **Current Status**: Stable / Improving / Deteriorating / Critical
2. **Trend Analysis**: comparison with baseline
3. **Alerts**: list of triggered alerts (if any)
4. **Recommendations**: actions for patient or provider
5. **Next Follow-up**: recommended timing

RULES:
- Be proactive about safety — err on the side of caution
- Clearly distinguish between patient self-management actions and provider-required actions
- Use simple language for patient-facing summaries
"""

    def __init__(self, provider: str | None = None) -> None:
        self.llm = LLMService(provider=provider)  # type: ignore[arg-type]

    async def check(
        self,
        patient_updates: str,
        baseline_status: str | None = None,
        current_plan: str | None = None,
    ) -> AgentResult:
        """Run monitoring check.

        Args:
            patient_updates: New symptoms, vitals, or concerns reported.
            baseline_status: Previous assessment baseline.
            current_plan: Current treatment plan being followed.

        Returns:
            AgentResult with monitoring assessment.
        """
        user_msg = f"患者最新反馈: {patient_updates}"
        if baseline_status:
            user_msg += f"\n基线状态: {baseline_status}"
        if current_plan:
            user_msg += f"\n当前治疗计划: {current_plan}"

        resp = await self.llm.chat(
            messages=[{"role": "user", "content": user_msg}],
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=1536,
        )

        # Parse confidence from content
        confidence = None
        if "关键" in resp.content or "critical" in resp.content.lower():
            confidence = "critical"
        elif "改善" in resp.content or "improving" in resp.content.lower():
            confidence = "improving"

        return AgentResult(
            agent_type="monitoring",
            content=resp.content,
            confidence=confidence,
        )


class AgentOrchestrator:
    """Orchestrates multi-agent workflow.

    Typical flow:
    1. DiagnosisAgent → analyze symptoms
    2. PlanningAgent → generate treatment plan
    3. MonitoringAgent → schedule follow-up
    """

    def __init__(self, provider: str | None = None) -> None:
        self.diagnosis = DiagnosisAgent(provider=provider)
        self.planning = PlanningAgent(provider=provider)
        self.monitoring = MonitoringAgent(provider=provider)

    async def full_consultation(
        self,
        symptoms: str,
        patient_history: str | None = None,
        patient_profile: dict[str, Any] | None = None,
        rag_service: RAGService | None = None,
    ) -> dict[str, Any]:
        """Run complete multi-agent consultation.

        Args:
            symptoms: Patient symptoms.
            patient_history: Medical history.
            patient_profile: Demographics, allergies, etc.
            rag_service: RAG service for knowledge retrieval.

        Returns:
            Combined results from all three agents.
        """
        # Step 1: Diagnosis
        diag_result = await self.diagnosis.analyze(
            symptoms=symptoms,
            patient_history=patient_history,
            use_rag=True,
            rag_service=rag_service,
        )

        # Step 2: Planning (based on diagnosis)
        plan_result = await self.planning.plan(
            diagnosis=diag_result.content,
            patient_profile=patient_profile,
            use_rag=True,
            rag_service=rag_service,
        )

        # Step 3: Monitoring setup
        mon_result = await self.monitoring.check(
            patient_updates=f"初次诊断: {symptoms}",
            baseline_status=diag_result.content,
            current_plan=plan_result.content,
        )

        return {
            "diagnosis": {
                "content": diag_result.content,
                "sources": diag_result.sources_used,
            },
            "treatment_plan": {
                "content": plan_result.content,
                "sources": plan_result.sources_used,
            },
            "monitoring": {
                "content": mon_result.content,
                "confidence": mon_result.confidence,
            },
            "disclaimer": (
                "以上内容仅供参考，不能替代专业医疗建议。"
                "请始终咨询合格的医疗专业人员。"
            ),
        }
