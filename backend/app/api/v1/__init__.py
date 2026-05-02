"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import admin, agents, auth, email, health, llm, medical_cases, notifications, rag, upload, users

router = APIRouter()
router.include_router(health.router, prefix="/health", tags=["Health"])
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(llm.router, prefix="/llm", tags=["LLM"])
router.include_router(rag.router, prefix="/rag", tags=["RAG / Knowledge Base"])
router.include_router(agents.router, prefix="/agents", tags=["Agents"])
router.include_router(admin.router, prefix="/admin", tags=["Admin"])
router.include_router(notifications.router, prefix="/admin/notifications", tags=["Admin Notifications"])
router.include_router(email.router, prefix="/admin/email", tags=["Admin Email"])
router.include_router(users.router, prefix="/users", tags=["Users"])
router.include_router(medical_cases.router, prefix="/medical-cases", tags=["Medical Cases"])
router.include_router(upload.router, prefix="/upload", tags=["File Upload"])
