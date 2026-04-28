"""add_platform_to_llm_provider_configs

Revision ID: 87fbf7eb3cbc
Revises: 91ac6552bc85
Create Date: 2026-04-28 20:27:39.010922

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '87fbf7eb3cbc'
down_revision: Union[str, Sequence[str], None] = '91ac6552bc85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add platform column and update unique constraint."""
    # Add platform column (nullable, default NULL = global)
    op.add_column('llm_provider_configs', sa.Column('platform', sa.String(length=20), nullable=True))

    # Remove old unique constraint on provider alone
    op.drop_constraint('llm_provider_configs_provider_key', 'llm_provider_configs', type_='unique')

    # Add new composite unique constraint (provider, platform)
    op.create_unique_constraint('uq_provider_platform', 'llm_provider_configs', ['provider', 'platform'])

    # Create index for platform filtering
    op.create_index('ix_llm_provider_configs_platform', 'llm_provider_configs', ['platform'], unique=False)


def downgrade() -> None:
    """Revert platform changes."""
    op.drop_index('ix_llm_provider_configs_platform', table_name='llm_provider_configs')
    op.drop_constraint('uq_provider_platform', 'llm_provider_configs', type_='unique')
    op.create_unique_constraint('llm_provider_configs_provider_key', 'llm_provider_configs', ['provider'])
    op.drop_column('llm_provider_configs', 'platform')
