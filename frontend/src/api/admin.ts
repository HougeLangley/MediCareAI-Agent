/** Admin API 服务层 */

import type {
  DashboardStats,
  LLMProvider,
  LLMProviderCreate,
  LLMProviderUpdate,
  ProviderTestResult,
  SystemSetting,
  SystemSettingCreate,
  SystemSettingUpdate,
} from '../types/admin';

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';

function getToken(): string | null {
  return localStorage.getItem('access_token');
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function jsonHeaders(): Record<string, string> {
  return { 'Content-Type': 'application/json', ...authHeaders() };
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return undefined as unknown as T;
  return res.json();
}

// ─── LLM Provider Configs ───────────────────────────────────

export async function listLLMProviders(platform?: string): Promise<LLMProvider[]> {
  const url = new URL(`${API_BASE}/admin/llm-providers`, window.location.origin);
  if (platform) url.searchParams.set('platform', platform);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse<LLMProvider[]>(res);
}

export async function createLLMProvider(data: LLMProviderCreate): Promise<LLMProvider> {
  const res = await fetch(`${API_BASE}/admin/llm-providers`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse<LLMProvider>(res);
}

export async function getLLMProvider(provider: string, platform?: string | null): Promise<LLMProvider> {
  const url = new URL(`${API_BASE}/admin/llm-providers/${provider}`, window.location.origin);
  if (platform) url.searchParams.set('platform', platform);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse<LLMProvider>(res);
}

export async function updateLLMProvider(
  provider: string,
  data: LLMProviderUpdate,
  platform?: string | null
): Promise<LLMProvider> {
  const url = new URL(`${API_BASE}/admin/llm-providers/${provider}`, window.location.origin);
  if (platform) url.searchParams.set('platform', platform);
  const res = await fetch(url.toString(), {
    method: 'PATCH',
    headers: jsonHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse<LLMProvider>(res);
}

export async function deleteLLMProvider(provider: string, platform?: string | null): Promise<void> {
  const url = new URL(`${API_BASE}/admin/llm-providers/${provider}`, window.location.origin);
  if (platform) url.searchParams.set('platform', platform);
  const res = await fetch(url.toString(), {
    method: 'DELETE',
    headers: authHeaders(),
  });
  return handleResponse<void>(res);
}

export async function testLLMProvider(provider: string, platform?: string | null): Promise<ProviderTestResult> {
  const url = new URL(`${API_BASE}/admin/llm-providers/${provider}/test`, window.location.origin);
  if (platform) url.searchParams.set('platform', platform);
  const res = await fetch(url.toString(), {
    method: 'POST',
    headers: authHeaders(),
  });
  return handleResponse<ProviderTestResult>(res);
}

// ─── System Settings ────────────────────────────────────────

export async function listSettings(): Promise<SystemSetting[]> {
  const res = await fetch(`${API_BASE}/admin/settings`, { headers: authHeaders() });
  return handleResponse<SystemSetting[]>(res);
}

export async function createSetting(data: SystemSettingCreate): Promise<SystemSetting> {
  const res = await fetch(`${API_BASE}/admin/settings`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse<SystemSetting>(res);
}

export async function getSetting(key: string): Promise<SystemSetting> {
  const res = await fetch(`${API_BASE}/admin/settings/${key}`, { headers: authHeaders() });
  return handleResponse<SystemSetting>(res);
}

export async function updateSetting(key: string, data: SystemSettingUpdate): Promise<SystemSetting> {
  const res = await fetch(`${API_BASE}/admin/settings/${key}`, {
    method: 'PATCH',
    headers: jsonHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse<SystemSetting>(res);
}

export async function deleteSetting(key: string): Promise<void> {
  const res = await fetch(`${API_BASE}/admin/settings/${key}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  return handleResponse<void>(res);
}

export async function batchUpdateSettings(items: SystemSettingCreate[]): Promise<SystemSetting[]> {
  const res = await fetch(`${API_BASE}/admin/settings/batch`, {
    method: 'PATCH',
    headers: jsonHeaders(),
    body: JSON.stringify({ items }),
  });
  return handleResponse<SystemSetting[]>(res);
}

// ─── Dashboard ──────────────────────────────────────────────

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const res = await fetch(`${API_BASE}/admin/dashboard/stats`, { headers: authHeaders() });
  return handleResponse<DashboardStats>(res);
}

// ─── Auth helpers ───────────────────────────────────────────

export async function adminLogin(email: string, password: string): Promise<{ access_token: string; token_type: string }> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail || json.message || 'Login failed');
  localStorage.setItem('access_token', json.data.access_token);
  return json.data;
}

export function logout(): void {
  localStorage.removeItem('access_token');
}

export function isLoggedIn(): boolean {
  return !!getToken();
}
