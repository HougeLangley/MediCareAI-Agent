import { useEffect, useState, useCallback } from 'react';
import {
  Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle,
  IconButton, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField,
  Typography, Switch, FormControlLabel, Tooltip, CircularProgress, Alert, Paper,
  Select, MenuItem, FormControl, InputLabel, Collapse, Autocomplete,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Block';
import TestIcon from '@mui/icons-material/NetworkCheck';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import {
  listLLMProviders, createLLMProvider, updateLLMProvider, deleteLLMProvider, testLLMProvider,
} from '../../api/admin';
import type { LLMProvider, LLMProviderCreate, LLMProviderUpdate } from '../../types/admin';
import { flexRowGap1 } from '@/styles/sxUtils';


const emptyForm: LLMProviderCreate = {
  provider: '',
  platform: null,
  name: '',
  base_url: '',
  api_key: '',
  default_model: '',
  model_type: 'diagnosis',
  is_active: true,
  is_default: false,
};

const MODEL_TYPE_OPTIONS = [
  { value: 'diagnosis', label: '诊断/对话 — 通用大语言模型' },
  { value: 'multimodal', label: '多模态 — 支持图文理解的大模型' },
  { value: 'embedding', label: '向量嵌入 — 文本向量化专用模型' },
  { value: 'reranking', label: '重排序 — RAG 结果精排专用模型' },
  { value: 'extraction', label: '结构化提取 — 文档关键字段解析' },
  { value: 'summarization', label: '摘要 — 文本摘要生成' },
  { value: 'classify', label: '分类/路由 — 文档分类与意图识别' },
  { value: 'vision', label: '医学影像 — 影像专用分析模型' },
];

// 官方 API 配置参考（OpenAI 兼容格式，聚焦国内模型）
interface ProviderGuide {
  name: string;
  baseUrl: string;
  models: { id: string; label: string; type: string }[];
  notes: string[];
}

const PROVIDER_GUIDES: Record<string, ProviderGuide> = {
  moonshot: {
    name: 'Moonshot AI (Kimi)',
    baseUrl: 'https://api.moonshot.cn/v1',
    models: [
      { id: 'kimi-2.5', label: 'kimi-2.5（推荐，长上下文通用模型）', type: 'diagnosis' },
      { id: 'kimi-2.6', label: 'kimi-2.6（推荐，最新旗舰模型）', type: 'diagnosis' },
    ],
    notes: [
      '支持 OpenAI 兼容 API 格式',
      'Base URL: https://api.moonshot.cn/v1',
      'API Key 在 https://platform.moonshot.cn 申请',
      '默认流量限制 60 RPM',
      '如需旧版 moonshot-v1 系列模型可手动输入',
    ],
  },
  opencode: {
    name: 'OpenCode Go',
    baseUrl: 'https://opencode.ai/zen/go/v1',
    models: [
      { id: 'kimi-k2.5', label: 'kimi-k2.5（Kimi K2.5，长上下文通用）', type: 'diagnosis' },
      { id: 'kimi-k2.6', label: 'kimi-k2.6（Kimi K2.6，旗舰模型）', type: 'diagnosis' },
      { id: 'glm-5.1', label: 'glm-5.1（GLM-5.1，高端模型）', type: 'diagnosis' },
      { id: 'glm-5', label: 'glm-5（GLM-5，性能均衡）', type: 'diagnosis' },
      { id: 'deepseek-v4-pro', label: 'deepseek-v4-pro（DeepSeek V4 Pro，推理强）', type: 'diagnosis' },
      { id: 'deepseek-v4-flash', label: 'deepseek-v4-flash（DeepSeek V4 Flash，速度快）', type: 'diagnosis' },
      { id: 'mimo-v2-pro', label: 'mimo-v2-pro（MiMo-V2-Pro）', type: 'diagnosis' },
      { id: 'mimo-v2-omni', label: 'mimo-v2-omni（MiMo-V2-Omni，多模态）', type: 'multimodal' },
      { id: 'mimo-v2.5-pro', label: 'mimo-v2.5-pro（MiMo-V2.5-Pro）', type: 'diagnosis' },
      { id: 'mimo-v2.5', label: 'mimo-v2.5（MiMo-V2.5，256K上下文）', type: 'diagnosis' },
      { id: 'qwen3.6-plus', label: 'qwen3.6-plus（通义千问 3.6 Plus）', type: 'diagnosis' },
      { id: 'qwen3.5-plus', label: 'qwen3.5-plus（通义千问 3.5 Plus）', type: 'diagnosis' },
    ],
    notes: [
      '支持 OpenAI 兼容 API 格式',
      'Base URL: https://opencode.ai/zen/go/v1',
      'API Key 在 https://opencode.ai/zen 订阅后获取',
      '首月 $5，之后 $10/月',
      '注意：MiniMax M2.5/M2.7 使用 Anthropic 格式，未包含',
    ],
  },
  zhipu: {
    name: '智谱 AI',
    baseUrl: 'https://open.bigmodel.cn/api/paas/v4/',
    models: [
      { id: 'glm-4', label: 'glm-4（旗舰模型，综合能力最强）', type: 'diagnosis' },
      { id: 'glm-4v', label: 'glm-4v（多模态，支持图片理解）', type: 'multimodal' },
      { id: 'glm-4-flash', label: 'glm-4-flash（轻量版，速度快成本低）', type: 'diagnosis' },
      { id: 'glm-4-plus', label: 'glm-4-plus（Plus 版本，性能更强）', type: 'diagnosis' },
      { id: 'glm-4-air', label: 'glm-4-air（Air 版本，性价比优化）', type: 'diagnosis' },
    ],
    notes: ['支持 OpenAI 兼容 API', 'API Key 在 open.bigmodel.cn 申请', 'glm-4v 支持图片输入'],
  },
  jina: {
    name: 'Jina AI',
    baseUrl: 'https://api.jina.ai/v1',
    models: [
      { id: 'jina-reranker-v2-base-multilingual', label: 'jina-reranker-v2-base-multilingual（多语言重排序）', type: 'reranking' },
      { id: 'jina-embeddings-v3', label: 'jina-embeddings-v3（向量嵌入）', type: 'embedding' },
      { id: 'jina-colbert-v2', label: 'jina-colbert-v2（ColBERT 重排序）', type: 'reranking' },
    ],
    notes: ['支持 OpenAI 兼容 API', 'API Key 在 jina.ai 申请', '专注 RAG 增强', '免费额度高'],
  },
  'custom-openai': {
    name: '自定义（OpenAI 兼容）',
    baseUrl: '',
    models: [
      { id: 'gpt-4o', label: 'gpt-4o（OpenAI 多模态旗舰）', type: 'diagnosis' },
      { id: 'gpt-4o-mini', label: 'gpt-4o-mini（OpenAI 轻量版）', type: 'diagnosis' },
    ],
    notes: [
      '兼容 OpenAI API 格式（/v1/chat/completions）',
      'Base URL 需填写为 OpenAI 兼容格式',
      '适用于各类第三方 OpenAI 兼容平台',
      '模型名称请按实际平台填写',
    ],
  },
  'custom-anthropic': {
    name: '自定义（Anthropic 兼容）',
    baseUrl: 'https://api.anthropic.com/v1',
    models: [
      { id: 'claude-3-5-sonnet-20241022', label: 'claude-3-5-sonnet（Anthropic 多模态）', type: 'diagnosis' },
      { id: 'claude-3-opus-20240229', label: 'claude-3-opus（Anthropic 最强推理）', type: 'diagnosis' },
    ],
    notes: [
      '⚠️ 注意：Anthropic 格式与 OpenAI 不同',
      '后端需额外适配 /v1/messages 接口',
      '当前版本可能无法直接调用',
      '模型名称请按实际平台填写',
    ],
  },
};

export default function LLMProvidersPage() {
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [openDialog, setOpenDialog] = useState(false);
  const [editingProvider, setEditingProvider] = useState<LLMProvider | null>(null);
  const [form, setForm] = useState<LLMProviderCreate>(emptyForm);
  const [testResults, setTestResults] = useState<Record<string, { status: string; msg?: string }>>({});
  const [testingId, setTestingId] = useState<string | null>(null);
  const [showGuide, setShowGuide] = useState(false);

  const providerKey = form.provider.toLowerCase().trim();
  const providerGuide = PROVIDER_GUIDES[providerKey];

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listLLMProviders();
      setProviders(data);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleOpenAdd = () => {
    setEditingProvider(null);
    setForm(emptyForm);
    setOpenDialog(true);
  };

  const handleOpenEdit = (p: LLMProvider) => {
    setEditingProvider(p);
    setForm({
      provider: p.provider,
      platform: p.platform,
      name: p.name,
      base_url: p.base_url,
      api_key: '',
      default_model: p.default_model,
      model_type: p.model_type,
      is_active: p.is_active,
      is_default: p.is_default,
    });
    setOpenDialog(true);
  };

  const handleAutoFill = () => {
    if (!providerGuide || editingProvider) return;
    const firstModel = providerGuide.models[0];
    setForm((prev) => ({
      ...prev,
      name: providerGuide.name,
      base_url: providerGuide.baseUrl,
      default_model: firstModel?.id || '',
      model_type: firstModel?.type || 'diagnosis',
    }));
  };

  const handleSave = async () => {
    try {
      if (editingProvider) {
        const update: LLMProviderUpdate = {
          name: form.name,
          base_url: form.base_url,
          default_model: form.default_model,
          model_type: form.model_type,
          platform: form.platform,
          is_active: form.is_active,
          is_default: form.is_default,
        };
        if (form.api_key) update.api_key = form.api_key;
        await updateLLMProvider(editingProvider.id, update);
      } else {
        await createLLMProvider(form);
      }
      setOpenDialog(false);
      load();
    } catch (e: unknown) {
      setError((e as Error).message);
    }
  };

  const handleDelete = async (p: LLMProvider) => {
    if (!window.confirm(`确定删除 ${p.name} （${p.provider}）？`)) return;
    try {
      await deleteLLMProvider(p.id);
      load();
    } catch (e: unknown) {
      setError((e as Error).message);
    }
  };

  const handleTest = async (p: LLMProvider) => {
    const key = `${p.provider}-${p.platform || 'global'}`;
    setTestingId(key);
    try {
      const result = await testLLMProvider(p.id);
      setTestResults((prev) => ({
        ...prev,
        [key]: { status: result.status, msg: result.detail || `模型: ${result.available_models?.join(', ') || 'N/A'}` },
      }));
    } catch (e: unknown) {
      setTestResults((prev) => ({ ...prev, [key]: { status: 'error', msg: (e as Error).message } }));
    } finally {
      setTestingId(null);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 600 }}>LLM 供应商管理</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={handleOpenAdd}>
          新增供应商
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      <Card>
        <CardContent sx={{ p: 0 }}>
          <TableContainer component={Paper} variant="outlined">
            <Table>
              <TableHead>
                <TableRow sx={{ bgcolor: '#F5F7FA' }}>
                  <TableCell>名称</TableCell>
                  <TableCell>提供商</TableCell>
                  <TableCell>平台</TableCell>
                  <TableCell>Base URL</TableCell>
                  <TableCell>默认模型</TableCell>
                  <TableCell>模型类型</TableCell>
                  <TableCell>状态</TableCell>
                  <TableCell>默认</TableCell>
                  <TableCell>API Key</TableCell>
                  <TableCell align="right">操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  <TableRow><TableCell colSpan={10} align="center"><CircularProgress size={24} /></TableCell></TableRow>
                ) : providers.length === 0 ? (
                  <TableRow><TableCell colSpan={10} align="center">暂无数据</TableCell></TableRow>
                ) : (
                  providers.map((p) => {
                    const testKey = `${p.provider}-${p.platform || 'global'}`;
                    const testRes = testResults[testKey];
                    return (
                      <TableRow key={testKey} hover>
                        <TableCell sx={{ fontWeight: 500 }}>{p.name}</TableCell>
                        <TableCell><Chip label={p.provider} size="small" /></TableCell>
                        <TableCell>{p.platform || 'global'}</TableCell>
                        <TableCell sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>{p.base_url}</TableCell>
                        <TableCell>{p.default_model}</TableCell>
                        <TableCell>
                          <Chip
                            label={MODEL_TYPE_OPTIONS.find((o) => o.value === p.model_type)?.label || p.model_type}
                            size="small"
                            variant="outlined"
                            color={p.model_type === 'diagnosis' ? 'primary' : 'default'}
                          />
                        </TableCell>
                        <TableCell>
                          {p.is_active ? (
                            <Chip icon={<CheckCircleIcon />} label="激活" color="success" size="small" />
                          ) : (
                            <Chip icon={<CancelIcon />} label="禁用" color="default" size="small" />
                          )}
                        </TableCell>
                        <TableCell>{p.is_default ? <Chip label="默认" color="primary" size="small" /> : '—'}</TableCell>
                        <TableCell>
                          <Box sx={flexRowGap1}>
                            <code style={{ fontSize: 12 }}>{p.api_key_masked}</code>
                            {testingId === testKey ? (
                              <CircularProgress size={16} />
                            ) : testRes ? (
                              <Tooltip title={testRes.msg || testRes.status}>
                                <Chip
                                  label={testRes.status === 'ok' ? '测试通过' : '测试失败'}
                                  color={testRes.status === 'ok' ? 'success' : 'error'}
                                  size="small"
                                />
                              </Tooltip>
                            ) : (
                              <Tooltip title="测试连通性">
                                <IconButton size="small" onClick={() => handleTest(p)}><TestIcon fontSize="small" /></IconButton>
                              </Tooltip>
                            )}
                          </Box>
                        </TableCell>
                        <TableCell align="right">
                          <IconButton size="small" onClick={() => handleOpenEdit(p)}><EditIcon fontSize="small" /></IconButton>
                          <IconButton size="small" color="error" onClick={() => handleDelete(p)}><DeleteIcon fontSize="small" /></IconButton>
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingProvider ? '编辑供应商' : '新增供应商'}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <Autocomplete
              freeSolo
              options={Object.keys(PROVIDER_GUIDES)}
              value={form.provider}
              onChange={(_, newValue) => setForm({ ...form, provider: newValue || '' })}
              onInputChange={(_, newInput) => setForm({ ...form, provider: newInput })}
              disabled={!!editingProvider}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="提供商标识"
                  required
                  size="small"
                  helperText="输入 moonshot / opencode / zhipu / jina 自动提示，或输入 custom-openai / custom-anthropic 添加自定义兼容平台"
                />
              )}
            />
            {providerGuide && !editingProvider && (
              <Alert
                severity="info"
                icon={false}
                sx={{ py: 0.5 }}
                action={
                  <Button
                    color="primary"
                    size="small"
                    startIcon={<AutoFixHighIcon />}
                    onClick={handleAutoFill}
                    sx={{ whiteSpace: 'nowrap' }}
                  >
                    一键填充
                  </Button>
                }
              >
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  ✅ 检测到 {providerGuide.name} 官方配置
                </Typography>
                <Typography variant="caption" component="div">
                  Base URL: {providerGuide.baseUrl}
                </Typography>
                <Typography variant="caption" component="div">
                  可用模型: {providerGuide.models.length} 个
                </Typography>
              </Alert>
            )}
            <TextField
              label="平台（留空=global）"
              value={form.platform || ''}
              onChange={(e) => setForm({ ...form, platform: e.target.value || null })}
              size="small"
            />
            <TextField
              label="显示名称"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
              size="small"
            />
            <TextField
              label="Base URL"
              value={form.base_url}
              onChange={(e) => setForm({ ...form, base_url: e.target.value })}
              required
              size="small"
            />
            <TextField
              label={editingProvider ? 'API Key (留空则不更新)' : 'API Key'}
              value={form.api_key}
              onChange={(e) => setForm({ ...form, api_key: e.target.value })}
              required={!editingProvider}
              type="password"
              size="small"
            />
            {providerGuide && !editingProvider ? (
              <FormControl size="small" fullWidth>
                <InputLabel id="model-select-label">默认模型</InputLabel>
                <Select
                  labelId="model-select-label"
                  label="默认模型"
                  value={form.default_model}
                  onChange={(e) => {
                    const modelId = e.target.value;
                    const modelInfo = providerGuide.models.find((m) => m.id === modelId);
                    setForm({
                      ...form,
                      default_model: modelId,
                      model_type: modelInfo?.type || form.model_type,
                    });
                  }}
                  required
                >
                  {providerGuide.models.map((m) => (
                    <MenuItem key={m.id} value={m.id}>
                      {m.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            ) : (
              <TextField
                label="默认模型"
                value={form.default_model}
                onChange={(e) => setForm({ ...form, default_model: e.target.value })}
                required
                size="small"
              />
            )}
            <FormControl size="small" fullWidth>
              <InputLabel id="model-type-label">模型类型</InputLabel>
              <Select
                labelId="model-type-label"
                label="模型类型"
                value={form.model_type}
                onChange={(e) => setForm({ ...form, model_type: e.target.value })}
              >
                {MODEL_TYPE_OPTIONS.map((opt) => (
                  <MenuItem key={opt.value} value={opt.value}>{opt.label}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <Box sx={{ display: 'flex', gap: 2 }}>
              <FormControlLabel
                control={<Switch checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />}
                label="激活"
              />
              <FormControlLabel
                control={<Switch checked={form.is_default} onChange={(e) => setForm({ ...form, is_default: e.target.checked })} />}
                label="设为默认"
              />
            </Box>
            <Box>
              <Button size="small" onClick={() => setShowGuide(!showGuide)} sx={{ textTransform: 'none' }}>
                {showGuide ? '隐藏' : '查看'}完整配置指南
              </Button>
              <Collapse in={showGuide}>
                <Alert severity="info" icon={false} sx={{ mt: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600, mb: 1 }}>
                    📖 官方 API 配置参考（OpenAI 兼容格式）
                  </Typography>
                  {Object.entries(PROVIDER_GUIDES).map(([key, guide]) => (
                    <Box key={key} sx={{ mb: 1.5 }}>
                      <Typography variant="caption" sx={{ fontWeight: 600, textTransform: 'capitalize' }}>
                        {key} ({guide.name}):
                      </Typography>
                      <Typography variant="caption" component="div">
                        Base URL: {guide.baseUrl}
                      </Typography>
                      <Typography variant="caption" component="div">
                        模型: {guide.models.map((m) => m.id).join(', ')}
                      </Typography>
                      {guide.notes.map((note, i) => (
                        <Typography key={i} variant="caption" component="div" color="text.secondary">
                          • {note}
                        </Typography>
                      ))}
                    </Box>
                  ))}
                </Alert>
              </Collapse>
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>取消</Button>
          <Button variant="contained" onClick={handleSave}>保存</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}