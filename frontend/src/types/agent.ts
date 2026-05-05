/**
 * Agent 相关类型定义
 * 文档来源: 14 - API 与通信协议设计
 */

/** SSE 事件类型 */
export type SSEEventType =
  | 'intent'
  | 'agent_switch'
  | 'thinking'
  | 'tool_call'
  | 'tool_result'
  | 'structured'
  | 'text'
  | 'error'
  | 'complete';

/** SSE 流事件 */
export interface SSEEvent {
  event: SSEEventType;
  data: Record<string, unknown>;
}

/** Agent 工作流步骤 */
export interface WorkflowStep {
  id: string;
  type: 'intent' | 'agent_switch' | 'tool_call' | 'tool_result' | 'thinking' | 'complete';
  status: 'pending' | 'running' | 'done' | 'error';
  title: string;
  detail?: string;
  timestamp: Date;
  icon?: string;
  toolName?: string;
  toolParams?: Record<string, unknown>;
  toolResult?: unknown;
}

/** 诊断报告 Schema */
export interface DiagnosisReport {
  primary_diagnosis: string;
  icd11_code: string;
  confidence: 'low' | 'medium' | 'high';
  differential_diagnoses?: Array<{
    diagnosis: string;
    icd11_code: string;
    reasoning: string;
  }>;
  recommended_exams?: string[];
  treatment_suggestions?: string[];
  follow_up_plan?: string;
  red_flags?: string[];
  referral_needed: boolean;
  referral_reason?: string;
}

/** 用户消息 */
export interface ChatMessageItem {
  id: string;
  role: 'user' | 'agent' | 'system';
  content: string;
  structured?: DiagnosisReport;
  toolCalls?: Array<{
    tool: string;
    params: Record<string, unknown>;
    result?: unknown;
  }>;
  workflowSteps?: WorkflowStep[];
  timestamp: Date;
  isStreaming?: boolean;
}

/** 会话 */
export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

/** 路由响应 */
export interface RouteResponse {
  intent: string;
  confidence: number;
  target_agent: string;
  requires_clarification: boolean;
  suggested_followup_questions: string[];
}

/** 访客状态 */
export interface GuestStatus {
  interaction_count: number;
  max_interactions: number;
  remaining: number;
  can_interact: boolean;
}

/** 统一 API 响应 */
export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
  request_id?: string;
  timestamp?: string;
}
