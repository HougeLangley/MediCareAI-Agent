/** 第三方 LLM Provider 域名配置
 * 禁止在组件中直接硬编码第方域名，所有地址必须从此处导入。
 */

export const PROVIDER_DOMAINS = {
  moonshot: {
    api: 'https://api.moonshot.cn',
    platform: 'https://platform.moonshot.cn',
  },
  opencode: {
    api: 'https://opencode.ai',
    zen: 'https://opencode.ai/zen',
  },
  zhipu: {
    api: 'https://open.bigmodel.cn',
  },
  jina: {
    api: 'https://api.jina.ai',
  },
  anthropic: {
    api: 'https://api.anthropic.com',
  },
  openai: {
    api: 'https://api.openai.com',
  },
} as const;

/** 构建完整的 Base URL */
export function buildBaseUrl(provider: keyof typeof PROVIDER_DOMAINS, path: string): string {
  const base = PROVIDER_DOMAINS[provider].api;
  return `${base}${path}`;
}
