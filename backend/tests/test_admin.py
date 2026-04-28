"""Tests for Admin API endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash
from app.models.config import LLMProviderConfig, SystemSetting
from app.models.user import User, UserRole, UserStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_user(
    db: AsyncSession,
    email: str,
    password: str,
    role: UserRole,
    full_name: str = "Test User",
) -> User:
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name,
        role=role,
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _auth_header(user: User) -> dict[str, str]:
    token = create_access_token(str(user.id), platform="web")
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# LLM Provider Config Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_llm_providers_empty(client: AsyncClient, db_session: AsyncSession) -> None:
    admin = await _create_user(db_session, "admin1@test.com", "password", UserRole.ADMIN)
    response = await client.get("/api/v1/admin/llm-providers", headers=_auth_header(admin))
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_llm_provider(client: AsyncClient, db_session: AsyncSession) -> None:
    admin = await _create_user(db_session, "admin2@test.com", "password", UserRole.ADMIN)

    payload = {
        "provider": "moonshot",
        "platform": "web",
        "name": "Moonshot Web",
        "base_url": "https://api.moonshot.cn/v1",
        "api_key": "short",
        "default_model": "moonshot-v1-8k",
        "model_type": "diagnosis",
        "is_active": True,
        "is_default": True,
    }
    response = await client.post(
        "/api/v1/admin/llm-providers", json=payload, headers=_auth_header(admin)
    )
    assert response.status_code == 201
    data = response.json()
    assert data["provider"] == "moonshot"
    assert data["name"] == "Moonshot Web"
    # mask_api_key("short") -> "****" because len <= 8
    assert data["api_key_masked"] == "****"


@pytest.mark.asyncio
async def test_create_llm_provider_duplicate_conflict(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await _create_user(db_session, "admin3@test.com", "password", UserRole.ADMIN)

    payload = {
        "provider": "openai",
        "platform": None,
        "name": "OpenAI Global",
        "base_url": "https://api.openai.com/v1",
        "api_key": "***",
        "default_model": "gpt-4o",
        "model_type": "diagnosis",
    }
    r1 = await client.post("/api/v1/admin/llm-providers", json=payload, headers=_auth_header(admin))
    assert r1.status_code == 201

    r2 = await client.post("/api/v1/admin/llm-providers", json=payload, headers=_auth_header(admin))
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_get_llm_provider(client: AsyncClient, db_session: AsyncSession) -> None:
    admin = await _create_user(db_session, "admin4@test.com", "password", UserRole.ADMIN)

    config = LLMProviderConfig(
        provider="deepseek",
        platform="web",
        name="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        api_key_encrypted="enc_test",
        default_model="deepseek-chat",
        model_type="diagnosis",
    )
    db_session.add(config)
    await db_session.commit()

    response = await client.get(
        "/api/v1/admin/llm-providers/deepseek?platform=web",
        headers=_auth_header(admin),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "deepseek"


@pytest.mark.asyncio
async def test_update_llm_provider(client: AsyncClient, db_session: AsyncSession) -> None:
    admin = await _create_user(db_session, "admin5@test.com", "password", UserRole.ADMIN)

    config = LLMProviderConfig(
        provider="glm",
        platform=None,
        name="GLM",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        api_key_encrypted="enc_old",
        default_model="glm-4",
        model_type="diagnosis",
    )
    db_session.add(config)
    await db_session.commit()

    response = await client.patch(
        "/api/v1/admin/llm-providers/glm",
        json={"name": "GLM Updated", "api_key": "***"},
        headers=_auth_header(admin),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "GLM Updated"
    assert data["api_key_masked"] != ""


@pytest.mark.asyncio
async def test_delete_llm_provider(client: AsyncClient, db_session: AsyncSession) -> None:
    admin = await _create_user(db_session, "admin6@test.com", "password", UserRole.ADMIN)

    config = LLMProviderConfig(
        provider="dashscope",
        platform=None,
        name="DashScope",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key_encrypted="enc_test",
        default_model="qwen-turbo",
        model_type="diagnosis",
    )
    db_session.add(config)
    await db_session.commit()

    response = await client.delete(
        "/api/v1/admin/llm-providers/dashscope",
        headers=_auth_header(admin),
    )
    assert response.status_code == 204

    # Verify deleted
    get_resp = await client.get(
        "/api/v1/admin/llm-providers/dashscope",
        headers=_auth_header(admin),
    )
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# System Setting Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_system_settings_empty(client: AsyncClient, db_session: AsyncSession) -> None:
    admin = await _create_user(db_session, "admin7@test.com", "password", UserRole.ADMIN)
    response = await client.get("/api/v1/admin/settings", headers=_auth_header(admin))
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_system_setting(client: AsyncClient, db_session: AsyncSession) -> None:
    admin = await _create_user(db_session, "admin8@test.com", "password", UserRole.ADMIN)

    payload = {"key": "app.name", "value": "MediCareAI", "description": "App display name"}
    response = await client.post(
        "/api/v1/admin/settings", json=payload, headers=_auth_header(admin)
    )
    assert response.status_code == 201
    data = response.json()
    assert data["key"] == "app.name"
    assert data["value"] == "MediCareAI"


@pytest.mark.asyncio
async def test_create_system_setting_duplicate(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    admin = await _create_user(db_session, "admin9@test.com", "password", UserRole.ADMIN)

    payload = {"key": "app.version", "value": "1.0.0"}
    r1 = await client.post("/api/v1/admin/settings", json=payload, headers=_auth_header(admin))
    assert r1.status_code == 201

    r2 = await client.post("/api/v1/admin/settings", json=payload, headers=_auth_header(admin))
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_update_system_setting(client: AsyncClient, db_session: AsyncSession) -> None:
    admin = await _create_user(db_session, "admin10@test.com", "password", UserRole.ADMIN)

    setting = SystemSetting(key="feature.flag", value="false", description="Toggle")
    db_session.add(setting)
    await db_session.commit()

    response = await client.patch(
        "/api/v1/admin/settings/feature.flag",
        json={"value": "true"},
        headers=_auth_header(admin),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["value"] == "true"


@pytest.mark.asyncio
async def test_delete_system_setting(client: AsyncClient, db_session: AsyncSession) -> None:
    admin = await _create_user(db_session, "admin11@test.com", "password", UserRole.ADMIN)

    setting = SystemSetting(key="temp.setting", value="123")
    db_session.add(setting)
    await db_session.commit()

    response = await client.delete(
        "/api/v1/admin/settings/temp.setting",
        headers=_auth_header(admin),
    )
    assert response.status_code == 204

    get_resp = await client.get(
        "/api/v1/admin/settings/temp.setting",
        headers=_auth_header(admin),
    )
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_batch_update_settings(client: AsyncClient, db_session: AsyncSession) -> None:
    admin = await _create_user(db_session, "admin12@test.com", "password", UserRole.ADMIN)

    payload = {
        "items": [
            {"key": "batch.a", "value": "1", "description": "First"},
            {"key": "batch.b", "value": "2", "description": "Second"},
        ]
    }
    response = await client.patch(
        "/api/v1/admin/settings/batch", json=payload, headers=_auth_header(admin)
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["key"] == "batch.a"
    assert data[1]["key"] == "batch.b"

    # Re-run batch — should update existing
    payload["items"][0]["value"] = "10"
    response2 = await client.patch(
        "/api/v1/admin/settings/batch", json=payload, headers=_auth_header(admin)
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2[0]["value"] == "10"


# ---------------------------------------------------------------------------
# Dashboard Stats Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dashboard_stats(client: AsyncClient, db_session: AsyncSession) -> None:
    admin = await _create_user(db_session, "admin13@test.com", "password", UserRole.ADMIN)
    patient = await _create_user(db_session, "pat1@test.com", "password", UserRole.PATIENT)
    doctor = await _create_user(db_session, "doc1@test.com", "password", UserRole.DOCTOR)

    config = LLMProviderConfig(
        provider="openai",
        platform=None,
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        api_key_encrypted="enc",
        default_model="gpt-4o",
        is_active=True,
    )
    db_session.add(config)
    await db_session.commit()

    response = await client.get("/api/v1/admin/dashboard/stats", headers=_auth_header(admin))
    assert response.status_code == 200
    data = response.json()
    assert data["users"]["total"] >= 3
    assert data["users"]["by_role"]["admin"] >= 1
    assert data["llm_providers"]["total"] >= 1
    assert data["llm_providers"]["active"] >= 1
    assert "timestamp" in data


# ---------------------------------------------------------------------------
# Permission Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_non_admin_cannot_access_admin_endpoints(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    patient = await _create_user(db_session, "pat2@test.com", "password", UserRole.PATIENT)

    response = await client.get("/api/v1/admin/llm-providers", headers=_auth_header(patient))
    assert response.status_code == 403

    response = await client.get("/api/v1/admin/settings", headers=_auth_header(patient))
    assert response.status_code == 403

    response = await client.get("/api/v1/admin/dashboard/stats", headers=_auth_header(patient))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_doctor_cannot_access_admin_endpoints(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    doctor = await _create_user(db_session, "doc2@test.com", "password", UserRole.DOCTOR)

    response = await client.get("/api/v1/admin/llm-providers", headers=_auth_header(doctor))
    assert response.status_code == 403
