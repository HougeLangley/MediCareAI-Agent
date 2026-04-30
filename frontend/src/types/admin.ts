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
  phone: string | null;
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
  phone?: string | null;
  status?: string;
  is_verified?: boolean;
  license_number?: string | null;
  hospital?: string | null;
  department?: string | null;
  title?: string | null;
}
