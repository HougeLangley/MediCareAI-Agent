/** Admin 管理面板类型定义 */

export interface LLMProvider {
  id: string;
  provider: string;
  platform: string | null;
  name: string;
  base_url: string;
  default_model: string;
  model_type: string;
  is_active: boolean;
  is_default: boolean;
  api_key_masked: string;
  created_at: string;
  updated_at: string;
}

export interface LLMProviderCreate {
  provider: string;
  platform: string | null;
  name: string;
  base_url: string;
  api_key: string;
  default_model: string;
  model_type: string;
  is_active?: boolean;
  is_default?: boolean;
}

export interface LLMProviderUpdate {
  name?: string;
  base_url?: string;
  api_key?: string;
  default_model?: string;
  model_type?: string;
  platform?: string | null;
  is_active?: boolean;
  is_default?: boolean;
}

export interface SystemSetting {
  id: string;
  key: string;
  value: string;
  description: string | null;
  is_sensitive: boolean;
  category: string;
  value_type: string;
  options: string | null;
  created_at: string;
  updated_at: string;
}

export interface SystemSettingCreate {
  key: string;
  value: string;
  description?: string | null;
  is_sensitive?: boolean;
  category?: string;
  value_type?: string;
  options?: string | null;
}

export interface SystemSettingUpdate {
  value?: string;
  description?: string | null;
  is_sensitive?: boolean;
  category?: string;
  value_type?: string;
  options?: string | null;
}

export interface BatchSettingsRequest {
  items: SystemSettingCreate[];
}

export interface DashboardStats {
  users: {
    total: number;
    by_role: Record<string, number>;
  };
  llm_providers: {
    total: number;
    active: number;
  };
  system_settings: number;
  timestamp: string;
}

export interface ProviderTestResult {
  provider: string;
  platform: string;
  status: string;
  detail?: string;
  available_models?: string[];
}

// ─── User Management ────────────────────────────────────────────

export interface UserItem {
  id: string;
  email: string;
  full_name: string;
  role: string;
  status: string;
  is_verified: boolean;
  license_number: string | null;
  hospital: string | null;
  department: string | null;
  title: string | null;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
}

export interface UserAdminUpdate {
  full_name?: string;
  status?: string;
  is_verified?: boolean;
  license_number?: string | null;
  hospital?: string | null;
  department?: string | null;
  title?: string | null;
}

// ─── Doctor Verification ──────────────────────────────────────

export interface DoctorVerifyRequest {
  action: 'approve' | 'reject';
  reason?: string;
}

// ─── Knowledge Base (Document) ─────────────────────────────────

export type DocumentType = 'platform_guideline' | 'case_report' | 'drug_reference';
export type ReviewStatus = 'pending' | 'agent_reviewed' | 'approved' | 'rejected' | 'revision_requested';

export interface DocumentItem {
  id: string;
  title: string;
  doc_type: DocumentType;
  source_type: string | null;
  review_status: ReviewStatus;
  department: string | null;
  disease_tags: string[] | null;
  drug_name: string | null;
  is_active: boolean;
  is_featured: boolean;
  chunk_count: number;
  vectorized_at: string | null;
  created_at: string;
  updated_at: string;
  source_url?: string | null;
}

export interface DocumentDetail extends DocumentItem {
  content: string;
  source_url: string | null;
  uploaded_by: string | null;
  reviewed_by: string | null;
  agent_review_score: number | null;
  agent_review_notes: string | null;
  embedding_model: string | null;
}

export interface DocumentCreate {
  title: string;
  content: string;
  doc_type: DocumentType;
  source_url?: string | null;
  department?: string | null;
  disease_tags?: string[];
  drug_name?: string | null;
  language?: string;
  is_featured?: boolean;
}

export interface DocumentUpdate {
  title?: string;
  content?: string;
  doc_type?: DocumentType;
  source_url?: string | null;
  department?: string | null;
  disease_tags?: string[] | null;
  drug_name?: string | null;
  language?: string | null;
  is_active?: boolean;
  is_featured?: boolean;
}

export interface DocumentReviewLog {
  id: string;
  document_id: string;
  reviewer_type: string;
  reviewer_id: string | null;
  action: string;
  score: number | null;
  comments: string | null;
  reviewed_at: string;
}

export interface ReviewAction {
  action: 'approve' | 'reject' | 'request_revision';
  comments?: string;
  score?: number;
}

export interface ReviewQueueItem {
  id: string;
  title: string;
  doc_type: DocumentType;
  review_status: ReviewStatus;
  agent_review_score: number | null;
  agent_review_notes: string | null;
  uploaded_by: string | null;
  created_at: string;
}


// ─── Audit Logs ─────────────────────────────────────────────────────────────────────────

export type AuditActionType =
  | 'LOGIN'
  | 'LOGOUT'
  | 'PASSWORD_CHANGE'
  | 'ROLE_SWITCH'
  | 'DOCTOR_VERIFY'
  | 'DOCTOR_REJECT'
  | 'DOCUMENT_CREATE'
  | 'DOCUMENT_UPDATE'
  | 'DOCUMENT_DELETE'
  | 'DOCUMENT_REVIEW'
  | 'DOCUMENT_TOGGLE'
  | 'SETTINGS_CHANGE'
  | 'LLM_CONFIG_CREATE'
  | 'LLM_CONFIG_UPDATE'
  | 'LLM_CONFIG_DELETE'
  | 'LLM_CONFIG_TEST'
  | 'USER_CREATE'
  | 'USER_UPDATE'
  | 'USER_DELETE'
  | 'AGENT_SESSION'
  | 'TOOL_CALL';

