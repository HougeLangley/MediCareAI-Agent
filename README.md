# 🏥 MediCareAI-Agent

> **Multi-Agent Autonomous Medical Collaboration System**
>
> Patient-driven + AI-assisted + Doctor-validated healthcare platform, reimagined for the Agent era.

---

## 🎯 Vision

MediCareAI-Agent is not a chatbot. It is a **team of specialized medical agents** that:

- **Diagnose** — Analyze symptoms with multi-path RAG and external knowledge
- **Plan** — Create personalized follow-up and treatment schedules
- **Monitor** — Proactively track patient recovery and alert on anomalies
- **Collaborate** — Route complex cases to the right doctor with full context

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) |
| Task Queue | Celery + Redis |
| Database | PostgreSQL 17 + pgvector |
| AI/LLM | OpenAI-compatible multi-provider (GLM / DeepSeek / Kimi / Qwen) |
| Auth | JWT + Role-based (Patient / Doctor / Admin / Guest) |
| Deploy | Docker Compose → VPS (production) |
| Monitor | Prometheus + Sentry |

## 🚀 Quick Start

### 1. Clone & Configure

```bash
git clone https://github.com/houge-langley/MediCareAI-Agent.git
cd MediCareAI-Agent
cp .env.example .env
# Edit .env with your real API keys and secrets
```

### 2. Local Development (Docker)

```bash
docker compose up -d
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### 3. Run Tests

```bash
cd backend
pip install -e ".[dev]"
pytest -q
```

## 📋 Development Workflow

```
💻 Local Dev          📡 Push               🔧 VPS Production
┌──────────────┐    ┌──────────┐    ┌──────────────┐
│ Edit code      │──────────▶│ git push │──────────▶│ git pull   │
│ Write tests    │    │  origin  │    │ docker     │
│ Run locally    │    │  main     │    │ compose up │
└──────────────┘    └──────────┘    └──────────────┘
       ▲                                          │
       │         ❌ Build fails / bug               │
       └──────────────────────────────────────────┘
```

## 📝 Architecture

See [`PROPOSAL.md`](./PROPOSAL.md) for the full architecture proposal (v1.0.0).

## 📝 License

[MIT](LICENSE) © 2026 Houge Langley
