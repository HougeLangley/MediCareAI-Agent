# MediCareAI → MediCareAI-Agent：进入 Agent 时代的升级方案

> **版本**: v1.0.0 | **作者**: Stellara (for 苏业钦) | **日期**: 2026-04-27
>
> 基于对 `/home/houge/MediCareAI` 项目的完整代码审计与架构分析

---

## 一、现状诊断：MediCareAI 已经拥有什么

在对项目 297 个文件、18 张数据表、20+ 个服务模块进行全面扫描后，我总结出 MediCareAI 的**核心资产**：

### 1.1 坚实的工程底座

| 层级 | 技术栈 | 成熟度 |
|------|--------|--------|
| **前端** | React 18 + TypeScript + Vite + MUI v6 + Zustand | ⭐⭐⭐⭐⭐ |
| **移动端** | Android (Jetpack Compose + Kotlin + Ktor) | ⭐⭐⭐⭐ |
| **后端** | FastAPI + Python 3.12 + SQLAlchemy 2.0 (async) | ⭐⭐⭐⭐⭐ |
| **数据** | PostgreSQL 17 + pgvector + Redis 7 | ⭐⭐⭐⭐⭐ |
| **部署** | Docker Compose + Nginx + SSL | ⭐⭐⭐⭐⭐ |
| **监控** | Prometheus + psutil + 审计日志 | ⭐⭐⭐⭐ |

### 1.2 已经实现的 AI 能力

- ✅ **多提供商 LLM 集成**（OpenAI 兼容，支持 GLM/GPT/DeepSeek/Kimi 等）
- ✅ **Multi-Path RAG**（分类过滤 + 全局向量检索 + 关键词匹配 + RRF 融合）
- ✅ **HyDE 查询扩展**（生成假设性文档提升检索精度）
- ✅ **外部 Reranking**（百炼/博查/Cohere/Jina，精度提升 10-20%）
- ✅ **文档智能处理**（MinerU PDF/图片 OCR + PII 自动脱敏）
- ✅ **动态知识库**（管理员上传指南 → 自动分块 → Qwen 向量化 → pgvector 存储）
- ✅ **AI 诊断工作流**（患者信息 + 症状 + 文档 + 知识库 → 流式诊断）
- ✅ **慢性病管理**（ICD-10 编码 + 患者关联 + AI 诊断参考）

### 1.3 医患协作生态

- ✅ 三端独立 UI（患者/医生/管理员）
- ✅ @医生提及系统
- ✅ 病例共享 + 脱敏
- ✅ 医生评论 + 患者回复
- ✅ 医生执业认证工作流

---

## 二、关键判断：为什么现在是 Agent 时代的转折点

MediCareAI 目前是一个**"高级问答系统"**——患者输入症状，系统返回诊断。这种模式在 Agent 时代面临根本性天花板：

### 2.1 当前架构的"非 Agent"特征

```
┌─────────────┐    Request     ┌─────────────┐    LLM Call    ┌─────────────┐
│   用户输入   │ ─────────────> │  后端编排    │ ─────────────> │   AI 模型    │
│  (症状+文档) │                │ (固定流程)   │                │ (单次响应)   │
└─────────────┘                └─────────────┘                └─────────────┘
                                      │
                                      ▼
                               ┌─────────────┐
                               │  保存结果    │
                               │ (被动记录)   │
                               └─────────────┘
```

**问题**：
1. **无自主能力** — AI 不能主动发起行动（如提醒复查、追踪指标）
2. **无工具使用** — AI 只能"说话"，不能"做事"（不能调 API、查数据库、发邮件）
3. **无状态规划** — 每次诊断都是独立的，没有跨会话的"治疗计划"
4. **无多 Agent 协作** — 一个 AI 做所有事，没有专科 Agent 分工
5. **无记忆演进** — 患者历史是"被查询的"，不是"被理解的"

### 2.2 Agent 时代的核心范式转变

