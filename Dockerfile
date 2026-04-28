# ==========================================
# MediCareAI-Agent Backend
# Multi-stage build with optimal layer caching
# ==========================================

FROM python:3.12-slim AS builder

WORKDIR /app

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ==========================================
# 核心优化：先复制仅依赖文件，利用镜像缓存
# 只有 pyproject.toml 变更时才重新 pip install
# 代码变更不会触发重新安装依赖
# ==========================================
COPY backend/pyproject.toml ./pyproject.toml
COPY README.md /README.md

# 创建临时空 app 目录，满足 pyproject.toml 中 packages=["app"] 的安装需求
RUN mkdir -p /app/app && touch /app/app/__init__.py

# 安装依赖（利用 Docker layer cache）
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e ".[dev]" \
    || pip install --no-cache-dir -e "."

# 清除临时 app 目录，准备复制真实代码
RUN rm -rf /app/app

# --- Production stage ---
FROM python:3.12-slim AS production

WORKDIR /app

# Runtime deps only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code (仅代码，不带 pyproject.toml 依赖安装)
COPY backend/app ./app
COPY backend/pyproject.toml .
COPY backend/alembic.ini ./alembic.ini

# Non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser \
    && chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
