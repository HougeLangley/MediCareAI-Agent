# Admin 仪表盘 API 去硬编码实施计划

> **For Hermes:** 使用 subagent-driven-development 或手动逐步实施。

**Goal:** 将 MediCareAI Admin 仪表盘后端 API 全面改为配置化（数据库驱动），消除业务层硬编码；完善 Admin API 覆盖所有配置管理需求；编写完整测试验证。

**Architecture:** 业务配置统一存储在 `system_settings` 表，Admin API 提供 CRUD；业务代码通过 `DynamicConfigService` 读取；LLM Provider 配置已存在 `llm_provider_configs` 表，修复 endpoint 使其真正读取数据库配置。

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, Pydantic, pytest

---

## 现状诊断

### 已完成的 (✅)
- `LLMProviderConfig` 模型 + Admin CRUD API (加密存储 API key)
- `SystemSetting` 模型 + Admin CRUD API (缺少 DELETE)
- Alembic migrations 已存在

### 硬编码问题 (🔴)
1. `app/services/llm.py:31-37` — `_PROVIDER_DEFAULTS` 硬编码 5 个 provider 的 base_url + default_model
2. `app/api/v1/llm.py:48,78,109` — `LLMService()` 未传入 `db`，无法读取数据库配置，只能 fallback 到硬编码
3. `app/core/config.py:83-85` — `guest_session_ttl_hours=24`, `guest_max_messages=10` 等业务参数在环境变量中硬编码
4. `app/api/deps.py` — guest session 创建使用硬编码参数，未从 SystemSetting 读取

### Admin API 缺口 (🟡)
1. System Setting 缺少 DELETE 接口
2. 缺少 LLM Provider 连通性测试接口
3. 缺少 Admin Dashboard 统计接口
4. 缺少配置导入/导出接口

---

## 实施步骤

### Task 1: 修复 LLM endpoint 的 db session 传递

**Objective:** 让 `/api/v1/llm/*` endpoint 能正确读取数据库中的 provider 配置

**Files:**
- Modify: `app/api/v1/llm.py`
- Modify: `app/services/llm.py` (移除不必要的硬编码 fallback)

**Step 1: 修改 llm.py endpoint**

所有 endpoint 需要注入 `AsyncSession`:

```python
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.llm import get_llm_service

@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    service = await get_llm_service(db, platform=current_user.platform)
    ...
```

**Step 2: 修改 LLMService 初始化**

当没有配置时，`get_llm_service` 应该报错提示 admin 去配置，而不是 fallback 到硬编码。

**验证:** `pytest tests/test_llm.py -v`

---

### Task 2: 将 _PROVIDER_DEFAULTS 改为 ProviderTemplate

**Objective:** 提供默认 provider 模板，但允许 admin 修改

**Files:**
- Create: `app/models/config.py` — `ProviderTemplate` model (或复用 SystemSetting)
- Modify: `app/services/llm.py` — 从 SystemSetting 读取 "provider_template_*"
- Create: Alembic migration

**方案 A (推荐):** 使用 SystemSetting，key 格式 `provider_defaults.openai.base_url`
**方案 B:** 新增 `ProviderTemplate` 表

选择方案 A（简单，不新增表）：

```python
# 初始化时插入默认模板（migration 或 seed 脚本）
default_templates = [
    {"key": "provider_defaults.openai.base_url", "value": "https://api.openai.com/v1"},
    {"key": "provider_defaults.openai.default_model", "value": "gpt-4o-mini"},
    ...
]
```

**验证:** Admin 可以通过 API 修改模板值，业务代码实时生效。

---

### Task 3: 创建 DynamicConfigService

**Objective:** 统一从 SystemSetting 读取业务配置，带缓存

**Files:**
- Create: `app/services/config.py`
- Modify: `app/core/config.py` — 保留基础设施配置，移除业务配置
- Modify: `app/api/deps.py` — guest session 使用动态配置

```python
# app/services/config.py
class DynamicConfigService:
    """Read configuration from system_settings table."""

    @staticmethod
    async def get_int(db: AsyncSession, key: str, default: int) -> int:
        ...

    @staticmethod
    async def get_str(db: AsyncSession, key: str, default: str) -> str:
        ...

    @staticmethod
    async def get_bool(db: AsyncSession, key: str, default: bool) -> bool:
        ...

    @staticmethod
    async def get_json(db: AsyncSession, key: str, default: dict) -> dict:
        ...
```