| 维度 | 当前（LLM 时代） | 下一个（Agent 时代） |
|------|----------------|---------------------|
| **交互模式** | 用户提问 → AI 回答 | AI 主动感知 → 自主决策 → 执行行动 |
| **AI 角色** | 回答者 (Responder) | 协作者 (Collaborator) |
| **知识使用** | RAG 检索注入 Prompt | Agent 自主决定调用什么工具/查什么数据 |
| **会话边界** | 单次请求-响应 | 长期状态机，跨会话记忆 |
| **多智能体** | 单一模型 | 专科 Agent 团队协作 |
| **结构化输出** | 正则解析文本 | 原生 Schema 约束（JSON/XML） |

---

## 三、愿景：MediCareAI-Agent 是什么

> **定义**：MediCareAI-Agent 不是一个聊天机器人，而是一个**由多个医疗智能体组成的自主协作系统**。它能主动感知患者状态、规划健康干预、调用医疗工具、协调医生资源，并在整个过程中保持可解释性和人类监督。

### 3.1 核心愿景对比

**当前 MediCareAI 的典型场景**：
> 患者："我咳嗽一周了"
> 系统：[RAG 检索 → LLM 诊断 → 返回建议]
> → 对话结束

**MediCareAI-Agent 的典型场景**：
> 患者："我咳嗽一周了"
> 诊断 Agent：[分析症状 + 调取历史病历 + 检索指南] → "建议排查肺炎，需结合胸片判断"
> 规划 Agent：[创建随访计划] → "3 天后若无好转，建议复查血常规"
> 监测 Agent：[设置提醒] → 第 3 天主动推送："咳嗽有好转吗？"
> 患者："没有，还发烧了"
> 诊断 Agent：[重新评估 + 升级建议] → "症状加重，建议立即就医，已为您查找附近呼吸科医生"
> 医生 Agent：[生成转诊摘要] → 将结构化病历推送给预约医生

---

## 四、架构设计：从三层到 Agent 网格

### 4.1 新架构总览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         用户接触层 (User Touchpoints)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  患者端 (React/移动端)  │  医生端 (React)  │  管理员端  │  第三方集成 (API)   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Agent 编排层 (Agent Orchestration)                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              主控 Agent (Master Agent / 医疗主任)                     │   │
│  │    - 接收用户意图    - 任务分解    - Agent 调度    - 结果汇总        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                       │
│      ┌─────────────┬──────────────┼──────────────┬─────────────┐           │
│      ▼             ▼              ▼              ▼             ▼           │
│  ┌────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │诊断Agent│  │规划Agent  │  │监测Agent  │  │知识Agent  │  │医生Agent  │      │
│  │Diagnosis│  │Planning  │  │Monitoring│  │Knowledge │  │Doctor    │      │
│  └────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
│      │             │              │              │             │           │
│      ▼             ▼              ▼              ▼             ▼           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      工具层 (Tool Layer / MCP)                        │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ │   │
│  │  │RAG检索  │ │病历查询  │ │检验单解析│ │药物查询  │ │预约系统  │ │邮件发送│ │   │
│  │  │知识库   │ │数据库   │ │MinerU   │ │知识图谱  │ │日历     │ │通知    │ │   │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      基础设施层 (Infrastructure)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  FastAPI │ PostgreSQL+pgvector │ Redis │ OSS │ 外部 LLM │ 嵌入模型 │ 邮件    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Agent 角色定义

#### Agent 1: 诊断 Agent (Diagnosis Agent)
- **继承**: 现有 `ai_service.py` + `multi_path_rag_selector.py`
- **升级**: 
  - 从"单次诊断"变为"可追问、可澄清、可请求补充检查"
  - 使用 **Tool Use** 主动调用化验单解析、影像描述生成
  - 输出结构化诊断报告（JSON Schema），而非自由文本
- **核心能力**: 症状分析 → 鉴别诊断 → 建议检查 → 置信度评估

