/** 认证 API 服务层 — 登录/注册/身份切换 */

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';

function jsonHeaders(): Record<string, string> {
  return { 'Content-Type': 'application/json' };
}

export interface LoginRequest {
  email: string;
  password: string;
  role: 'patient' | 'doctor' | 'admin';
}

export interface LoginResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in?: number;
  user: {
    id: string;
    email: string;
    role: string;
    name?: string;
  };
}

export interface RegisterRequest {
  email: string;
  password: string;
  role: 'patient' | 'doctor';
  name: string;
  phone?: string;
}

export interface UserInfo {
  id: string;
  email: string;
  role: string;
  name?: string;
  full_name?: string;
}

export async function login(data: LoginRequest): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      username: data.email,
      password: data.password,
    }),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail || json.message || 'Login failed');
  localStorage.setItem('access_token', json.access_token);
  localStorage.setItem('user_role', json.user?.role || data.role);
  return json;
}

export async function register(data: RegisterRequest): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(data),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail || json.message || 'Register failed');
  return json;
}

export async function getMe(): Promise<UserInfo> {
  const token = localStorage.getItem('access_token');
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.detail || 'Failed to get user info');
  return json;
}

export async function logout(): Promise<void> {
  const token = localStorage.getItem('access_token');
  if (token) {
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    }).catch(() => {});
  }
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_role');
  localStorage.removeItem('guest_token');
  localStorage.removeItem('guest_status');
}

export function getToken(): string | null {
  return localStorage.getItem('access_token');
}

export function getUserRole(): string | null {
  return localStorage.getItem('user_role');
}

export function isLoggedIn(): boolean {
  return !!getToken();
}
