import { useEffect, useState, useCallback } from 'react';
import {
  Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle,
  IconButton, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField,
  Typography, Switch, FormControlLabel, Tooltip, CircularProgress, Alert, Paper,
  Select, MenuItem, FormControl, InputLabel, Collapse,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Block';
import TestIcon from '@mui/icons-material/NetworkCheck';
import {
  listLLMProviders, createLLMProvider, updateLLMProvider, deleteLLMProvider, testLLMProvider,
} from '../../api/admin';
import type { LLMProvider, LLMProviderCreate, LLMProviderUpdate } from '../../types/admin';

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
const PROVIDER_GUIDES: Record<string, { baseUrl: string; models: string; note?: string }> = {
  moonshot: {
    baseUrl: 'https://api.moonshot.cn/v1',
    models: 'moonshot-v1-8k, moonshot-v1-32k, moonshot-v1-128k',
    note: 'Kimi 模型支持文本+图片多模态理解',
  },
  deepseek: {
    baseUrl: 'https://api.deepseek.com/v1',
    models: 'deepseek-chat, deepseek-reasoner',
    note: '推理能力强，适合复杂诊断场景',
  },
  zhipu: {
    baseUrl: 'https://open.bigmodel.cn/api/paas/v4/',
    models: 'glm-4, glm-4v (多模态), glm-4-flash',
    note: 'GLM-4V 支持图片理解，Flash 版本成本低',
  },
  siliconflow: {
    baseUrl: 'https://api.siliconflow.cn/v1',
    models: 'BAAI/bge-m3 (embedding), deepseek-ai/DeepSeek-V2.5, Qwen/Qwen2.5-72B-Instruct, THUDM/glm-4-9b-chat',
    note: '矽基流动聚合了国内外优秀开源模型，可作为备选方案',
  },
  jina: {
    baseUrl: 'https://api.jina.ai/v1',
    models: 'jina-reranker-v2-base-multilingual (reranking)',
    note: '重排序专用，支持多语言，提升 RAG 精度',
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

  const providerGuide = PROVIDER_GUIDES[form.provider.toLowerCase()];

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
        await updateLLMProvider(editingProvider.provider, update, editingProvider.platform);
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
      await deleteLLMProvider(p.provider, p.platform);
      load();
    } catch (e: unknown) {
      setError((e as Error).message);
    }
  };

  const handleTest = async (p: LLMProvider) => {
    const key = `${p.provider}-${p.platform || 'global'}`;
    setTestingId(key);
    try {
      const result = await testLLMProvider(p.provider, p.platform);
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
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
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
            <TextField
              label="提供商标识"
              value={form.provider}
              onChange={(e) => setForm({ ...form, provider: e.target.value })}
              disabled={!!editingProvider}
              required
              size="small"
              helperText="如：moonshot, deepseek, zhipu, siliconflow, jina"
            />
            {providerGuide && !editingProvider && (
              <Alert severity="info" icon={false} sx={{ py: 0.5 }}>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  ⚠️ 提示：检测到 {form.provider} 官方配置
                </Typography>
                <Typography variant="caption" component="div">
                  Base URL: {providerGuide.baseUrl}
                </Typography>
                <Typography variant="caption" component="div">
                  推荐模型: {providerGuide.models}
                </Typography>
                {providerGuide.note && (
                  <Typography variant="caption" component="div" color="warning.main">
                    {providerGuide.note}
                  </Typography>
                )}
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
            <TextField
              label="默认模型"
              value={form.default_model}
              onChange={(e) => setForm({ ...form, default_model: e.target.value })}
              required
              size="small"
            />
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
                    <Box key={key} sx={{ mb: 1 }}>
                      <Typography variant="caption" sx={{ fontWeight: 600, textTransform: 'capitalize' }}>
                        {key}:
                      </Typography>
                      <Typography variant="caption" component="div">
                        Base URL: {guide.baseUrl}
                      </Typography>
                      <Typography variant="caption" component="div">
                        模型: {guide.models}
                      </Typography>
                      {guide.note && (
                        <Typography variant="caption" component="div" color="warning.main">
                          注意: {guide.note}
                        </Typography>
                      )}
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
