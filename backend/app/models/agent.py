"""Agent session and task models.

Implements the Agent Memory layer from PROPOSAL §5.3:
- Agent sessions track multi-turn interactions
- Agent tasks record tool executions
- Patient health profiles store long-term memory

These enable true multi-turn, stateful Agent workflows.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AgentSessionStatus(str, PyEnum):
    """Lifecycle states of an Agent session."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ESCALATED = "escalated"  # handed off to human doctor
    FAILED = "failed"
    TIMEOUT = "timeout"


class AgentSessionType(str, PyEnum):
    """Types of Agent sessions."""

    DIAGNOSIS = "diagnosis"
    PLANNING = "planning"
    MONITORING = "monitoring"
    CONSULTATION = "consultation"  # full multi-agent flow


class AgentSession(Base):
    """Tracks a multi-turn Agent interaction.

    This is the core of Agent Memory Layer 2 (Working Memory).
    Each session represents one coherent medical inquiry from a patient.
    """

    __tablename__ = "agent_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    guest_session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("guest_sessions.id", ondelete="SET NULL"), nullable=True
    )

    session_type: Mapped[AgentSessionType] = mapped_column(
        Enum(AgentSessionType), default=AgentSessionType.DIAGNOSIS, nullable=False
    )
    status: Mapped[AgentSessionStatus] = mapped_column(
        Enum(AgentSessionStatus), default=AgentSessionStatus.ACTIVE, nullable=False
    )

    # User's original intent (filled by Master Agent)
    intent: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Conversation context snapshot (messages, intermediate states)
    context: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=lambda: {"messages": [], "collected_info": {}}
    )

    # Tool execution history
    tool_calls: Mapped[list[dict] | None] = mapped_column(
        JSONB, nullable=True, default=list
    )

    # Structured output from the Agent (if any)
    structured_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Escalation info
    escalated_to: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    escalation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_agent_sessions_user_id", "user_id"),
        Index("ix_agent_sessions_status", "status"),
        Index("ix_agent_sessions_type_status", "session_type", "status"),
    )


class AgentTask(Base):
    """Atomic task executed within an Agent session.

    Records what the Agent did, when, and with what result.
    Used for audit, debugging, and replay.
    """

    __tablename__ = "agent_tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False
    )

    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    task_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, running, completed, failed, cancelled

    input_params: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tool_calls: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    dependencies: Mapped[list[uuid.UUID] | None] = mapped_column(
        JSONB, nullable=True
    )  # list of task IDs this depends on

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_agent_tasks_session_id", "session_id"),
        Index("ix_agent_tasks_status", "status"),
    )


class PatientHealthProfile(Base):
    """Long-term patient health profile — Agent Memory Layer 3.

    AI-generated and continuously updated summary of a patient's
    health status, disease patterns, medication history, and preferences.
    """

    __tablename__ = "patient_health_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    # AI-generated health summary paragraph
    health_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Structured data
    disease_patterns: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )  # e.g. {"recurrent_conditions": [...], "typical_severity": "mild"}
    medication_history: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )  # e.g. {"current": [...], "past": [...], "adverse_reactions": [...]}
    risk_factors: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )  # e.g. {"smoking": false, "family_history": ["diabetes"]}
    preferences: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )  # e.g. {"communication_style": "detailed", "reminder_time": "08:00"}

    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_by_agent: Mapped[str | None] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_patient_health_profiles_patient_id", "patient_id"),
    )
