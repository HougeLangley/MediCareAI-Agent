"""add_agent_sessions_tasks_and_health_profiles

Revision ID: 280f5fca0584
Revises: d43330930428
Create Date: 2026-04-28 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '280f5fca0584'
down_revision: Union[str, Sequence[str], None] = 'd43330930428'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create agent_sessions, agent_tasks, and patient_health_profiles tables."""
    # Create agent_sessions
    op.create_table(
        'agent_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('guest_session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_type', sa.Enum('DIAGNOSIS', 'PLANNING', 'MONITORING', 'CONSULTATION', name='agentsessiontype'), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'COMPLETED', 'ESCALATED', 'FAILED', 'TIMEOUT', name='agentsessionstatus'), nullable=False),
        sa.Column('intent', sa.String(length=100), nullable=True),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tool_calls', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('structured_output', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('escalated_to', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('escalation_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['escalated_to'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['guest_session_id'], ['guest_sessions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_agent_sessions_user_id', 'agent_sessions', ['user_id'], unique=False)
    op.create_index('ix_agent_sessions_status', 'agent_sessions', ['status'], unique=False)
    op.create_index('ix_agent_sessions_type_status', 'agent_sessions', ['session_type', 'status'], unique=False)

    # Create agent_tasks
    op.create_table(
        'agent_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_type', sa.String(length=50), nullable=False),
        sa.Column('task_name', sa.String(length=200), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('input_params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tool_calls', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('dependencies', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['agent_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_agent_tasks_session_id', 'agent_tasks', ['session_id'], unique=False)
    op.create_index('ix_agent_tasks_status', 'agent_tasks', ['status'], unique=False)

    # Create patient_health_profiles
    op.create_table(
        'patient_health_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('health_summary', sa.Text(), nullable=True),
        sa.Column('disease_patterns', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('medication_history', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('risk_factors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_by_agent', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('patient_id')
    )
    op.create_index('ix_patient_health_profiles_patient_id', 'patient_health_profiles', ['patient_id'], unique=False)


def downgrade() -> None:
    """Drop agent tables."""
    op.drop_index('ix_patient_health_profiles_patient_id', table_name='patient_health_profiles')
    op.drop_table('patient_health_profiles')
    op.drop_index('ix_agent_tasks_status', table_name='agent_tasks')
    op.drop_index('ix_agent_tasks_session_id', table_name='agent_tasks')
    op.drop_table('agent_tasks')
    op.drop_index('ix_agent_sessions_type_status', table_name='agent_sessions')
    op.drop_index('ix_agent_sessions_status', table_name='agent_sessions')
    op.drop_index('ix_agent_sessions_user_id', table_name='agent_sessions')
    op.drop_table('agent_sessions')
    sa.Enum(name='agentsessiontype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='agentsessionstatus').drop(op.get_bind(), checkfirst=True)
