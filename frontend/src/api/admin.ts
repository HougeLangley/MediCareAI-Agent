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

export async function getLLMProvider(id: string): Promise<LLMProvider> {
  const res = await fetch(`${API_BASE}/admin/llm-providers/${id}`, { headers: authHeaders() });
  return handleResponse<LLMProvider>(res);
}

export async function updateLLMProvider(
  id: string,
  data: LLMProviderUpdate
): Promise<LLMProvider> {
  const res = await fetch(`${API_BASE}/admin/llm-providers/${id}`, {
    method: 'PATCH',
    headers: jsonHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse<LLMProvider>(res);
}

export async function deleteLLMProvider(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/admin/llm-providers/${id}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  return handleResponse<void>(res);
}

export async function testLLMProvider(id: string): Promise<ProviderTestResult> {
  const res = await fetch(`${API_BASE}/admin/llm-providers/${id}/test`, {
    method: 'POST',
    headers: authHeaders(),
  });
  return handleResponse<ProviderTestResult>(res);
}

// ─── System Settings ────────────────────────────────────────

export async function listSettings(category?: string): Promise<SystemSetting[]> {
  const url = new URL(`${API_BASE}/admin/settings`, window.location.origin);
  if (category) url.searchParams.set('category', category);
  const res = await fetch(url.toString(), { headers: authHeaders() });
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

export async function adminLogin(email: string, password: string): Promise<{
  access_token: string;
  token_type: string;
  password_change_required?: boolean;
}> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username: email, password }),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail || json.message || 'Login failed');
  localStorage.setItem('access_token', json.access_token);
  if (json.password_change_required) {
    localStorage.setItem('password_change_required', 'true');
  } else {
    localStorage.removeItem('password_change_required');
  }
  return json;
}

export async function changePassword(data: { old_password?: string; new_password: string }): Promise<void> {
  const res = await fetch(`${API_BASE}/auth/change-password`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  localStorage.removeItem('password_change_required');
}

export async function getMe(): Promise<{
  id: string;
  email: string;
  role: string;
  full_name: string;
  password_change_required?: boolean;
}> {
  const res = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders() });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail || 'Failed to get user info');
  return json;
}

export function logout(): void {
  localStorage.removeItem('access_token');
}

export function isLoggedIn(): boolean {
  return !!getToken();
}

// ─── User Management ────────────────────────────────────────────

import type { UserItem, UserAdminUpdate } from '../types/admin';

export async function listUsers(params?: {
  role?: string;
  status?: string;
  search?: string;
  skip?: number;
  limit?: number;
}): Promise<UserItem[]> {
  const url = new URL(`${API_BASE}/admin/users`, window.location.origin);
  if (params?.role) url.searchParams.set('role', params.role);
  if (params?.status) url.searchParams.set('status', params.status);
  if (params?.search) url.searchParams.set('search', params.search);
  if (params?.skip !== undefined) url.searchParams.set('skip', String(params.skip));
  if (params?.limit !== undefined) url.searchParams.set('limit', String(params.limit));
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse<UserItem[]>(res);
}

export async function getUser(id: string): Promise<UserItem> {
  const res = await fetch(`${API_BASE}/admin/users/${id}`, { headers: authHeaders() });
  return handleResponse<UserItem>(res);
}