#### Agent 2: 规划 Agent (Care Planning Agent)
- **新增**: 完全新能力
- **职责**: 
  - 根据诊断生成个性化治疗/随访计划
  - 分解为可执行的任务序列（Task DAG）
  - 管理计划状态机（pending → active → completed → overdue）
- **示例输出**:
  ```json
  {
    "plan_id": "plan-uuid",
    "title": "上呼吸道感染随访计划",
    "tasks": [
      {"id": 1, "type": "medication", "description": "服用阿莫西林 3 天", "due": "2026-04-30"},
      {"id": 2, "type": "self_check", "description": "每日记录体温", "frequency": "daily"},
      {"id": 3, "type": "follow_up", "description": "3 天后复查", "due": "2026-05-01", "condition": "if_not_improved"}
    ]
  }
  ```

#### Agent 3: 监测 Agent (Monitoring Agent)
- **新增**: Cron + 事件驱动的自主 Agent
- **职责**:
  - 按计划主动推送提醒（用药、复查、记录症状）
  - 监测患者输入的异常信号（如体温持续升高）
  - 触发升级流程（自动通知医生/紧急联系人）
- **触发模式**: 定时触发 + 事件触发 + 患者主动汇报

#### Agent 4: 知识 Agent (Knowledge Agent)
- **继承**: 现有知识库 + RAG 系统
- **升级**:
  - 封装为 **MCP Server**（Model Context Protocol）
  - 不仅被"查询"，还能被 Agent 主动"探索"（如：规划 Agent 问"糖尿病患者感冒需要注意什么？"）
  - 支持 **GraphRAG**: 从向量检索升级到知识图谱推理

#### Agent 5: 医生协作 Agent (Doctor Collaboration Agent)
- **继承**: 现有 @医生 + 评论系统
- **升级**:
  - 自动为医生生成**结构化病例摘要**（而非让医生看原始对话）
  - 医生可通过自然语言指令操作（如"安排下周二复查血常规"）
  - 支持医生自定义自己的 Agent 工作流

### 4.3 主控 Agent (Master Agent)

这是整个系统的中枢，类似医院的"医疗主任"。它不负责具体诊断，而是：

1. **意图识别**: 理解用户到底想干什么
   - "我头疼" → 启动诊断 Agent
   - "我药吃完了" → 启动规划 Agent（续方）
   - "上周的复查结果出来了吗" → 启动知识 Agent（查记录）

2. **任务分解**: 将复杂请求拆分为子任务 DAG
   ```
   "帮我安排下周复查并提醒我带检验单"
   → Task 1: 查找最近待复查的项目（知识 Agent）
   → Task 2: 生成复查清单（规划 Agent）
   → Task 3: 创建日历提醒（监测 Agent）
   → Task 4: 发送确认通知（工具层）
   ```

3. **状态管理**: 维护跨 Agent 的会话状态
   - 使用 **PostgreSQL + Redis** 实现 Agent Memory
   - 支持长时运行任务（如"监测我一周血压"）

---

## 五、关键技术升级方案

### 5.1 核心升级 1：Tool Use / Function Calling 架构

**当前问题**: AI 只能生成文本，不能执行操作。

**升级方案**: 所有后端能力封装为 **Tools**，让 LLM 自主决定调用。

```python
# 示例：诊断 Agent 的工具箱
class DiagnosisToolkit:
    @tool(description="查询患者历史病历")
    async def query_medical_history(self, patient_id: str, limit: int = 5) -> list:
        ...
    
    @tool(description="解析化验单 PDF，提取关键指标")
    async def parse_lab_report(self, document_id: str) -> dict:
        ...  # 调用现有 MinerU + 医疗数据提取器
    
    @tool(description="检索医学知识库")
    async def search_knowledge_base(self, query: str, top_k: int = 5) -> list:
        ...  # 调用现有 MultiPathRAGSelector
    
    @tool(description="查询药物相互作用")
    async def check_drug_interactions(self, drugs: list) -> dict:
        ...
    
    @tool(description="生成结构化诊断报告")
    async def generate_structured_report(
        self, 
        symptoms: str,
        diagnosis: str,
        confidence: float,
        recommended_tests: list,
        follow_up_plan: dict
    ) -> dict:
        ...
```

