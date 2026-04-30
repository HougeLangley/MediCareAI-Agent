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
