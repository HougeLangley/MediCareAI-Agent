# 多轮问诊对话（Medical Interview）实现计划

> **目标**：让 DiagnosisAgent 像真实医生一样问诊——先收集关键信息，再问选择题/追问，最后才输出诊断报告。
> **架构**：SSE 流式输出 + HTTP POST 续传（保持现有架构不变）
> **部署**：严格遵循标准部署流程，逐个服务部署

---

## 当前问题诊断

当前 `route_stream` 的 diagnosis 流程：
```
用户输入 → MasterAgent 意图识别 → 直接调用 DiagnosisAgent.analyze() → 一次性输出结构化报告
```

**问题**：
1. Agent 没有"问诊"环节，直接出报告
2. 报告内容依赖 LLM 预训练知识，没有基于用户逐步补充的信息
3. 用户体验像"搜索引擎"而不是"医生问诊"

---

## 目标交互流程

```
用户: "腹痛拉肚子"
    ↓
Agent: "您好，为了更准确地帮您分析，我需要了解几个问题。"
        "首先，腹痛的位置在哪里？"  [上腹部] [下腹部] [脐周] [全腹] [不确定]
    ↓
用户点击: "下腹部"
    ↓
Agent: "收到。疼痛的性质是怎样的？"  [绞痛] [胀痛] [隐痛] [刺痛] [绞痛]
    ↓
用户点击: "绞痛"
    ↓
Agent: "疼痛大概持续多久了？"  [不到1天] [1-3天] [3-7天] [超过1周]
    ↓
...（继续追问，直到信息足够）...
    ↓
Agent: "🔍 正在检索医学知识库..."（真实工具调用）
Agent: "🧪 正在分析症状模式..."
Agent: "🏥 初步诊断：急性肠胃炎"
        Markdown 报告...
```

---

## 技术方案

### 核心思想

保持现有 SSE 架构不变，新增 `question` 事件类型：
- Agent 分析信息缺口 → 发送 `question` → SSE 流结束（`complete: waiting_for_answer`）
- 用户回答 → POST `/api/v1/agents/route/stream/continue` → 新 SSE 流继续
- 循环直到信息足够 → 最终输出诊断报告

### 状态管理

不引入新的数据库表，复用现有 `AgentSession.context` JSONB 字段：
```json
{
  "interview": {
    "collected_info": {
      "pain_location": "下腹部",
      "pain_nature": "绞痛",
      "duration": "1-3天",
      ...
    },
    "asked_questions": ["q1", "q2", "q3"],
    "is_sufficient": false
  }
}
```

### SSE 事件扩展

新增事件类型：

| 事件 | 方向 | 说明 |
|------|------|------|
| `question` | S→C | Agent 发送追问/选择题 |
| `interview_progress` | S→C | 显示已收集信息摘要 |

---

## 后端变更（backend/app/）

### Task 1: 新增问诊相关数据模型

**文件**: `backend/app/models/interview.py`（新建）

定义问诊状态和问题模板：
- `InterviewState` dataclass: 收集到的信息、已问问题、是否足够
- `QuestionTemplate` dataclass: 问题ID、问题文本、选项列表、类型(choice/text)

### Task 2: 扩展 DiagnosisAgent — 新增 interview 方法

**文件**: `backend/app/services/agents.py`

修改 `DiagnosisAgent`：
1. 新增 `interview()` 方法：分析当前信息，决定下一个问题或结束问诊
2. LLM system prompt 改为"问诊模式"：
   - 你是一位专业的问诊医生
   - 根据已收集信息，判断还缺哪些关键信息
   - 如果信息不足，输出下一个要问的问题（JSON格式）
   - 如果信息足够，输出"sufficient: true"
3. 预定义关键问诊问题列表（位置、性质、持续时间、伴随症状、诱因等）

### Task 3: 扩展 route_stream — 支持 question 事件

**文件**: `backend/app/api/v1/agents.py`

修改 `event_generator()`：
1. `intent == "diagnosis"` 时，先进入 interview 阶段
2. 发送 `event: interview_progress` 显示已收集信息
3. 调用 `diag_agent.interview()`：
   - 如果返回 `sufficient: true` → 继续现有诊断流程（工具调用 → 报告）
   - 如果返回问题 → 发送 `event: question`，然后 `complete`