export type AuditResourceType =
  | 'USER'
  | 'DOCTOR'
  | 'DOCUMENT'
  | 'SYSTEM_SETTING'
  | 'LLM_PROVIDER'
  | 'AGENT_SESSION'
  | 'UNKNOWN';

export interface AuditLogItem {
  id: string;
  user_id: string | null;
  user_email: string | null;
  user_role: string | null;
  action: AuditActionType;
  resource_type: AuditResourceType;
  resource_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  user_agent: string | null;
  success: boolean;
  error_message: string | null;
  created_at: string;
}

export interface AuditLogStats {
  total_today: number;
  total_week: number;
  failed_today: number;
  action_breakdown: { action: string; count: number }[];
}

export interface AuditLogFilters {
  action?: string;
  user_id?: string;
  resource_type?: string;
  date_from?: string;
  date_to?: string;
  success?: boolean;
  skip?: number;
  limit?: number;
}

// ═══════════════════════════════════════════════════════════════
// Notifications | 站内信
// ═══════════════════════════════════════════════════════════════

export type NotificationType = 'system' | 'announcement' | 'direct' | 'reminder';
export type NotificationPriority = 'high' | 'medium' | 'low';

export interface NotificationSender {
  id: string;
  full_name: string;
  role: string;
}

export interface NotificationItem {
  id: string;
  notification_type: NotificationType;
  priority: NotificationPriority;
  subject: string;
  content_preview: string;
  is_read: boolean;
  read_at: string | null;
  broadcast: boolean;
  sender: NotificationSender | null;
  created_at: string;
}

export interface NotificationDetail {
  id: string;
  notification_type: NotificationType;
  priority: NotificationPriority;
  subject: string;
  content: string;
  action_url: string | null;
  is_read: boolean;
  read_at: string | null;
  broadcast: boolean;
  sender: NotificationSender | null;
  recipient: NotificationSender | null;
  created_at: string;
  updated_at: string;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  unread_count: number;
}

export interface NotificationUnreadCount {
  total: number;
  system: number;
  announcement: number;
  direct: number;
  reminder: number;
}

export interface NotificationCreate {
  notification_type: NotificationType;
  priority: NotificationPriority;
  subject: string;
  content: string;
  recipient_id?: string | null;
  action_url?: string | null;
  broadcast?: boolean;
}

export interface NotificationBroadcastCreate {
  subject: string;
  content: string;
  priority?: NotificationPriority;
  action_url?: string | null;
}

// ═══════════════════════════════════════════════════════════════
// Email Management | 邮件管理
// ═══════════════════════════════════════════════════════════════

export type SmtpSecurity = 'starttls' | 'ssl' | 'none';
export type EmailSendStatus = 'pending' | 'sent' | 'failed' | 'retrying';

export interface EmailConfig {
  id: string;
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_from_email: string;
  smtp_from_name: string;
  smtp_security: SmtpSecurity;
  is_active: boolean;
  is_default: boolean;
  test_status: string;
  test_message: string | null;
  tested_at: string | null;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface EmailConfigCreate {
  smtp_host: string;
  smtp_port: number;
  smtp_user: string;
  smtp_password: string;
  smtp_from_email: string;
  smtp_from_name?: string;
  smtp_security?: SmtpSecurity;
  description?: string | null;
  is_default?: boolean;
}

export interface EmailConfigUpdate {
  smtp_host?: string;
  smtp_port?: number;
  smtp_user?: string;
  smtp_password?: string;
  smtp_from_email?: string;
  smtp_from_name?: string;
  smtp_security?: SmtpSecurity;
  is_active?: boolean;
  is_default?: boolean;
  description?: string | null;
}

export interface EmailConfigListResponse {
  items: EmailConfig[];
  total: number;
}

export interface EmailTemplate {
  id: string;
  name: string;
  description: string | null;
  subject: string;
  html_body: string;
  text_body: string | null;
  variables: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface EmailTemplateCreate {
  name: string;
  description?: string | null;
  subject: string;
  html_body: string;
  text_body?: string | null;
  variables?: string | null;
  is_active?: boolean;
}

export interface EmailTemplateUpdate {
  name?: string;
  description?: string | null;
  subject?: string;
  html_body?: string;
  text_body?: string | null;
  variables?: string | null;
  is_active?: boolean;
}

export interface EmailTemplateListResponse {
  items: EmailTemplate[];
  total: number;
}

export interface EmailLog {
  id: string;
  config_id: string | null;
  template_id: string | null;
  recipient_email: string;
  subject: string;
  body_preview: string | null;
  status: EmailSendStatus;
  retry_count: number;
  error_message: string | null;
  sent_at: string | null;
  failed_at: string | null;
  created_at: string;
}

export interface EmailLogListResponse {
  items: EmailLog[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface EmailProviderPreset {
  id: string;
  name: string;
  category: string;
  category_label: string;
  icon: string;
  description: string;
  smtp: {
    host: string;
    port: number;
    security: SmtpSecurity;
  };
  help_text: string;
  help_link: string | null;
}

export interface EmailProviderCategory {
  label: string;
  description: string;
  icon: string;
}

export interface EmailProviderPresetsResponse {
  providers: EmailProviderPreset[];
  categories: Record<string, EmailProviderCategory>;
}

export interface EmailServiceStatus {
  is_available: boolean;
  config_source: string;
  smtp_host: string | null;
  smtp_port: number | null;
  smtp_user: string | null;
  from_email: string | null;
  from_name: string | null;
  smtp_security: SmtpSecurity | null;
}
