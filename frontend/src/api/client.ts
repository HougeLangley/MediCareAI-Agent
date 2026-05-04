/** API 统一客户端配置
 * 所有 API 模块从此处导入 API_BASE，禁止自行定义
 */
const rawBase = import.meta.env.VITE_API_BASE || '/api/v1';

/** 生产环境防御：绝对 HTTP URL 自动升级为 HTTPS，避免 Mixed Content */
function ensureHttps(base: string): string {
  if (
    base.startsWith('http://') &&
    typeof window !== 'undefined' &&
    window.location.protocol === 'https:'
  ) {
    return base.replace('http://', 'https://');
  }
  return base;
}

export const API_BASE = ensureHttps(rawBase);

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