4. 保持向后兼容：其他意图（planning/monitoring 等）不受影响

### Task 4: 新增续传端点

**文件**: `backend/app/api/v1/agents.py`

新增 `POST /api/v1/agents/route/stream/continue`：
```python
class StreamContinueRequest(BaseModel):
    session_id: str
    question_id: str
    answer: str
```

逻辑：
1. 读取 AgentSession.context.interview 状态
2. 将 answer 追加到 collected_info
3. 重新进入 interview 流程
4. 返回新的 SSE 流（继续追问 或 进入诊断）

### Task 5: 扩展 LLMService — 支持结构化问诊输出

**文件**: `backend/app/services/llm.py`

新增 `chat_structured_interview()` 或复用现有 `generate_structured`：
- 输出 schema：`InterviewDecision`（next_question 或 sufficient）

---

## 前端变更（frontend/src/）

### Task 6: 扩展 SSE 类型定义

**文件**: `frontend/src/types/agent.ts`

新增：
```typescript
export type SSEEventType = ... | 'question' | 'interview_progress';

export interface InterviewQuestion {
  question_id: string;
  type: 'choice' | 'text';
  question: string;
  options?: string[];
  hint?: string;
}

export interface ChatMessageItem {
  ...
  interviewQuestion?: InterviewQuestion;  // 用于渲染追问UI
}
```

### Task 7: 新增追问交互组件

**文件**: `frontend/src/components/InterviewQuestion.tsx`（新建）

渲染选择题或文本输入：
- 选择题：Chip 按钮矩阵，用户点击即发送
- 文本题：小型输入框，Enter 发送
- 样式与 ChatInput 统一，但更紧凑

### Task 8: 修改 ChatMessage — 支持追问渲染

**文件**: `frontend/src/components/ChatMessage.tsx`

当 `message.interviewQuestion` 存在时：
- 渲染 `InterviewQuestion` 组件
- 用户回答后，通过回调通知父组件

### Task 9: 修改 ChatPage — 支持多轮交互

**文件**: `frontend/src/components/ChatPage.tsx`

重大修改：
1. `handleSend` 保持现有逻辑（发起首次 SSE 流）
2. 新增 `handleInterviewAnswer(questionId, answer)`：
   - 发送 POST `/agents/route/stream/continue`
   - 处理新的 SSE 流（可能再次收到 question，或进入诊断）
3. `onEvent` 处理新增 `question` 事件：
   - 将 question 数据附加到当前 agent message
   - 停止 `isStreaming`，让用户可以交互
4. `onEvent` 处理 `interview_progress`：显示已收集信息

### Task 10: 修改 agent.ts — 新增续传 API

**文件**: `frontend/src/api/agent.ts`

新增：
```typescript
export function streamDiagnoseContinue(
  payload: { session_id: string; question_id: string; answer: string },
  onEvent: (event: SSEEvent) => void
): Promise<void>
```

---

## 数据流时序图

```
┌─────────┐     ┌─────────┐     ┌──────────────┐     ┌──────────┐
│  User   │     │ Frontend│     │  Backend     │     │ LLM/RAG  │
└────┬────┘     └────┬────┘     └──────┬───────┘     └────┬─────┘
     │               │                  │                  │
     │  "腹痛拉肚子"  │                  │                  │
     │──────────────>│                  │                  │
     │               │ GET /route/stream│                  │
     │               │─────────────────>│                  │
     │               │                  │ classify_intent  │
     │               │                  │ interview()      │
     │               │                  │─── insufficient ─┤
     │               │                  │<── next_question ─│
     │               │                  │                  │
     │               │<── question ─────│                  │
     │               │<── complete ─────│                  │
     │               │                  │                  │
     │  显示选择题    │                  │                  │
     │<──────────────│                  │                  │
     │               │                  │                  │
     │  点击"下腹部"  │                  │                  │
     │──────────────>│                  │                  │
     │               │ POST /continue   │                  │
     │               │─────────────────>│                  │
     │               │                  │ interview()      │
     │               │                  │─── insufficient ─┤
     │               │                  │<── next_question ─│
     │               │                  │                  │
     │               │<── question ─────│                  │
     │  ...继续追问... │                  │                  │
     │               │                  │                  │
     │               │                  │ interview()      │
     │               │                  │─── sufficient ───┤
     │               │                  │                  │
     │               │                  │ analyze()        │
     │               │                  │─── tool calls ───┤
     │               │                  │<── results ──────│
     │               │                  │                  │
     │               │<── structured ───│                  │
     │               │<── text ─────────│                  │
     │               │<── complete ─────│                  │
     │               │                  │                  │
     │  显示诊断报告   │                  │                  │
     │<──────────────│                  │                  │
```

