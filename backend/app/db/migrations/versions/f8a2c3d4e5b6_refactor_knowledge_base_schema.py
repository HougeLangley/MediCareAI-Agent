"""refactor_knowledge_base_schema

Revision ID: f8a2c3d4e5b6
Revises: 947c66152833
Create Date: 2026-04-30 09:45:00.000000

Simplify DocType from 5 to 3 types. Add review workflow columns.
External knowledge (papers, textbooks) will be retrieved via SearXNG.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f8a2c3d4e5b6'
down_revision: Union[str, Sequence[str], None] = '947c66152833'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: simplify doc types, add review workflow."""

    # --- Step 1: Convert doc_type to VARCHAR first so we can UPDATE ---
    op.execute("ALTER TABLE documents ALTER COLUMN doc_type TYPE VARCHAR(50)")

    # --- Step 2: Migrate existing doc_type values ---
    # Map old enum values to new ones
    op.execute("""
        UPDATE documents
        SET doc_type = CASE doc_type
            WHEN 'GUIDELINE' THEN 'platform_guideline'
            WHEN 'PAPER' THEN 'platform_guideline'
            WHEN 'CASE_REPORT' THEN 'case_report'
            WHEN 'DRUG_INFO' THEN 'drug_reference'
            WHEN 'TEXTBOOK' THEN 'platform_guideline'
        END
    """)

    # --- Step 3: Drop old enum and create new one ---
    op.execute("DROP TYPE IF EXISTS doctype")
    op.execute("""
        CREATE TYPE doctype AS ENUM (
            'platform_guideline',
            'case_report',
            'drug_reference'
        )
    """)

    # --- Step 4: Convert back to new enum ---
    op.execute("ALTER TABLE documents ALTER COLUMN doc_type TYPE doctype USING doc_type::doctype")

    # --- Step 5: Drop old 'source' column, add new columns ---
    op.drop_column('documents', 'source')

    # Source tracking
    op.add_column('documents', sa.Column('source_type', sa.String(length=50), nullable=True))
    op.add_column('documents', sa.Column('source_url', sa.String(length=1000), nullable=True))
    op.add_column('documents', sa.Column('uploaded_by', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_documents_uploaded_by', 'documents', 'users', ['uploaded_by'], ['id'])

    # Review workflow
    op.add_column('documents', sa.Column('review_status', sa.String(length=50), nullable=False, server_default='approved'))
    op.add_column('documents', sa.Column('reviewed_by', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_documents_reviewed_by', 'documents', 'users', ['reviewed_by'], ['id'])
    op.add_column('documents', sa.Column('agent_review_score', sa.Float(), nullable=True))
    op.add_column('documents', sa.Column('agent_review_notes', sa.Text(), nullable=True))

    # Metadata
    op.add_column('documents', sa.Column('department', sa.String(length=100), nullable=True))
    op.add_column('documents', sa.Column('disease_tags', postgresql.ARRAY(sa.String(length=100)), nullable=True))
    op.add_column('documents', sa.Column('drug_name', sa.String(length=200), nullable=True))

    # Activation & curation
    op.add_column('documents', sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'))

    # Vectorization status
    op.add_column('documents', sa.Column('vectorized_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('documents', sa.Column('embedding_model', sa.String(length=100), nullable=True))

    # --- Step 6: Add new indexes ---
    op.create_index('ix_documents_doc_type', 'documents', ['doc_type'], unique=False)
    op.create_index('ix_documents_review_status', 'documents', ['review_status'], unique=False)
    op.create_index('ix_documents_is_active', 'documents', ['is_active'], unique=False)
    op.create_index('ix_documents_disease_tags', 'documents', ['disease_tags'], unique=False, postgresql_using='gin')

    # --- Step 7: Create document_reviews table ---
    op.create_table('document_reviews',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('reviewer_type', sa.String(length=20), nullable=False),
        sa.Column('reviewer_id', sa.UUID(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_doc_reviews_document_id', 'document_reviews', ['document_id'], unique=False)
    op.create_index('ix_doc_reviews_reviewer_type', 'document_reviews', ['reviewer_type'], unique=False)

    # --- Step 8: Add chunk-level index ---
    op.create_index('ix_chunks_document_id', 'document_chunks', ['document_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema: restore old doc types, drop new columns."""

    # Drop document_reviews table
    op.drop_index('ix_doc_reviews_reviewer_type', table_name='document_reviews')
    op.drop_index('ix_doc_reviews_document_id', table_name='document_reviews')
    op.drop_table('document_reviews')

    # Drop new indexes
    op.drop_index('ix_chunks_document_id', table_name='document_chunks')
    op.drop_index('ix_documents_disease_tags', table_name='documents', postgresql_using='gin')
    op.drop_index('ix_documents_is_active', table_name='documents')
    op.drop_index('ix_documents_review_status', table_name='documents')
    op.drop_index('ix_documents_doc_type', table_name='documents')

    # Drop new columns (reverse order of addition)
    op.drop_column('documents', 'embedding_model')
    op.drop_column('documents', 'vectorized_at')
    op.drop_column('documents', 'is_featured')
    op.drop_column('documents', 'drug_name')
    op.drop_column('documents', 'disease_tags')
    op.drop_column('documents', 'department')
    op.drop_column('documents', 'agent_review_notes')
    op.drop_column('documents', 'agent_review_score')
    op.drop_constraint('fk_documents_reviewed_by', 'documents', type_='foreignkey')
    op.drop_column('documents', 'reviewed_by')
    op.drop_column('documents', 'review_status')
    op.drop_constraint('fk_documents_uploaded_by', 'documents', type_='foreignkey')
    op.drop_column('documents', 'uploaded_by')
    op.drop_column('documents', 'source_url')
    op.drop_column('documents', 'source_type')

    # Restore old 'source' column
    op.add_column('documents', sa.Column('source', sa.String(length=500), nullable=True))

    # Restore old enum
    op.execute("ALTER TABLE documents ALTER COLUMN doc_type TYPE VARCHAR(50)")
    op.execute("DROP TYPE IF EXISTS doctype")
    op.execute("""
        CREATE TYPE doctype AS ENUM (
            'GUIDELINE', 'PAPER', 'CASE_REPORT', 'DRUG_INFO', 'TEXTBOOK'
        )
    """)
    op.execute("ALTER TABLE documents ALTER COLUMN doc_type TYPE doctype USING doc_type::doctype")

    # Revert data mapping (approximate)
    op.execute("""
        UPDATE documents
        SET doc_type = CASE doc_type
            WHEN 'platform_guideline' THEN 'GUIDELINE'
            WHEN 'case_report' THEN 'CASE_REPORT'
            WHEN 'drug_reference' THEN 'DRUG_INFO'
        END
    """)
