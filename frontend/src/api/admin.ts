/** Admin API 服务层 */

import type {
  AuditLogFilters,
  AuditLogItem,
  AuditLogStats,
  DashboardStats,
  LLMProvider,
  LLMProviderCreate,
  LLMProviderUpdate,
  ProviderTestResult,
  SystemSetting,
  SystemSettingCreate,
  SystemSettingUpdate,
} from '../types/admin';

import { API_BASE, authHeaders, jsonHeaders, getToken } from './client';

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

export async function createDocument(data: DocumentCreate & { file?: File }): Promise<DocumentDetail> {
  const formData = new FormData();
  formData.append('title', data.title);
  if (data.content) formData.append('content', data.content);
  formData.append('doc_type', data.doc_type);
  if (data.source_url) formData.append('source_url', data.source_url);
  if (data.department) formData.append('department', data.department);
  if (data.disease_tags?.length) {
    data.disease_tags.forEach(tag => formData.append('disease_tags', tag));
  }
  if (data.drug_name) formData.append('drug_name', data.drug_name);
  if (data.language) formData.append('language', data.language);
  if (data.is_featured) formData.append('is_featured', String(data.is_featured));
  if (data.file) formData.append('file', data.file);

  const res = await fetch(`${API_BASE}/admin/knowledge`, {
    method: 'POST',
    headers: authHeaders(), // No Content-Type for FormData — browser sets it
    body: formData,
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


// ─── Audit Logs ─────────────────────────────────────────────────────────────────────────

export async function listAuditLogs(params?: AuditLogFilters): Promise<AuditLogItem[]> {
  const url = new URL(`${API_BASE}/admin/audit-logs`, window.location.origin);
  if (params?.action) url.searchParams.set('action', params.action);
  if (params?.user_id) url.searchParams.set('user_id', params.user_id);
  if (params?.resource_type) url.searchParams.set('resource_type', params.resource_type);
  if (params?.date_from) url.searchParams.set('date_from', params.date_from);
  if (params?.date_to) url.searchParams.set('date_to', params.date_to);
  if (params?.success !== undefined) url.searchParams.set('success', String(params.success));
  if (params?.skip !== undefined) url.searchParams.set('skip', String(params.skip));
  if (params?.limit !== undefined) url.searchParams.set('limit', String(params.limit));
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse<AuditLogItem[]>(res);
}

export async function getAuditLog(id: string): Promise<AuditLogItem> {
  const res = await fetch(`${API_BASE}/admin/audit-logs/${id}`, { headers: authHeaders() });
  return handleResponse<AuditLogItem>(res);
}

export async function getAuditLogStats(): Promise<AuditLogStats> {
  const res = await fetch(`${API_BASE}/admin/audit-logs/stats/overview`, { headers: authHeaders() });
  return handleResponse<AuditLogStats>(res);
}

// ═══════════════════════════════════════════════════════════════
// Notifications | 站内信
// ═══════════════════════════════════════════════════════════════

import type {
  NotificationListResponse,
  NotificationDetail,
  NotificationUnreadCount,
  NotificationCreate,
  NotificationBroadcastCreate,
} from '../types/admin';

export async function listNotifications(params?: {
  page?: number;
  page_size?: number;
  notification_type?: string;
  priority?: string;
  is_read?: boolean;
  search?: string;
}): Promise<NotificationListResponse> {
  const url = new URL(`${API_BASE}/admin/notifications/notifications`, window.location.origin);
  if (params?.page) url.searchParams.set('page', String(params.page));
  if (params?.page_size) url.searchParams.set('page_size', String(params.page_size));
  if (params?.notification_type) url.searchParams.set('notification_type', params.notification_type);
  if (params?.priority) url.searchParams.set('priority', params.priority);
  if (params?.is_read !== undefined) url.searchParams.set('is_read', String(params.is_read));
  if (params?.search) url.searchParams.set('search', params.search);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse<NotificationListResponse>(res);
}

export async function getUnreadCount(): Promise<NotificationUnreadCount> {
  const res = await fetch(`${API_BASE}/admin/notifications/notifications/unread-count`, { headers: authHeaders() });
  return handleResponse<NotificationUnreadCount>(res);
}

export async function getNotification(id: string): Promise<NotificationDetail> {
  const res = await fetch(`${API_BASE}/admin/notifications/notifications/${id}`, { headers: authHeaders() });
  return handleResponse<NotificationDetail>(res);
}

export async function createNotification(data: NotificationCreate): Promise<NotificationDetail> {
  const res = await fetch(`${API_BASE}/admin/notifications/notifications`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse<NotificationDetail>(res);
}

export async function broadcastNotification(data: NotificationBroadcastCreate): Promise<{ message: string; notification_id: string; recipient_count: number }> {
  const res = await fetch(`${API_BASE}/admin/notifications/notifications/broadcast`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse<{ message: string; notification_id: string; recipient_count: number }>(res);
}

export async function markNotificationRead(id: string, is_read = true): Promise<NotificationDetail> {
  const res = await fetch(`${API_BASE}/admin/notifications/notifications/${id}/read`, {
    method: 'PATCH',
    headers: jsonHeaders(),
    body: JSON.stringify({ is_read }),
  });
  return handleResponse<NotificationDetail>(res);
}

export async function deleteNotification(id: string): Promise<{ message: string; deleted_id: string }> {
  const res = await fetch(`${API_BASE}/admin/notifications/notifications/${id}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  return handleResponse<{ message: string; deleted_id: string }>(res);
}

// ═══════════════════════════════════════════════════════════════
// Email Management | 邮件管理
// ═══════════════════════════════════════════════════════════════

import type {
  EmailConfig,
  EmailConfigCreate,
  EmailConfigUpdate,
  EmailConfigListResponse,
  EmailTemplate,
  EmailTemplateCreate,
  EmailTemplateUpdate,
  EmailTemplateListResponse,
  EmailLogListResponse,
  EmailProviderPresetsResponse,
  EmailServiceStatus,
} from '../types/admin';

export async function listEmailConfigs(): Promise<EmailConfigListResponse> {
  const res = await fetch(`${API_BASE}/admin/email/configs`, { headers: authHeaders() });
  return handleResponse<EmailConfigListResponse>(res);
}

export async function getEmailConfig(id: string): Promise<EmailConfig> {
  const res = await fetch(`${API_BASE}/admin/email/configs/${id}`, { headers: authHeaders() });
  return handleResponse<EmailConfig>(res);
}

export async function createEmailConfig(data: EmailConfigCreate): Promise<EmailConfig> {
  const res = await fetch(`${API_BASE}/admin/email/configs`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse<EmailConfig>(res);
}

export async function updateEmailConfig(id: string, data: EmailConfigUpdate): Promise<EmailConfig> {
  const res = await fetch(`${API_BASE}/admin/email/configs/${id}`, {
    method: 'PUT',
    headers: jsonHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse<EmailConfig>(res);
}

export async function deleteEmailConfig(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/admin/email/configs/${id}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  return handleResponse<void>(res);
}

export async function testEmailConfig(id: string, test_email: string): Promise<{ success: boolean; message: string }> {
  const res = await fetch(`${API_BASE}/admin/email/configs/${id}/test`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify({ test_email }),
  });
  return handleResponse<{ success: boolean; message: string }>(res);
}

export async function setDefaultEmailConfig(id: string): Promise<EmailConfig> {
  const res = await fetch(`${API_BASE}/admin/email/configs/${id}/set-default`, {
    method: 'POST',
    headers: authHeaders(),
  });
  return handleResponse<EmailConfig>(res);
}

export async function getEmailStatus(): Promise<EmailServiceStatus> {
  const res = await fetch(`${API_BASE}/admin/email/status`, { headers: authHeaders() });
  return handleResponse<EmailServiceStatus>(res);
}

export async function listEmailTemplates(): Promise<EmailTemplateListResponse> {
  const res = await fetch(`${API_BASE}/admin/email/templates`, { headers: authHeaders() });
  return handleResponse<EmailTemplateListResponse>(res);
}

export async function createEmailTemplate(data: EmailTemplateCreate): Promise<EmailTemplate> {
  const res = await fetch(`${API_BASE}/admin/email/templates`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse<EmailTemplate>(res);
}

export async function updateEmailTemplate(id: string, data: EmailTemplateUpdate): Promise<EmailTemplate> {
  const res = await fetch(`${API_BASE}/admin/email/templates/${id}`, {
    method: 'PUT',
    headers: jsonHeaders(),
    body: JSON.stringify(data),
  });
  return handleResponse<EmailTemplate>(res);
}

export async function deleteEmailTemplate(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/admin/email/templates/${id}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  return handleResponse<void>(res);
}

export async function listEmailLogs(params?: {
  page?: number;
  page_size?: number;
  status?: string;
  search?: string;
}): Promise<EmailLogListResponse> {
  const url = new URL(`${API_BASE}/admin/email/logs`, window.location.origin);
  if (params?.page) url.searchParams.set('page', String(params.page));
  if (params?.page_size) url.searchParams.set('page_size', String(params.page_size));
  if (params?.status) url.searchParams.set('status', params.status);
  if (params?.search) url.searchParams.set('search', params.search);
  const res = await fetch(url.toString(), { headers: authHeaders() });
  return handleResponse<EmailLogListResponse>(res);
}

export async function getEmailProviderPresets(): Promise<EmailProviderPresetsResponse> {
  const res = await fetch(`${API_BASE}/admin/email/providers`, { headers: authHeaders() });
  return handleResponse<EmailProviderPresetsResponse>(res);
}
