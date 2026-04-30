"""add_audit_logs_table

Revision ID: eaae3e1d5d98
Revises: f8a2c3d4e5b6
Create Date: 2026-04-30 23:16:30.953263

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'eaae3e1d5d98'
down_revision: Union[str, Sequence[str], None] = 'f8a2c3d4e5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create audit_logs table for admin operation tracking.

    Only admin-side operations are logged; patient-side operations
    are intentionally excluded for privacy protection.
    """
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('user_email', sa.String(length=255), nullable=True),
        sa.Column('user_role', sa.String(length=20), nullable=True),
        sa.Column(
            'action',
            sa.Enum(
                'LOGIN', 'LOGOUT', 'PASSWORD_CHANGE', 'ROLE_SWITCH',
                'DOCTOR_VERIFY', 'DOCTOR_REJECT',
                'DOCUMENT_CREATE', 'DOCUMENT_UPDATE', 'DOCUMENT_DELETE',
                'DOCUMENT_REVIEW', 'DOCUMENT_TOGGLE',
                'SETTINGS_CHANGE',
                'LLM_CONFIG_CREATE', 'LLM_CONFIG_UPDATE', 'LLM_CONFIG_DELETE', 'LLM_CONFIG_TEST',
                'USER_CREATE', 'USER_UPDATE', 'USER_DELETE',
                'AGENT_SESSION', 'TOOL_CALL',
                name='auditactiontype',
            ),
            nullable=False,
        ),
        sa.Column(
            'resource_type',
            sa.Enum(
                'USER', 'DOCTOR', 'DOCUMENT', 'SYSTEM_SETTING',
                'LLM_PROVIDER', 'AGENT_SESSION', 'UNKNOWN',
                name='auditresourcetype',
            ),
            nullable=False,
        ),
        sa.Column('resource_id', sa.String(length=100), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'], unique=False)
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'], unique=False)
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'], unique=False)
    op.create_index('ix_audit_logs_success', 'audit_logs', ['success'], unique=False)
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'], unique=False)


def downgrade() -> None:
    """Drop audit_logs table."""
    op.drop_index('ix_audit_logs_user_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_success', table_name='audit_logs')
    op.drop_index('ix_audit_logs_resource_type', table_name='audit_logs')
    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
    op.drop_index('ix_audit_logs_action', table_name='audit_logs')
    op.drop_table('audit_logs')
