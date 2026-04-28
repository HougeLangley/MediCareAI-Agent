/**
 * Agent API 服务层
 * 文档来源: 14 - API 与通信协议设计
 * 支持 REST + SSE 流式输出
 */

import type { ApiResponse, ChatSession, GuestStatus, RouteResponse, SSEEvent } from '../types/agent';

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';

function getToken(): string | null {
  return localStorage.getItem('access_token');
}

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
 * POST /api/v1/guest/session
 */
export async function createGuestSession(
  fingerprint?: string
): Promise<string> {
  const res = await fetch(`${API_BASE}/guest/session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fingerprint: fingerprint || 'web' }),
  });
  const json: ApiResponse<{ guest_token: string; remaining_interactions: number }> =
    await res.json();
  if (json.code !== 200) throw new Error(json.message);
  localStorage.setItem('guest_token', json.data.guest_token);
  const status: GuestStatus = {
    interaction_count: 0,
    max_interactions: 3,
    remaining: json.data.remaining_interactions,
    can_interact: true,
  };
  localStorage.setItem('guest_status', JSON.stringify(status));
  return json.data.guest_token;
}

/**
 * 查询访客状态
 * GET /api/v1/guest/status
 */
export async function fetchGuestStatus(): Promise<GuestStatus> {
  const res = await fetch(`${API_BASE}/guest/status`, {
    headers: authHeaders(),
  });
  const json: ApiResponse<GuestStatus> = await res.json();
  if (json.code !== 200) throw new Error(json.message);
  localStorage.setItem('guest_status', JSON.stringify(json.data));
  return json.data;
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
 * GET /api/v1/agent/chat/stream
 * 文档定义事件类型: thinking / tool_call / tool_result / structured / text / error / complete
 */
export function streamDiagnose(
  payload: { message: string; session_id?: string },
  onEvent: (event: SSEEvent) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const params = new URLSearchParams();
    params.set('message', payload.message);
    if (payload.session_id) params.set('session_id', payload.session_id);

    const url = `${API_BASE}/agent/chat/stream?${params.toString()}`;
    const eventSource = new EventSource(url);

    eventSource.onmessage = (e) => {
      try {
        const parsed = JSON.parse(e.data);
        onEvent({ event: (parsed.event || 'text') as SSEEvent['event'], data: parsed.data || parsed });
        if (parsed.event === 'complete') {
          eventSource.close();
          resolve();
        }
        if (parsed.event === 'error') {
          eventSource.close();
          reject(new Error(parsed.data?.message || 'SSE error'));
        }
      } catch {
        onEvent({ event: 'text', data: { content: e.data } });
      }
    };

    eventSource.addEventListener('complete', (e) => {
      onEvent({ event: 'complete', data: JSON.parse((e as MessageEvent).data) });
      eventSource.close();
      resolve();
    });

    eventSource.addEventListener('error', (e) => {
      const data = (e as MessageEvent).data;
      onEvent({ event: 'error', data: data ? JSON.parse(data) : { message: 'SSE error' } });
      eventSource.close();
      reject(new Error('SSE stream error'));
    });

    eventSource.onerror = () => {
      eventSource.close();
      reject(new Error('SSE connection failed'));
    };
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
  listSessions,
  clearGuestToken,
};
