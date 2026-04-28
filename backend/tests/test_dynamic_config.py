"""Tests for DynamicConfigService."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import SystemSetting
from app.services.config import DynamicConfigService


@pytest.mark.asyncio
async def test_get_str_existing(db_session: AsyncSession) -> None:
    setting = SystemSetting(key="test.string", value="hello", is_sensitive=False)
    db_session.add(setting)
    await db_session.commit()

    result = await DynamicConfigService.get_str(db_session, "test.string", default="fallback")
    assert result == "hello"


@pytest.mark.asyncio
async def test_get_str_missing_returns_default(db_session: AsyncSession) -> None:
    result = await DynamicConfigService.get_str(db_session, "test.missing", default="fallback")
    assert result == "fallback"


@pytest.mark.asyncio
async def test_get_int_parses_correctly(db_session: AsyncSession) -> None:
    db_session.add(SystemSetting(key="test.int", value="42"))
    await db_session.commit()

    result = await DynamicConfigService.get_int(db_session, "test.int", default=0)
    assert result == 42


@pytest.mark.asyncio
async def test_get_int_invalid_returns_default(db_session: AsyncSession) -> None:
    db_session.add(SystemSetting(key="test.bad", value="not_a_number"))
    await db_session.commit()

    result = await DynamicConfigService.get_int(db_session, "test.bad", default=99)
    assert result == 99


@pytest.mark.asyncio
async def test_get_bool_variants(db_session: AsyncSession) -> None:
    for key, value, expected in [
        ("test.true1", "true", True),
        ("test.true2", "1", True),
        ("test.true3", "yes", True),
        ("test.false1", "false", False),
        ("test.false2", "0", False),
        ("test.false3", "no", False),
    ]:
        db_session.add(SystemSetting(key=key, value=value))
    await db_session.commit()

    for key, _, expected in [
        ("test.true1", None, True),
        ("test.true2", None, True),
        ("test.true3", None, True),
        ("test.false1", None, False),
        ("test.false2", None, False),
        ("test.false3", None, False),
    ]:
        result = await DynamicConfigService.get_bool(db_session, key)
        assert result is expected


@pytest.mark.asyncio
async def test_get_json_parses_list(db_session: AsyncSession) -> None:
    db_session.add(SystemSetting(key="test.list", value='["a", "b"]'))
    await db_session.commit()

    result = await DynamicConfigService.get_json(db_session, "test.list", default=[])
    assert result == ["a", "b"]


@pytest.mark.asyncio
async def test_get_json_invalid_returns_default(db_session: AsyncSession) -> None:
    db_session.add(SystemSetting(key="test.bad_json", value="not json"))
    await db_session.commit()

    result = await DynamicConfigService.get_json(db_session, "test.bad_json", default={"x": 1})
    assert result == {"x": 1}


@pytest.mark.asyncio
async def test_guest_session_ttl_hours_convenience(db_session: AsyncSession) -> None:
    db_session.add(SystemSetting(key="guest.session_ttl_hours", value="48"))
    await db_session.commit()

    result = await DynamicConfigService.guest_session_ttl_hours(db_session)
    assert result == 48


@pytest.mark.asyncio
async def test_guest_session_ttl_hours_default(db_session: AsyncSession) -> None:
    result = await DynamicConfigService.guest_session_ttl_hours(db_session)
    assert result == 24


@pytest.mark.asyncio
async def test_cors_origins_json_list(db_session: AsyncSession) -> None:
    db_session.add(SystemSetting(key="cors.origins", value='["https://example.com"]'))
    await db_session.commit()

    result = await DynamicConfigService.cors_origins(db_session)
    assert result == ["https://example.com"]


@pytest.mark.asyncio
async def test_cors_origins_default(db_session: AsyncSession) -> None:
    result = await DynamicConfigService.cors_origins(db_session)
    assert result == ["*"]