**业务配置清单（迁移到 SystemSetting）:**
- `guest.session_ttl_hours` = 24
- `guest.max_messages` = 10
- `cors.origins` = ["*"] (JSON)
- `app.max_upload_size_mb` = 10
- `rag.chunk_size` = 500
- `rag.chunk_overlap` = 50

**验证:** `pytest tests/test_dynamic_config.py -v`

---

### Task 4: 完善 Admin API

**Objective:** 补全缺失的 Admin 接口

**Files:**
- Modify: `app/api/v1/admin.py`

**4.1 System Setting DELETE:**
```python
@router.delete("/settings/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_setting(key: str, db: AsyncSession = Depends(get_db)) -> None:
    ...
```

**4.2 LLM Provider 连通性测试:**
```python
@router.post("/llm-providers/{provider}/test")
async def test_llm_provider(provider: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Test provider connectivity by listing models."""
    ...
```

**4.3 Admin Dashboard 统计:**
```python
@router.get("/dashboard/stats")
async def dashboard_stats(db: AsyncSession = Depends(get_db)) -> dict:
    """Return counts: users, sessions, messages, providers, documents, etc."""
    ...
```

**4.4 批量配置更新:**
```python
@router.patch("/settings/batch")
async def batch_update_settings(
    items: list[SystemSettingUpdate], db: AsyncSession = Depends(get_db)
) -> list[SystemSettingResponse]:
    ...
```

**验证:** 使用 `curl` 或 pytest 逐个验证新接口

---

### Task 5: 编写 Admin API 测试

**Objective:** 覆盖所有 Admin 接口的单元测试和集成测试

**Files:**
- Create: `tests/test_admin.py`
- Create: `tests/test_dynamic_config.py`
- Create: `tests/conftest.py` (如缺少)

**测试覆盖:**
1. LLM Provider CRUD (create, list, get, update, delete, uniqueness)
2. System Setting CRUD (create, list, get, update, delete, batch)
3. LLM Provider 连通性测试 (mock OpenAI client)
4. Dashboard 统计 (验证返回字段)
5. 权限测试 (非 admin 返回 403)
6. API key 加密验证 (数据库中不是明文)
7. DynamicConfigService (读取、默认值、缓存)

**验证:** `pytest tests/ -v --tb=short`

---

### Task 6: 本地验证 & 部署

**Objective:** 确保所有变更在本地可运行

**Step 1: 数据库 migration**
```bash
cd backend
alembic revision --autogenerate -m "add provider templates and config seeds"
alembic upgrade head
```

**Step 2: 启动服务测试**
```bash
uv run uvicorn app.main:app --reload --port 8000
```

**Step 3: 使用 curl 验证**
```bash
# 1. 获取 token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login ...)

# 2. 测试 LLM provider CRUD
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/admin/llm-providers

# 3. 测试 System Setting
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/admin/settings

# 4. 测试 Dashboard
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/admin/dashboard/stats
```

**Step 4: 提交代码**
```bash
git add .
git commit -m "feat: configurable admin dashboard api + dynamic config service"
git push origin main
```

---

## 配置分层原则 (重要)

实施后，配置分层如下：

| 层级 | 存储位置 | 示例 | 修改方式 |
|------|---------|------|---------|
| 基础设施 | 环境变量 / .env | DB_URL, REDIS_URL, SECRET_KEY | 重启服务 |
| 业务配置 | system_settings 表 | guest_max_messages, cors_origins | Admin API 实时生效 |
| 运行时密钥 | llm_provider_configs 表 | API keys (加密) | Admin API 实时生效 |
| 默认模板 | system_settings 表 | provider_defaults.* | Admin API 实时生效 |

**原则:** 只有真正基础设施相关的才保留在环境变量，所有业务可调参数全部配置化。

---

## 验收标准

- [ ] `/api/v1/admin/llm-providers` CRUD 完整可用
- [ ] `/api/v1/admin/settings` CRUD + DELETE + batch 完整可用
- [ ] `/api/v1/admin/llm-providers/{provider}/test` 可测试连通性
- [ ] `/api/v1/admin/dashboard/stats` 返回正确统计
- [ ] LLM chat endpoint 正确读取数据库配置（不依赖硬编码）
- [ ] Guest mode 参数可从 SystemSetting 动态调整
- [ ] 所有 Admin 接口有 pytest 覆盖
- [ ] 非 admin 用户访问返回 403
