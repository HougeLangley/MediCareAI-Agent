"""Medical tools for Agent use.

These tools wrap existing backend services so Agents can:
- Search the medical knowledge base
- Query patient history
- Check drug interactions
- Generate structured reports

All tools are registered to GLOBAL_REGISTRY on import.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.tools.base import SimpleTool, Tool
from app.tools.registry import register_tool


# ---------------------------------------------------------------------------
# Parameter schemas (Pydantic → JSON Schema for LLM)
# ---------------------------------------------------------------------------

class SearchKnowledgeParams(BaseModel):
    """Parameters for search_medical_knowledge tool."""

    query: str = Field(..., description="The medical question or keywords to search", min_length=1)
    doc_type: str | None = Field(
        None,
        description="Filter by document type: platform_guideline, case_report, drug_reference",
    )
    top_k: int = Field(5, description="Number of top results to retrieve", ge=1, le=20)


class QueryPatientHistoryParams(BaseModel):
    """Parameters for query_patient_history tool."""

    patient_id: str = Field(..., description="UUID of the patient")
    limit: int = Field(5, description="Max number of recent cases to return", ge=1, le=50)
    include_documents: bool = Field(
        False, description="Whether to include attached medical documents"
    )


class CheckDrugInteractionsParams(BaseModel):
    """Parameters for check_drug_interactions tool."""

    drugs: list[str] = Field(..., description="List of drug names to check", min_length=1)
    patient_allergies: list[str] | None = Field(
        None, description="Known patient allergies or contraindications"
    )


class GenerateStructuredDiagnosisParams(BaseModel):
    """Parameters for generate_structured_diagnosis tool."""

    symptoms: str = Field(..., description="Patient-reported symptoms")
    patient_history: str | None = Field(None, description="Relevant medical history")
    test_results: str | None = Field(None, description="Lab or imaging results if available")
    knowledge_context: str | None = Field(
        None, description="Retrieved knowledge base context to cite"
    )


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

class SearchMedicalKnowledgeTool(Tool):
    """Search the medical knowledge base for relevant guidelines and literature."""

    name = "search_medical_knowledge"
    description = (
        "Search the institutional medical knowledge base for clinical guidelines, "
        "research papers, drug information, or case reports relevant to a query. "
        "Use this when you need evidence-based information to support a diagnosis or treatment plan."
    )
    parameters = SearchKnowledgeParams

    async def execute(self, query: str, doc_type: str | None = None, top_k: int = 5) -> dict[str, Any]:
        # Deferred import to avoid circular deps at module load time
        from app.services.rag import RAGService
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.db.session import async_session_maker

        async with async_session_maker() as db:
            rag = RAGService(db)
            from app.models.rag import DocType
            dt = DocType(doc_type) if doc_type else None
            result = await rag.query(query=query, doc_type=dt, top_k=top_k)
            return {
                "answer": result["answer"],
                "sources": result["sources"],
                "retrieved_chunks": result["retrieved_chunks"],
            }


class QueryPatientHistoryTool(Tool):
    """Query a patient's medical case history."""

    name = "query_patient_history"
    description = (
        "Retrieve a patient's recent medical cases, diagnoses, and attached documents. "
        "Use this to understand the patient's baseline health status, chronic conditions, "
        "previous diagnoses, and ongoing treatments before making new recommendations."
    )
    parameters = QueryPatientHistoryParams

    async def execute(
        self, patient_id: str, limit: int = 5, include_documents: bool = False
    ) -> dict[str, Any]:
        import uuid
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.db.session import async_session_maker
        from app.models.medical_case import MedicalCase, MedicalDocument

        async with async_session_maker() as db:
            stmt = (
                select(MedicalCase)
                .where(MedicalCase.patient_id == uuid.UUID(patient_id))
                .order_by(MedicalCase.created_at.desc())
                .limit(limit)
            )
            result = await db.execute(stmt)
            cases = result.scalars().all()

            case_list = []
            for case in cases:
                case_data = {
                    "id": str(case.id),
                    "title": case.title,
                    "chief_complaint": case.chief_complaint,
                    "diagnosis_doctor": case.diagnosis_doctor,
                    "status": case.status.value,
                    "created_at": case.created_at.isoformat() if case.created_at else None,
                    "updated_at": case.updated_at.isoformat() if case.updated_at else None,
                }
                if include_documents:
                    doc_stmt = select(MedicalDocument).where(
                        MedicalDocument.case_id == case.id
                    )
                    doc_result = await db.execute(doc_stmt)
                    docs = doc_result.scalars().all()
                    case_data["documents"] = [
                        {
                            "id": str(d.id),
                            "doc_type": d.doc_type.value,
                            "title": d.title,
                            "description": d.description,
                        }
                        for d in docs
                    ]
                case_list.append(case_data)

            return {
                "patient_id": patient_id,
                "case_count": len(case_list),
                "cases": case_list,
            }


