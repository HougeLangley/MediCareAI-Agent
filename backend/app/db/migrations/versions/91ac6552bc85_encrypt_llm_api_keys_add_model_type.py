"""encrypt_llm_api_keys_add_model_type

Revision ID: 91ac6552bc85
Revises: fe1f5fae2aac
Create Date: 2026-04-28 11:38:46.487932

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision = "91ac6552bc85"
down_revision = "fe1f5fae2aac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema: encrypt existing API keys, add model_type."""
    op.add_column("llm_provider_configs", sa.Column("api_key_encrypted", sa.Text(), nullable=True))
    op.add_column("llm_provider_configs", sa.Column("model_type", sa.String(length=50), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, api_key FROM llm_provider_configs"))

    import os
    import base64
    import hashlib
    from cryptography.fernet import Fernet

    master_key = os.getenv("API_KEY_MASTER_KEY")
    if master_key:
        key = base64.urlsafe_b64encode(hashlib.sha256(master_key.encode()).digest())
        cipher = Fernet(key)
    else:
        cipher = None

    for row in rows:
        api_key = row.api_key or ""
        if cipher and api_key:
            encrypted = cipher.encrypt(api_key.encode()).decode()
        else:
            encrypted = api_key
        conn.execute(
            sa.text("UPDATE llm_provider_configs SET api_key_encrypted = :enc, model_type = :mt WHERE id = :id"),
            {"enc": encrypted, "mt": "diagnosis", "id": row.id}
        )

    op.alter_column("llm_provider_configs", "api_key_encrypted", nullable=False)
    op.alter_column("llm_provider_configs", "model_type", nullable=False, server_default="diagnosis")
    op.drop_column("llm_provider_configs", "api_key")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("llm_provider_configs", sa.Column("api_key", sa.TEXT(), autoincrement=False, nullable=True))

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, api_key_encrypted FROM llm_provider_configs"))

    import os
    import base64
    import hashlib
    from cryptography.fernet import Fernet

    master_key = os.getenv("API_KEY_MASTER_KEY")
    if master_key:
        key = base64.urlsafe_b64encode(hashlib.sha256(master_key.encode()).digest())
        cipher = Fernet(key)
    else:
        cipher = None

    for row in rows:
        encrypted = row.api_key_encrypted or ""
        if cipher and encrypted:
            try:
                decrypted = cipher.decrypt(encrypted.encode()).decode()
            except Exception:
                decrypted = encrypted
        else:
            decrypted = encrypted
        conn.execute(
            sa.text("UPDATE llm_provider_configs SET api_key = :key WHERE id = :id"),
            {"key": decrypted, "id": row.id}
        )

    op.alter_column("llm_provider_configs", "api_key", nullable=False)
    op.drop_column("llm_provider_configs", "model_type")
    op.drop_column("llm_provider_configs", "api_key_encrypted")