**技术选型**:
- **原生 OpenAI Function Calling**（GLM/GPT 都支持）
- 或 **MCP (Model Context Protocol)** —— 更开放的标准

### 5.2 核心升级 2：结构化输出 (Structured Output)

**当前问题**: AI 输出用正则表达式解析，脆弱且容易出错。

**升级方案**: 使用 **Outlines / Instructor** 等库强制 LLM 输出合法 JSON Schema。

```python
from pydantic import BaseModel
from typing import Literal

class DiagnosisReport(BaseModel):
    primary_diagnosis: str
    differential_diagnoses: list[str]
    confidence: Literal["high", "medium", "low"]
    severity: Literal["mild", "moderate", "severe", "emergency"]
    key_findings: list[str]
    recommended_tests: list[str]
    recommended_actions: list[str]
    contraindications: list[str]  # 基于患者慢性病的禁忌
    follow_up_required: bool
    follow_up_timeline: str
    red_flags: list[str]  # 需立即就医的警示信号
    knowledge_sources: list[str]  # 引用的知识库来源
```

**收益**:
- 前端可直接渲染结构化报告（无需解析 Markdown）
- 下游 Agent 可安全消费输出
- 可验证、可审计、可回滚

### 5.3 核心升级 3：Agent Memory 系统

**当前问题**: 每次 AI 调用都是独立的，没有"患者画像"的演进概念。

**升级方案**: 三层记忆架构

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: 长期记忆 (Long-term Memory)                        │
│  - 患者健康画像（慢性病、过敏史、用药史、家族病史）              │
│  - 既往诊断模式（什么病容易复发、什么药效果好）                │
│  - 存储: PostgreSQL (users + patient_profiles 表)            │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: 工作记忆 (Working Memory / Session State)          │
│  - 当前会话的上下文（已讨论的症状、已做的检查）                │
│  - 进行中的计划（待完成的任务列表）                           │
│  - 存储: Redis (TTL: 24h)                                    │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: 感官记忆 (Sensory Memory / Current Turn)           │
│  - 当前轮次的输入和工具返回结果                               │
│  - 直接放在 LLM 的 context window 中                         │
└─────────────────────────────────────────────────────────────┘
```

### 5.4 核心升级 4：MCP (Model Context Protocol) 集成

MediCareAI-Agent 不应是一个封闭系统，而应通过 MCP 与外部工具生态连接：

```
MediCareAI-Agent (MCP Client)
        │
        ├─── MCP Server: 内部知识库 (现有 RAG)
        ├─── MCP Server: 医学影像分析 (未来集成)
        ├─── MCP Server: 电子病历系统 (医院 HIS 对接)
        ├─── MCP Server: 药品数据库 (用药助手)
        ├─── MCP Server: 日历/预约系统
        └─── MCP Server: 通知/邮件系统 (现有邮件服务)
```

**收益**: 第三方开发者可以为 MediCareAI-Agent 编写 MCP Server，扩展能力无需修改核心代码。

### 5.5 核心升级 5：GraphRAG —— 从向量检索到知识推理

**当前**: 向量相似度检索（"找语义相近的段落"）

**升级**: 医疗知识图谱 + 向量混合

```cypher
// 知识图谱示例查询
MATCH (d:Disease {name: "2型糖尿病"})-[:HAS_SYMPTOM]->(s:Symptom)
MATCH (d)-[:CONTRAINDICATED_WITH]->(drug:Drug)
MATCH (d)-[:REQUIRES_MONITORING]->(indicator:LabIndicator)
RETURN s.name, drug.name, indicator.name
```

**应用场景**:
- 患者有糖尿病 + 感冒 → 知识图谱推理：避免使用含糖 cough syrup
- 药物相互作用检测 → 不仅是文本匹配，而是图谱路径查询
- 并发症预警 → "糖尿病患者出现足部麻木 → 高度怀疑周围神经病变"

---

## 六、数据模型演进

### 6.1 新增核心表

```sql
-- Agent 会话表：跟踪多轮 Agent 交互
CREATE TABLE agent_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    master_agent_id VARCHAR(100),  -- 主控 Agent 实例 ID
    intent VARCHAR(100),           -- 识别的用户意图
    status VARCHAR(50),            -- active, completed, escalated, failed
    context_snapshot JSONB,        -- 会话上下文快照
    task_dag JSONB,                -- 任务依赖图
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 任务执行表：Agent 调度的原子任务
CREATE TABLE agent_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES agent_sessions(id),
    agent_type VARCHAR(50),        -- diagnosis, planning, monitoring, knowledge, doctor
    task_name VARCHAR(200),
    status VARCHAR(50),            -- pending, running, completed, failed, cancelled
    input_params JSONB,
    output_result JSONB,
    tool_calls JSONB,              -- 记录调用了哪些工具
    dependencies UUID[],           -- 依赖的其他任务
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT
);