---

## 预定义问诊问题库

第一阶段实现 6-8 个核心问诊问题：

| # | 问题 | 类型 | 选项 |
|---|------|------|------|
| 1 | 腹痛的位置是？ | choice | 上腹部, 下腹部, 脐周, 全腹, 不确定 |
| 2 | 疼痛的性质是？ | choice | 绞痛, 胀痛, 隐痛, 刺痛, 烧灼痛 |
| 3 | 症状持续多久了？ | choice | 不到1天, 1-3天, 3-7天, 超过1周 |
| 4 | 有无发热？ | choice | 无, 低热(37.3-38℃), 中等发热(38-39℃), 高热(>39℃) |
| 5 | 大便的性状？ | choice | 水样便, 稀便, 黏液便, 脓血便, 正常 |
| 6 | 有无恶心呕吐？ | choice | 无, 恶心, 呕吐, 两者都有 |
| 7 | 近期有无不洁饮食/旅行史？ | choice | 无, 可疑不洁食物, 外出就餐, 旅行中 |
| 8 | 大便次数？（可选文字补充） | text | 用户输入 |

---

## 实施顺序

### Phase 1: 后端基础（Task 1-5）
1. Task 1: 新建 interview 数据模型
2. Task 2: DiagnosisAgent 新增 interview 方法
3. Task 3: 修改 route_stream 支持 question 事件
4. Task 4: 新增续传端点
5. Task 5: 扩展 LLM 结构化输出（如需要）
6. 本地 py_compile 检查
7. Git commit + push
8. VPS: pull → build backend --no-cache → recreate backend

### Phase 2: 前端交互（Task 6-10）
9. Task 6: 扩展 SSE 类型定义
10. Task 7: 新建 InterviewQuestion 组件
11. Task 8: 修改 ChatMessage
12. Task 9: 修改 ChatPage
13. Task 10: 新增续传 API
14. 本地 npm run build 检查
15. Git commit + push
16. VPS: pull → build frontend --no-cache → recreate frontend

### Phase 3: 验证
17. 浏览器测试完整问诊流程
18. 确认选择题交互正常
19. 确认最终诊断报告正确输出
20. 确认 AgentWorkflow 正确展示

---

## 测试验证清单

- [ ] 用户输入主诉后，Agent 发送 question 事件而不是直接出报告
- [ ] 选择题选项正确渲染，点击后发送回答
- [ ] POST /continue 端点正确接收回答并续传
- [ ] 追问 2-3 轮后，Agent 判断信息足够，进入诊断流程
- [ ] 诊断流程中真实工具调用仍然执行
- [ ] 最终诊断报告正确渲染
- [ ] 刷新页面后，会话历史保留（如已实现）
- [ ] 非 diagnosis 意图（如 planning）不受影响

---

## 风险与回退

| 风险 | 缓解措施 |
|------|----------|
| LLM interview 判断不准确 | 预定义问题顺序作为 fallback |
| 用户不想回答某些问题 | 添加"跳过"选项 |
| SSE 连接中断 | POST 续传端点天然支持重试 |
| 前端状态管理复杂 | 保持简单：question 存在时禁用自由输入 |

---

## 文件变更清单

**新建**：
- `backend/app/models/interview.py`
- `frontend/src/components/InterviewQuestion.tsx`

**修改**：
- `backend/app/services/agents.py` — DiagnosisAgent 新增 interview
- `backend/app/services/llm.py` — 新增结构化问诊输出（如需要）
- `backend/app/api/v1/agents.py` — route_stream + 续传端点
- `frontend/src/types/agent.ts` — 新增 question 类型
- `frontend/src/api/agent.ts` — 新增 streamDiagnoseContinue
- `frontend/src/components/ChatPage.tsx` — 多轮交互逻辑
- `frontend/src/components/ChatMessage.tsx` — 追问渲染