export async function updateUser(id: string, data: UserAdminUpdate): Promise<UserItem> {
  const res = await fetch(`${API_BASE}/admin/users/${id}`, {
    method: 'PATCH',
    headers: jsonHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse<UserItem>(res);
}

// ─── Doctor Verification ──────────────────────────────────────

import type { DoctorVerifyRequest } from '../types/admin';

export async function listDoctors(params?: {
  is_verified?: boolean;
  status?: string;
  search?: string;
  skip?: number;
  limit?: number;
}): Promise<UserItem[]> {
  const url = new URL(`${API_BASE}/admin/doctors`, window.location.origin);
  if (params?.is_verified !== undefined) url.searchParams.set('is_verified', String(params.is_verified));
  if (params?.status) url.searchParams.set('status', params.status);
  if (params?.search) url.searchParams.set('search', params.search);
  if (params?.skip !== undefined) url.searchParams.set('skip', String(params.skip));
  if (params?.limit !== undefined) url.searchParams.set('limit', String(params.limit));
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse<UserItem[]>(res);
}

export async function verifyDoctor(id: string, data: DoctorVerifyRequest): Promise<UserItem> {
  const res = await fetch(`${API_BASE}/admin/doctors/${id}/verify`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse<UserItem>(res);
}

// ─── Knowledge Base Management ─────────────────────────────────

import type {
  DocumentCreate,
  DocumentDetail,
  DocumentItem,
  DocumentReviewLog,
  DocumentUpdate,
  ReviewAction,
  ReviewQueueItem,
} from '../types/admin';

export async function listDocuments(params?: {
  doc_type?: string;
  status?: string;
  search?: string;
  is_active?: boolean;
  skip?: number;
  limit?: number;
}): Promise<DocumentItem[]> {
  const url = new URL(`${API_BASE}/admin/knowledge`, window.location.origin);
  if (params?.doc_type) url.searchParams.set('doc_type', params.doc_type);
  if (params?.status) url.searchParams.set('status', params.status);
  if (params?.search) url.searchParams.set('search', params.search);
  if (params?.is_active !== undefined) url.searchParams.set('is_active', String(params.is_active));
  if (params?.skip !== undefined) url.searchParams.set('skip', String(params.skip));
  if (params?.limit !== undefined) url.searchParams.set('limit', String(params.limit));
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse<DocumentItem[]>(res);
}

export async function getDocument(id: string): Promise<DocumentDetail> {
  const res = await fetch(`${API_BASE}/admin/knowledge/${id}`, { headers: authHeaders() });
  return handleResponse<DocumentDetail>(res);
}

export async function createDocument(data: DocumentCreate): Promise<DocumentDetail> {
  const res = await fetch(`${API_BASE}/admin/knowledge`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse<DocumentDetail>(res);
}

export async function updateDocument(id: string, data: DocumentUpdate): Promise<DocumentDetail> {
  const res = await fetch(`${API_BASE}/admin/knowledge/${id}`, {
    method: 'PATCH',
    headers: jsonHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse<DocumentDetail>(res);
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/admin/knowledge/${id}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  return handleResponse<void>(res);
}

export async function toggleDocumentActive(id: string): Promise<{ id: string; is_active: boolean }> {
  const res = await fetch(`${API_BASE}/admin/knowledge/${id}/toggle`, {
    method: 'PATCH',
    headers: authHeaders(),
  });
  return handleResponse<{ id: string; is_active: boolean }>(res);
}

// ─── Document Review Queue ─────────────────────────────────

export async function listReviewQueue(params?: {
  status?: string;
  skip?: number;
  limit?: number;
}): Promise<ReviewQueueItem[]> {
  const url = new URL(`${API_BASE}/admin/knowledge/reviews`, window.location.origin);
  if (params?.status) url.searchParams.set('status', params.status);
  if (params?.skip !== undefined) url.searchParams.set('skip', String(params.skip));
  if (params?.limit !== undefined) url.searchParams.set('limit', String(params.limit));
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse<ReviewQueueItem[]>(res);
}

export async function getDocumentReviewHistory(id: string): Promise<DocumentReviewLog[]> {
  const res = await fetch(`${API_BASE}/admin/knowledge/reviews/${id}/history`, {
    headers: authHeaders(),
  });
  return handleResponse<DocumentReviewLog[]>(res);
}

export async function reviewDocument(id: string, data: ReviewAction): Promise<{
  id: string;
  review_status: string;
  action: string;
  message: string;
}> {
  const res = await fetch(`${API_BASE}/admin/knowledge/reviews/${id}`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse<{ id: string; review_status: string; action: string; message: string }>(res);
}