class CheckDrugInteractionsTool(Tool):
    """Check for drug-drug and drug-allergy interactions."""

    name = "check_drug_interactions"
    description = (
        "Check for potential interactions between multiple drugs and known patient allergies. "
        "Use this before recommending medications, especially when the patient is on multiple drugs "
        "or has known allergies. Returns a safety assessment with warnings."
    )
    parameters = CheckDrugInteractionsParams

    async def execute(
        self, drugs: list[str], patient_allergies: list[str] | None = None
    ) -> dict[str, Any]:
        # MVP: simplified rule-based check + LLM-powered analysis placeholder
        # Future: integrate with DrugBank or similar API
        warnings: list[str] = []
        allergies = patient_allergies or []

        # Simple heuristic checks
        drug_set = {d.lower().strip() for d in drugs}

        # Known common interaction pairs (simplified MVP rules)
        interaction_pairs = [
            ({"aspirin", "warfarin"}, "Increased bleeding risk when combining aspirin with warfarin."),
            ({"metformin", "contrast"}, "Risk of lactic acidosis with contrast media in metformin patients."),
            ({"ace inhibitor", "spironolactone"}, "Risk of hyperkalemia."),
            ({"nsaid", "ace inhibitor"}, "Reduced antihypertensive effect and renal risk."),
        ]

        for pair, warning in interaction_pairs:
            if len(pair & drug_set) >= 2:
                warnings.append(warning)

        # Allergy check
        for allergy in allergies:
            for drug in drugs:
                if allergy.lower() in drug.lower():
                    warnings.append(
                        f"CRITICAL: Patient is allergic to '{allergy}' which may be related to '{drug}'."
                    )

        return {
            "drugs_checked": drugs,
            "allergies_considered": allergies,
            "interaction_warnings": warnings,
            "safety_status": "caution" if warnings else "safe",
            "disclaimer": (
                "This is an automated preliminary check. Always verify with a pharmacist "
                "or clinical drug reference before prescribing."
            ),
        }


class GenerateStructuredDiagnosisTool(Tool):
    """Generate a structured, validated diagnosis report."""

    name = "generate_structured_diagnosis"
    description = (
        "Generate a formal structured diagnosis report based on collected symptoms, "
        "patient history, test results, and retrieved medical knowledge. "
        "Use this as the final step after gathering all necessary information."
    )
    parameters = GenerateStructuredDiagnosisParams

    async def execute(
        self,
        symptoms: str,
        patient_history: str | None = None,
        test_results: str | None = None,
        knowledge_context: str | None = None,
    ) -> dict[str, Any]:
        # This tool acts as a wrapper around the LLM with a strict structured-output prompt
        from app.services.llm import LLMService
        from app.db.session import async_session_maker

        system_prompt = """You are a medical diagnostic AI. Based on the provided information,
generate a structured diagnosis report in the exact JSON format below.

REQUIRED JSON STRUCTURE:
{
  "primary_diagnosis": "string (most likely diagnosis)",
  "differential_diagnoses": ["string", "string"],
  "confidence": "high|medium|low",
  "severity": "mild|moderate|severe|emergency",
  "key_findings": ["string"],
  "recommended_tests": ["string"],
  "recommended_actions": ["string"],
  "contraindications": ["string"],
  "follow_up_required": true|false,
  "follow_up_timeline": "string (e.g., '3 days')",
  "red_flags": ["string (symptoms requiring immediate care)"],
  "knowledge_sources": ["string"]
}

RULES:
- Be specific and evidence-based.
- Always include the disclaimer that this is AI-assisted, not definitive.
- If information is insufficient, state so explicitly in key_findings.
- Output ONLY valid JSON, no markdown formatting."""

        user_msg = f"症状: {symptoms}"
        if patient_history:
            user_msg += f"\n病史: {patient_history}"
        if test_results:
            user_msg += f"\n检查结果: {test_results}"
        if knowledge_context:
            user_msg += f"\n参考知识: {knowledge_context}"

        async with async_session_maker() as db:
            llm = LLMService(db=db)
            resp = await llm.chat(
                messages=[{"role": "user", "content": user_msg}],
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=2048,
            )

            # Parse the JSON response
            import json
            try:
                report = json.loads(resp.content)
            except json.JSONDecodeError:
                # Fallback: wrap raw content
                report = {
                    "primary_diagnosis": "Parse error",
                    "raw_content": resp.content,
                    "confidence": "low",
                    "severity": "unknown",
                }

            return {
                "report": report,
                "model_used": resp.model,
                "disclaimer": (
                    "This report is generated by AI for reference only and does not "
                    "replace professional medical diagnosis."
                ),
            }


# ---------------------------------------------------------------------------
# Register all tools
# ---------------------------------------------------------------------------

search_medical_knowledge = register_tool(SearchMedicalKnowledgeTool())
query_patient_history = register_tool(QueryPatientHistoryTool())
check_drug_interactions = register_tool(CheckDrugInteractionsTool())
generate_structured_diagnosis = register_tool(GenerateStructuredDiagnosisTool())
