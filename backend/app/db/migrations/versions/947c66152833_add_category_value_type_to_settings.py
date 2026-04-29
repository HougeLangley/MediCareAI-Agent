"""add_category_value_type_options_to_system_settings

Revision ID: 947c66152833
Revises: 280f5fca0584
Create Date: 2026-04-30 07:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '947c66152833'
down_revision: Union[str, Sequence[str], None] = '280f5fca0584'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add category, value_type, options columns to system_settings."""
    op.add_column('system_settings', sa.Column('category', sa.String(length=50), nullable=False, server_default='general'))
    op.add_column('system_settings', sa.Column('value_type', sa.String(length=20), nullable=False, server_default='string'))
    op.add_column('system_settings', sa.Column('options', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove category, value_type, options columns from system_settings."""
    op.drop_column('system_settings', 'options')
    op.drop_column('system_settings', 'value_type')
    op.drop_column('system_settings', 'category')
