/**
 * Agent API 服务层
 * 文档来源: 14 - API 与通信协议设计
 * 支持 REST + SSE 流式输出
 */

import type { ApiResponse, ChatSession, GuestStatus, RouteResponse, SSEEvent } from '../types/agent';

import { API_BASE, getToken } from './client';

function getGuestToken(): string | null {
  return localStorage.getItem('guest_token');
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  const guest = getGuestToken();
  if (token) return { Authorization: `Bearer ${token}` };
  if (guest) return { 'X-Guest-Token': guest };
  return {};
}

/** 获取本地存储的访客状态 */
export function getStoredGuestStatus(): GuestStatus | null {
  const raw = localStorage.getItem('guest_status');
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

/**
 * 创建访客 Session
 * POST /api/v1/auth/guest
 */
export async function createGuestSession(
  fingerprint?: string
): Promise<string> {
  const res = await fetch(`${API_BASE}/auth/guest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fingerprint: fingerprint || 'web' }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  const data = await res.json();
  // 后端返回: { id, session_token, message_count, max_messages, expires_at, created_at }
  localStorage.setItem('guest_token', data.session_token);
  const status: GuestStatus = {
    interaction_count: data.message_count || 0,
    max_interactions: data.max_messages || 10,
    remaining: (data.max_messages || 10) - (data.message_count || 0),
    can_interact: true,
  };
  localStorage.setItem('guest_status', JSON.stringify(status));
  return data.session_token;
}

/**
 * 查询访客状态
 * GET /api/v1/auth/guest/status
 */
export async function fetchGuestStatus(): Promise<GuestStatus> {
  const guestToken = getGuestToken();
  const res = await fetch(`${API_BASE}/auth/guest/status`, {
    headers: guestToken ? { 'X-Guest-Token': guestToken } : {},
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  const data = await res.json();
  // 后端返回: { interaction_count, max_interactions, remaining, can_interact, expires_at }
  const status: GuestStatus = {
    interaction_count: data.interaction_count || 0,
    max_interactions: data.max_interactions || 10,
    remaining: data.remaining ?? 0,
    can_interact: data.can_interact ?? false,
  };
  localStorage.setItem('guest_status', JSON.stringify(status));
  return status;
}

/**
 * 路由用户意图
 * POST /api/v1/agents/route
 */
export async function routeIntent(
  message: string,
  sessionId?: string
): Promise<RouteResponse> {
  const res = await fetch(`${API_BASE}/agents/route`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  const json: ApiResponse<RouteResponse> = await res.json();
  if (json.code !== 200) throw new Error(json.message);
  return json.data;
}

/**
 * 非流式对话
 * POST /api/v1/agents/diagnose
 */
export async function chat(
  message: string,
  sessionId?: string
): Promise<{ session_id: string; response_text: string; structured_report?: unknown }> {
  const res = await fetch(`${API_BASE}/agents/diagnose`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ message, session_id: sessionId, patient_id: 'guest' }),
  });
  const json: ApiResponse<{
    session_id: string;
    response_text: string;
    structured_report?: unknown;
    requires_followup: boolean;
  }> = await res.json();
  if (json.code !== 200 && json.code !== 202) throw new Error(json.message);
  return {
    session_id: json.data.session_id,
    response_text: json.data.response_text,
    structured_report: json.data.structured_report,
  };
}

/**
 * 流式对话 (SSE)
 * GET /api/v1/agents/route/stream
 * 事件类型: intent / agent_switch / thinking / tool_call / tool_result / text / error / complete
 */
export function streamDiagnose(
  payload: { message: string; session_id?: string; patient_history?: string },
  onEvent: (event: SSEEvent) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const params = new URLSearchParams();
    params.set('message', payload.message);
    if (payload.session_id) params.set('session_id', payload.session_id);
    if (payload.patient_history) params.set('patient_history', payload.patient_history);

    // EventSource 不支持自定义 headers，将 token 通过 URL query 传递
    const token = getToken();
    const guestToken = getGuestToken();
    if (guestToken) params.set('guest_token', guestToken);
    else if (token) params.set('token', token);

    const url = `${API_BASE}/agents/route/stream?${params.toString()}`;
    const eventSource = new EventSource(url);

    // 处理命名事件
    const namedEvents: SSEEventType[] = ['intent', 'agent_switch', 'thinking', 'tool_call', 'tool_result', 'structured', 'text', 'question', 'interview_progress', 'complete', 'error'];
    namedEvents.forEach(eventName => {
      eventSource.addEventListener(eventName, (e) => {
        try {
          const parsed = JSON.parse((e as MessageEvent).data);
          onEvent({ event: eventName, data: parsed });
          if (eventName === 'complete') {
            eventSource.close();
            resolve();
          }
          if (eventName === 'error') {
            eventSource.close();
            reject(new Error(parsed.message || 'SSE error'));
          }
        } catch {
          onEvent({ event: eventName, data: { raw: (e as MessageEvent).data } });
        }
      });
    });

    // 默认消息处理（无事件名的数据，作为安全回退）
    eventSource.onmessage = (e) => {
      // 所有命名事件已通过 addEventListener 处理，这里只处理未知格式的数据
      onEvent({ event: 'text', data: { text: e.data } });
    };

    eventSource.onerror = () => {
      eventSource.close();
      reject(new Error('SSE connection failed'));
    };
  });
}

/**
 * 续传流式对话 (SSE via POST + fetch ReadableStream)
 * POST /api/v1/agents/route/stream/continue
 */
export function streamDiagnoseContinue(
  payload: { session_id: string; question_id: string; answer: string },
  onEvent: (event: SSEEvent) => void
): Promise<void> {
  return new Promise(async (resolve, reject) => {
    try {
      const res = await fetch(`${API_BASE}/agents/route/stream/continue`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders() },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        reject(new Error(err.detail || `HTTP ${res.status}`));
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        reject(new Error('No response body'));
        return;
      }

      const decoder = new TextDecoder();
      let buffer = '';
      let currentEvent: SSEEventType = 'text';
      let currentData = '';

      const flushEvent = () => {
        if (currentData) {
          try {
            const parsed = JSON.parse(currentData);
            onEvent({ event: currentEvent, data: parsed });
          } catch {
            onEvent({ event: currentEvent, data: { raw: currentData } });
          }
        }
        currentEvent = 'text';
        currentData = '';
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          flushEvent();
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed === '') {
            flushEvent();
            continue;
          }
          if (trimmed.startsWith('event:')) {
            currentEvent = trimmed.slice(6).trim() as SSEEventType;
          } else if (trimmed.startsWith('data:')) {
            currentData += trimmed.slice(5).trim();
          }
        }
      }

      resolve();
    } catch (e) {
      reject(e instanceof Error ? e : new Error(String(e)));
    }
  });
}

/**
 * 获取会话列表
 * GET /api/v1/agents/sessions
 */
export async function listSessions(): Promise<ChatSession[]> {
  const res = await fetch(`${API_BASE}/agents/sessions`, {
    headers: authHeaders(),
  });
  const json: ApiResponse<ChatSession[]> = await res.json();
  if (json.code !== 200) throw new Error(json.message);
  return json.data || [];
}

/**
 * 清除访客 Token
 */
export function clearGuestToken(): void {
  localStorage.removeItem('guest_token');
  localStorage.removeItem('guest_status');
}

/**
 * Agent API 对象 (兼容性导出)
 */
export const agentApi = {
  getGuestStatus: getStoredGuestStatus,
  createGuestSession,
  fetchGuestStatus,
  routeIntent,
  chat,
  streamDiagnose,
  streamDiagnoseContinue,
  listSessions,
  clearGuestToken,
};
