/** API 统一客户端配置
 * 所有 API 模块从此处导入 API_BASE，禁止自行定义
 */

export const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';

/** 获取当前访问令牌 */
export function getToken(): string | null {
  return localStorage.getItem('access_token');
}

/** 构建认证请求头 */
export function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** 构建 JSON 请求头（含认证） */
export function jsonHeaders(): Record<string, string> {
  return { 'Content-Type': 'application/json', ...authHeaders() };
}
