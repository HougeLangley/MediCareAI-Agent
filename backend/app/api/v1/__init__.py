"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import auth, health, llm, users

router = APIRouter()
router.include_router(health.router, prefix="/health", tags=["Health"])
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(llm.router, prefix="/llm", tags=["LLM"])
router.include_router(users.router, prefix="/users", tags=["Users"])