-- 患者健康画像（Agent 长期记忆）
CREATE TABLE patient_health_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID REFERENCES users(id),
    health_summary TEXT,           -- AI 生成的健康摘要
    disease_patterns JSONB,        -- 疾病模式识别
    medication_history JSONB,      -- 用药历史及反应
    risk_factors JSONB,            -- 风险因素评估
    preferences JSONB,             -- 患者偏好（沟通风格、提醒时间等）
    last_updated TIMESTAMP WITH TIME ZONE,
    updated_by_agent VARCHAR(100)  -- 哪个 Agent 最后更新
);

-- 护理计划表
CREATE TABLE care_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID REFERENCES users(id),
    title VARCHAR(255),
    source_case_id UUID REFERENCES medical_cases(id),
    status VARCHAR(50),            -- active, completed, cancelled
    tasks JSONB,                   -- 任务列表
    created_by_agent VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- 监测事件表（监测 Agent 使用）
CREATE TABLE monitoring_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    patient_id UUID REFERENCES users(id),
    event_type VARCHAR(100),       -- reminder, alert, check_in, escalation
    trigger_condition VARCHAR(255), -- 触发条件描述
    payload JSONB,                 -- 事件内容
    delivered_at TIMESTAMP WITH TIME ZONE,
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    response_value JSONB           -- 患者回应
);

-- 知识图谱边表（GraphRAG）
CREATE TABLE knowledge_graph_edges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id VARCHAR(255),        -- 源实体
    source_type VARCHAR(100),      -- Disease, Symptom, Drug, etc.
    relation VARCHAR(100),         -- HAS_SYMPTOM, TREATED_BY, CONTRAINDICATED_WITH
    target_id VARCHAR(255),        -- 目标实体
    target_type VARCHAR(100),
    confidence FLOAT,              -- 关系置信度
    evidence TEXT,                 -- 证据来源
    metadata JSONB
);
```

### 6.2 现有表增强

```sql
-- users 表增加 Agent 相关字段
ALTER TABLE users ADD COLUMN agent_preferences JSONB DEFAULT '{}'::jsonb;
ALTER TABLE users ADD COLUMN last_agent_interaction TIMESTAMP WITH TIME ZONE;

-- medical_cases 表增加结构化诊断字段
ALTER TABLE medical_cases ADD COLUMN structured_diagnosis JSONB;
ALTER TABLE medical_cases ADD COLUMN agent_session_id UUID REFERENCES agent_sessions(id);

