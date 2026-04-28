"""Agent Tool framework.

Import this module to ensure all medical tools are registered.
"""

from app.tools.base import SimpleTool, Tool, ToolError
from app.tools.medical import (
    check_drug_interactions,
    generate_structured_diagnosis,
    query_patient_history,
    search_medical_knowledge,
)
from app.tools.registry import GLOBAL_REGISTRY, ToolRegistry, register_tool

__all__ = [
    "Tool",
    "SimpleTool",
    "ToolError",
    "ToolRegistry",
    "GLOBAL_REGISTRY",
    "register_tool",
    "search_medical_knowledge",
    "query_patient_history",
    "check_drug_interactions",
    "generate_structured_diagnosis",
]
