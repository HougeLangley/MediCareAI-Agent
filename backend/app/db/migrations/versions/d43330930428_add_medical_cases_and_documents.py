"""add_medical_cases_and_documents

Revision ID: d43330930428
Revises: 87fbf7eb3cbc
Create Date: 2026-04-28 21:03:03.662319

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd43330930428'
down_revision: Union[str, Sequence[str], None] = '87fbf7eb3cbc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create medical_cases and medical_documents tables."""
    # Create medical_cases
    op.create_table(
        'medical_cases',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('ACTIVE', 'CLOSED', 'ARCHIVED', name='casestatus'), nullable=False),
        sa.Column('diagnosis_ai', sa.Text(), nullable=True),
        sa.Column('diagnosis_doctor', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['patient_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_medical_cases_doctor_id'), 'medical_cases', ['doctor_id'], unique=False)
    op.create_index(op.f('ix_medical_cases_patient_id'), 'medical_cases', ['patient_id'], unique=False)

    # Create medical_documents
    op.create_table(
        'medical_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('case_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('document_type', sa.Enum('REPORT', 'PRESCRIPTION', 'IMAGE', 'LAB_RESULT', 'DISCHARGE_SUMMARY', 'OTHER', name='documenttype'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('content_text', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['case_id'], ['medical_cases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_medical_documents_case_id'), 'medical_documents', ['case_id'], unique=False)


def downgrade() -> None:
    """Drop medical_cases and medical_documents tables."""
    op.drop_index(op.f('ix_medical_documents_case_id'), table_name='medical_documents')
    op.drop_table('medical_documents')
    op.drop_index(op.f('ix_medical_cases_patient_id'), table_name='medical_cases')
    op.drop_index(op.f('ix_medical_cases_doctor_id'), table_name='medical_cases')
    op.drop_table('medical_cases')
    # Drop enum types created by PostgreSQL
    sa.Enum(name='casestatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='documenttype').drop(op.get_bind(), checkfirst=True)