-- ai_feedbacks 表增加工具调用记录
ALTER TABLE ai_feedbacks ADD COLUMN tool_calls JSONB;
ALTER TABLE ai_feedbacks ADD COLUMN reasoning_chain TEXT;  -- Agent 的思考链
```

---

## 七、前端升级方案

### 7.1 患者端：从"表单"到"对话"

**当前**: 患者填写表单 → 等待 AI 返回大段 Markdown

**升级**: 对话式 Agent 界面

```
┌─────────────────────────────────────────┐
│  🤖 MediCareAI-Agent                    │
│                                         │
│  【对话区域】                            │
│  ─────────────────────────────────────  │
│  患者: 我咳嗽一周了                      │
│                                         │
│  Agent: 了解到您咳嗽一周了。为了更准确   │
│  地帮助您，我需要了解几个细节：          │
│  ① 咳嗽有痰吗？什么颜色？               │
│  ② 有没有发烧？                         │
│  ③ 您有慢性病（如糖尿病、高血压）吗？    │
│                                         │
│  【快捷回复】干咳 │ 有黄痰 │ 低烧 │ 无慢性病 │
│                                         │
│  ─────────────────────────────────────  │
│  [语音输入] [拍照上传] [发送]           │
└─────────────────────────────────────────┘
```

**技术实现**:
- 引入 **React 聊天组件库**（如 `chat-ui-kit-react` 或自研）
- 支持**流式 SSE** 显示 Agent 思考过程
- **卡片化输出**: 诊断报告、检查建议、用药提醒都以结构化卡片展示

### 7.2 医生端：从"浏览病例"到"指挥 Agent"

**新增功能**:
- **Agent 摘要面板**: 每个病例自动显示 Agent 生成的结构化摘要
- **自然语言指令**: 医生可以直接输入"为这个患者安排 2 周后的复查，项目包括血常规和胸片"
- **Agent 协作记录**: 查看患者与 Agent 的交互历史

### 7.3 管理员端：Agent 监控中心

- **Agent 会话审计**: 查看所有 Agent 会话的完整链路
- **工具调用统计**: 哪些工具被调用最多、成功率、延迟
- **Agent 性能仪表盘**: 各 Agent 的响应时间、错误率、用户满意度
- **知识图谱可视化**: GraphRAG 的知识关系图谱

---

## 八、实施路线图

### Phase 1: 基础 Agent 架构（2-3 个月）

**目标**: 搭建 Agent 框架，让诊断能力从"单次问答"进化为"多轮对话 + 工具调用"

| 任务 | 说明 | 复用现有 |
|------|------|----------|
| 搭建 Agent 运行时 | 基于 `langchain` 或自研轻量框架 | FastAPI 后端 |
| 实现 Tool Use 架构 | 将现有服务封装为 Tools | ai_service, rag, mineru |
| 诊断 Agent v1 | 支持多轮追问 + 工具调用 | comprehensive_diagnosis |
| 结构化输出 | 使用 Pydantic Schema 约束 | - |
| 前端对话 UI | 替换表单为对话界面 | React + MUI |
| Agent Memory v1 | Session-level 记忆 | Redis |

**技术选型建议**:
- **Agent 框架**: 建议使用 **PydanticAI** 或自研轻量框架（MediCareAI 已经很复杂，LangChain 可能过度设计）
- **LLM**: 保持现有 OpenAI 兼容架构
- **Schema**: Pydantic v2 + Outlines 做结构化输出

### Phase 2: 多 Agent 协作（2-3 个月）

**目标**: 引入主控 Agent + 规划 Agent + 监测 Agent

| 任务 | 说明 |
|------|------|
| 主控 Agent | 意图识别 + 任务分解 + Agent 调度 |
| 规划 Agent | 生成护理计划 + 任务 DAG |
| 监测 Agent | 定时任务 + 事件驱动提醒 |
| 医生协作 Agent v2 | 结构化摘要 + 自然语言指令 |
| 新增数据表 | agent_sessions, agent_tasks, care_plans |

### Phase 3: 知识增强（2-3 个月）

**目标**: GraphRAG + MCP 生态

| 任务 | 说明 | 复用现有 |
|------|------|----------|
| 知识图谱构建 | 从现有知识库抽取实体关系 | knowledge_base_chunks |
| GraphRAG 集成 | 混合向量+图谱检索 | MultiPathRAGSelector |
| MCP Server 封装 | 将内部能力暴露为 MCP | 全部服务 |
| 患者健康画像 | AI 生成 + 持续更新 | users + medical_cases |

### Phase 4: 自主智能（3-6 个月）

**目标**: Agent 真正"自主"运行

| 任务 | 说明 |
|------|------|
|  proactive health monitoring | 无需患者输入，主动分析健康趋势 |
| 多模态 Agent | 集成医学影像分析 |
| 个性化 Agent 训练 | 基于患者反馈微调 Agent 行为 |
| 医生自定义 Agent | 每个医生可配置自己的 Agent 工作流 |

---

## 九、风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| **Agent 幻觉** | 医疗场景致命 | ① 强制结构化输出 ② 所有诊断标注知识来源 ③ 高风险建议必须医生确认 ④ 置信度分级 |
| **LLM 成本激增** | Tool Use + 多轮对话消耗更多 Token | ① 智能缓存 ② 小模型路由（简单任务用轻量模型）③ Token 预算控制 |
| **系统复杂度爆炸** | 多 Agent 调试困难 | ① 完善的 Agent Tracing（LangSmith 风格）② 每个 Agent 独立测试 ③ 回退到单模型模式 |
| **数据隐私** | Agent 记忆持久化增加泄露面 | ① 分层加密 ② 敏感数据不出 LLM context ③ 审计所有工具调用 |
| **医生接受度** | 医生可能不信任 AI Agent | ① 可解释性优先（显示推理链）② 医生始终有否决权 ③ 渐进式引入 |

---

## 十、技术栈推荐（新项目）

### 后端

| 组件 | 推荐 | 理由 |
|------|------|------|
| **Agent 框架** | 自研轻量 + PydanticAI | MediCareAI 已很重，LangChain 过度复杂 |
| **结构化输出** | Outlines / Instructor | 强制 JSON Schema，医疗场景必需 |
| **Tool Use** | OpenAI Function Calling / MCP | 标准协议 |
| **工作流引擎** | Temporal.io 或自研 | 护理计划需要可靠的任务调度 |
| **知识图谱** | Neo4j 或 pg_graph | GraphRAG 需要图数据库 |
| **LLM 网关** | LiteLLM Proxy | 统一路由多提供商，控制成本 |
| **现有保留** | FastAPI, PostgreSQL, Redis, Docker | 工程底座无需更换 |

### 前端

| 组件 | 推荐 |
|------|------|
| **聊天 UI** | 自研（基于 MUI）或 `chat-ui-kit-react` |
| **状态管理** | Zustand（保持）+ 新增 Agent 状态机 |
| **流式渲染** | EventSource (SSE) |
| **卡片组件** | MUI Card + 自定义诊断/计划卡片 |

---

## 十一、最小可行产品 (MVP) 定义

如果要在最短时间内验证 Agent 方向，建议先做：

> **MVP: "Agent 诊断助手"**
>
> 1. 一个**诊断 Agent**，支持多轮对话追问症状
> 2. **3 个 Tools**: 查病历、查知识库、生成结构化报告
> 3. **前端对话 UI** 替换现有症状提交表单
> 4. **结构化诊断报告** 卡片展示
>
> 这个 MVP 可以在 **4-6 周**内完成，且能立即让用户感受到 Agent 体验的差异。

---

## 十二、总结：为什么这是值得的

MediCareAI 已经是一个**优秀的医疗 AI 产品**。但 LLM 时代的架构决定了它只能"回答问题"。

Agent 时代的 MediCareAI-Agent 将是一个**真正的医疗协作者**：

- 它会**主动关心**患者，而不是等患者来问
- 它会**规划治疗路径**，而不是只给建议
- 它会**调用工具执行**，而不是只给文字指导
- 它会**团队协作**（多 Agent），而不是一个模型做所有事
- 它会**持续学习**每个患者，而不是每次都从零开始

这不是简单的功能迭代，而是**产品范式的跃迁**。

---

*下一步建议：苏医生可以先看看这份方案，如果有感兴趣的 Phase，我可以立刻开始搭建 MVP 的代码骨架。*
