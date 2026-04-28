"""Agent orchestration Celery tasks.

These handle long-running AI operations asynchronously.
"""

from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=2, default_retry_delay=10)
def run_diagnosis_agent(self, session_id: str, patient_input: str) -> dict:
    """Run diagnosis agent asynchronously.

    Args:
        session_id: Chat/session identifier
        patient_input: Raw patient message

    Returns:
        Agent result dict with diagnosis, confidence, follow-up plan
    """
    # TODO: integrate real agent logic
    return {
        "status": "completed",
        "session_id": session_id,
        "diagnosis": "placeholder",
        "confidence": 0.0,
    }
