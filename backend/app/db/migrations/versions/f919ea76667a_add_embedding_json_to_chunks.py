"""add_embedding_json_to_chunks

Revision ID: f919ea76667a
Revises: eaae3e1d5d98
Create Date: 2026-05-01 10:45:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f919ea76667a"
down_revision: Union[str, None] = "eaae3e1d5d98"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add embedding_json column for vector storage (pre-pgvector phase)."""
    op.add_column(
        "document_chunks",
        sa.Column("embedding_json", postgresql.JSONB, nullable=True),
    )
    op.create_index(
        "ix_chunks_embedding_json",
        "document_chunks",
        ["embedding_json"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Remove embedding_json column."""
    op.drop_index("ix_chunks_embedding_json", table_name="document_chunks")
    op.drop_column("document_chunks", "embedding_json")
