import { useState, useEffect, useCallback } from 'react';
import {
  Box, Paper, Typography, Button, TextField, Dialog, DialogTitle, DialogContent,
  DialogActions, FormControl, InputLabel, Select, MenuItem, Chip, IconButton,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TablePagination,
  Tabs, Tab, Tooltip, Alert, Grid, Card, CardContent,
  Link as MuiLink,
} from '@mui/material';
import EmailIcon from '@mui/icons-material/Email';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import SettingsIcon from '@mui/icons-material/Settings';
import TemplateIcon from '@mui/icons-material/Description';
import HistoryIcon from '@mui/icons-material/History';
import PresetIcon from '@mui/icons-material/Store';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import SendIcon from '@mui/icons-material/Send';
import type {
  EmailConfig, EmailTemplate, EmailLog, EmailProviderPreset,
  SmtpSecurity,
} from '../../types/admin';
import { flexRowGap1Mb1 } from '../../styles/sxUtils';
import { PageHeader } from '../../components/layout/PageHeader';
import {
  listEmailConfigs, createEmailConfig, updateEmailConfig, deleteEmailConfig,
  testEmailConfig, setDefaultEmailConfig,
  listEmailTemplates, createEmailTemplate, updateEmailTemplate, deleteEmailTemplate,
  listEmailLogs, getEmailProviderPresets,
} from '../../api/admin';

const SECURITY_LABELS: Record<string, string> = {
  starttls: 'STARTTLS',
  ssl: 'SSL/TLS',
  none: '无加密',
};

const STATUS_COLORS: Record<string, 'success' | 'error' | 'warning' | 'default'> = {
  success: 'success',
  failed: 'error',
  untested: 'warning',
  pending: 'default',
};

export default function EmailManagementPage() {
  const [tab, setTab] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [configs, setConfigs] = useState<EmailConfig[]>([]);
  const [configsLoading, setConfigsLoading] = useState(false);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState<EmailConfig | null>(null);
  const [configForm, setConfigForm] = useState({
    smtp_host: '', smtp_port: 587, smtp_user: '', smtp_password: '',
    smtp_from_email: '', smtp_from_name: 'MediCareAI-Agent',
    smtp_security: 'starttls' as SmtpSecurity, description: '', is_default: false,
  });
  const [testEmail, setTestEmail] = useState('');
  const [testDialogOpen, setTestDialogOpen] = useState(false);
  const [testingConfigId, setTestingConfigId] = useState<string | null>(null);

  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [templateDialogOpen, setTemplateDialogOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<EmailTemplate | null>(null);
  const [templateForm, setTemplateForm] = useState({
    name: '', description: '', subject: '', html_body: '', text_body: '',
    variables: '', is_active: true,
  });

  const [logs, setLogs] = useState<EmailLog[]>([]);
  const [logsTotal, setLogsTotal] = useState(0);
  const [logsPage, setLogsPage] = useState(0);
  const [logsPageSize, setLogsPageSize] = useState(20);
  const [logsLoading, setLogsLoading] = useState(false);

  const [presets, setPresets] = useState<EmailProviderPreset[]>([]);

  const showError = (msg: string) => { setError(msg); setTimeout(() => setError(null), 5000); };
  const showSuccess = (msg: string) => { setSuccess(msg); setTimeout(() => setSuccess(null), 5000); };

  const fetchConfigs = useCallback(async () => {
    setConfigsLoading(true);
    try {
      const res = await listEmailConfigs();
      setConfigs(res.items);
    } catch (e: any) { showError(e.message); }
    finally { setConfigsLoading(false); }
  }, []);

  const fetchTemplates = useCallback(async () => {
    setTemplatesLoading(true);
    try {
      const res = await listEmailTemplates();
      setTemplates(res.items);
    } catch (e: any) { showError(e.message); }
    finally { setTemplatesLoading(false); }
  }, []);

  const fetchLogs = useCallback(async () => {
    setLogsLoading(true);
    try {
      const res = await listEmailLogs({ page: logsPage + 1, page_size: logsPageSize });
      setLogs(res.items);
      setLogsTotal(res.total);
    } catch (e: any) { showError(e.message); }
    finally { setLogsLoading(false); }
  }, [logsPage, logsPageSize]);

  const fetchPresets = useCallback(async () => {
    try {
      const res = await getEmailProviderPresets();
      setPresets(res.providers);
    } catch (e: any) { showError(e.message); }
  }, []);

  useEffect(() => { fetchConfigs(); }, [fetchConfigs]);
  useEffect(() => { if (tab === 1) fetchTemplates(); }, [tab, fetchTemplates]);
  useEffect(() => { if (tab === 2) fetchLogs(); }, [tab, fetchLogs]);
  useEffect(() => { if (tab === 3) fetchPresets(); }, [tab, fetchPresets]);

  const openConfigDialog = (cfg?: EmailConfig) => {
    if (cfg) {
      setEditingConfig(cfg);
      setConfigForm({
        smtp_host: cfg.smtp_host, smtp_port: cfg.smtp_port, smtp_user: cfg.smtp_user,
        smtp_password: '', smtp_from_email: cfg.smtp_from_email,
        smtp_from_name: cfg.smtp_from_name, smtp_security: cfg.smtp_security,
        description: cfg.description || '', is_default: cfg.is_default,
      });
    } else {
      setEditingConfig(null);
      setConfigForm({
        smtp_host: '', smtp_port: 587, smtp_user: '', smtp_password: '',
        smtp_from_email: '', smtp_from_name: 'MediCareAI-Agent',
        smtp_security: 'starttls', description: '', is_default: false,
      });
    }
    setConfigDialogOpen(true);
  };

  const handleSaveConfig = async () => {
    try {
      if (editingConfig) {
        const updateData: any = { ...configForm };
        if (!updateData.smtp_password) delete updateData.smtp_password;
        await updateEmailConfig(editingConfig.id, updateData);
        showSuccess('配置已更新');
      } else {
        await createEmailConfig(configForm);
        showSuccess('配置已创建');
      }
      setConfigDialogOpen(false);
      fetchConfigs();
    } catch (e: any) { showError(e.message); }
  };

  const handleDeleteConfig = async (id: string) => {
    if (!window.confirm('确定删除该配置？')) return;
    try { await deleteEmailConfig(id); fetchConfigs(); showSuccess('已删除'); }
    catch (e: any) { showError(e.message); }
  };

  const handleTestConfig = async () => {
    if (!testingConfigId || !testEmail) return;
    try {
      const res = await testEmailConfig(testingConfigId, testEmail);
      if (res.success) showSuccess(res.message);
      else showError(res.message);
      setTestDialogOpen(false);
      fetchConfigs();
    } catch (e: any) { showError(e.message); }
  };

  const handleSetDefault = async (id: string) => {
    try { await setDefaultEmailConfig(id); fetchConfigs(); showSuccess('已设为默认'); }
    catch (e: any) { showError(e.message); }
  };

  const openTemplateDialog = (tpl?: EmailTemplate) => {
    if (tpl) {
      setEditingTemplate(tpl);
      setTemplateForm({
        name: tpl.name, description: tpl.description || '', subject: tpl.subject,
        html_body: tpl.html_body, text_body: tpl.text_body || '',
        variables: tpl.variables || '', is_active: tpl.is_active,
      });
    } else {
      setEditingTemplate(null);
      setTemplateForm({ name: '', description: '', subject: '', html_body: '', text_body: '', variables: '', is_active: true });
    }
    setTemplateDialogOpen(true);
  };

  const handleSaveTemplate = async () => {
    try {
      if (editingTemplate) {
        await updateEmailTemplate(editingTemplate.id, templateForm);
        showSuccess('模板已更新');
      } else {
        await createEmailTemplate(templateForm);
        showSuccess('模板已创建');
      }
      setTemplateDialogOpen(false);
      fetchTemplates();
    } catch (e: any) { showError(e.message); }
  };

  const handleDeleteTemplate = async (id: string) => {
    if (!window.confirm('确定删除该模板？')) return;
    try { await deleteEmailTemplate(id); fetchTemplates(); showSuccess('已删除'); }
    catch (e: any) { showError(e.message); }
  };

  return (
    <Box>
      <PageHeader
        title="邮件管理"
        icon={<EmailIcon sx={{ verticalAlign: 'middle', color: '#1565C0' }} />}
      />

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>{success}</Alert>}

      <Paper sx={{ mb: 2 }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)}>
          <Tab icon={<SettingsIcon fontSize="small" />} label="SMTP 配置" />
          <Tab icon={<TemplateIcon fontSize="small" />} label="邮件模板" />
          <Tab icon={<HistoryIcon fontSize="small" />} label="发送历史" />
          <Tab icon={<PresetIcon fontSize="small" />} label="预设提供商" />
        </Tabs>
      </Paper>

      {/* === SMTP Configs Tab === */}
      {tab === 0 && (
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => openConfigDialog()}>
              新增配置
            </Button>
          </Box>
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow sx={{ bgcolor: '#F3F4F6' }}>
                  <TableCell>默认</TableCell>
                  <TableCell>SMTP 服务器</TableCell>
                  <TableCell>用户名</TableCell>
                  <TableCell>发件人</TableCell>
                  <TableCell>加密</TableCell>
                  <TableCell>测试状态</TableCell>
                  <TableCell align="right">操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {configs.map((cfg) => (
                  <TableRow key={cfg.id}>
                    <TableCell>{cfg.is_default ? <CheckCircleIcon color="success" /> : '—'}</TableCell>
                    <TableCell>{cfg.smtp_host}:{cfg.smtp_port}</TableCell>
                    <TableCell>{cfg.smtp_user}</TableCell>
                    <TableCell>{cfg.smtp_from_name} &lt;{cfg.smtp_from_email}&gt;</TableCell>
                    <TableCell>{SECURITY_LABELS[cfg.smtp_security]}</TableCell>
                    <TableCell><Chip label={cfg.test_status} color={STATUS_COLORS[cfg.test_status] || 'default'} size="small" /></TableCell>
                    <TableCell align="right">
                      {!cfg.is_default && <Tooltip title="设为默认"><IconButton size="small" onClick={() => handleSetDefault(cfg.id)}><SettingsIcon fontSize="small" /></IconButton></Tooltip>}
                      <Tooltip title="测试"><IconButton size="small" onClick={() => { setTestingConfigId(cfg.id); setTestDialogOpen(true); }}><SendIcon fontSize="small" /></IconButton></Tooltip>
                      <Tooltip title="编辑"><IconButton size="small" onClick={() => openConfigDialog(cfg)}><EditIcon fontSize="small" /></IconButton></Tooltip>
                      <Tooltip title="删除"><IconButton size="small" color="error" onClick={() => handleDeleteConfig(cfg.id)}><DeleteIcon fontSize="small" /></IconButton></Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
                {configs.length === 0 && !configsLoading && (
                  <TableRow><TableCell colSpan={7} align="center" sx={{ py: 4, color: '#9CA3AF' }}>暂无配置，请添加 SMTP 配置</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {/* === Templates Tab === */}
      {tab === 1 && (
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => openTemplateDialog()}>
              新增模板
            </Button>
          </Box>
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow sx={{ bgcolor: '#F3F4F6' }}>
                  <TableCell>名称</TableCell>
                  <TableCell>主题</TableCell>
                  <TableCell>变量</TableCell>
                  <TableCell>状态</TableCell>
                  <TableCell align="right">操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {templates.map((tpl) => (
                  <TableRow key={tpl.id}>
                    <TableCell>
                      <strong>{tpl.name}</strong>
                      <Typography variant="caption" sx={{ display: 'block' }} color="text.secondary">{tpl.description}</Typography>
                    </TableCell>
                    <TableCell>{tpl.subject}</TableCell>
                    <TableCell><Typography variant="body2" sx={{ fontFamily: 'monospace' }}>{tpl.variables || '—'}</Typography></TableCell>
                    <TableCell><Chip label={tpl.is_active ? '启用' : '禁用'} color={tpl.is_active ? 'success' : 'default'} size="small" /></TableCell>
                    <TableCell align="right">
                      <Tooltip title="编辑"><IconButton size="small" onClick={() => openTemplateDialog(tpl)}><EditIcon fontSize="small" /></IconButton></Tooltip>
                      <Tooltip title="删除"><IconButton size="small" color="error" onClick={() => handleDeleteTemplate(tpl.id)}><DeleteIcon fontSize="small" /></IconButton></Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
                {templates.length === 0 && !templatesLoading && (
                  <TableRow><TableCell colSpan={5} align="center" sx={{ py: 4, color: '#9CA3AF' }}>暂无模板</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {/* === Logs Tab === */}
      {tab === 2 && (
        <Box>
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow sx={{ bgcolor: '#F3F4F6' }}>
                  <TableCell>状态</TableCell>
                  <TableCell>收件人</TableCell>
                  <TableCell>主题</TableCell>
                  <TableCell>重试</TableCell>
                  <TableCell>错误信息</TableCell>
                  <TableCell>时间</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell>
                      {log.status === 'sent' ? <Chip icon={<CheckCircleIcon />} label="已发送" color="success" size="small" /> :
                       log.status === 'failed' ? <Chip icon={<ErrorIcon />} label="失败" color="error" size="small" /> :
                       <Chip label={log.status} size="small" />}
                    </TableCell>
                    <TableCell>{log.recipient_email}</TableCell>
                    <TableCell>{log.subject}</TableCell>
                    <TableCell>{log.retry_count}</TableCell>
                    <TableCell><Typography variant="caption" color="error">{log.error_message || '—'}</Typography></TableCell>
                    <TableCell>{new Date(log.created_at).toLocaleString()}</TableCell>
                  </TableRow>
                ))}
                {logs.length === 0 && !logsLoading && (
                  <TableRow><TableCell colSpan={6} align="center" sx={{ py: 4, color: '#9CA3AF' }}>暂无发送记录</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
          <TablePagination
            component="div" count={logsTotal} page={logsPage}
            onPageChange={(_, p) => setLogsPage(p)}
            rowsPerPage={logsPageSize}
            onRowsPerPageChange={(e) => { setLogsPageSize(parseInt(e.target.value, 10)); setLogsPage(0); }}
            rowsPerPageOptions={[10, 20, 50]} labelRowsPerPage="每页"
          />
        </Box>
      )}

      {/* === Presets Tab === */}
      {tab === 3 && (
        <Box>
          <Grid container spacing={2}>
            {presets.map((preset) => (
              <Grid size={{ xs: 12, md: 6, lg: 4 }} key={preset.id}>
                <Card variant="outlined">
                  <CardContent>
                    <Box sx={flexRowGap1Mb1}>
                      <Typography variant="h6" sx={{ fontSize: '1.1rem', fontWeight: 600 }}>{preset.icon} {preset.name}</Typography>
                      <Chip label={preset.category_label} size="small" variant="outlined" />
                    </Box>
                    <Typography variant="body2" sx={{ color: 'text.secondary', mb: 1 }}>{preset.description}</Typography>
                    <Typography variant="body2" sx={{ fontFamily: 'monospace', bgcolor: '#F3F4F6', p: 1, borderRadius: 1 }}>
                      {preset.smtp.host}:{preset.smtp.port} ({SECURITY_LABELS[preset.smtp.security]})
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
                      {preset.help_text}
                    </Typography>
                    {preset.help_link && (
                      <MuiLink href={preset.help_link} target="_blank" rel="noreferrer" variant="caption">
                        查看帮助 →
                      </MuiLink>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}

      {/* Config Dialog */}
      <Dialog open={configDialogOpen} onClose={() => setConfigDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingConfig ? '编辑 SMTP 配置' : '新增 SMTP 配置'}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField label="SMTP 服务器地址" fullWidth value={configForm.smtp_host} onChange={(e) => setConfigForm({ ...configForm, smtp_host: e.target.value })} />
            <TextField label="端口" type="number" fullWidth value={configForm.smtp_port} onChange={(e) => setConfigForm({ ...configForm, smtp_port: parseInt(e.target.value) || 0 })} />
            <TextField label="用户名" fullWidth value={configForm.smtp_user} onChange={(e) => setConfigForm({ ...configForm, smtp_user: e.target.value })} />
            <TextField label={editingConfig ? '密码 (留空则不更新)' : '密码'} type="password" fullWidth value={configForm.smtp_password} onChange={(e) => setConfigForm({ ...configForm, smtp_password: e.target.value })} />
            <TextField label="发件人邮箱" fullWidth value={configForm.smtp_from_email} onChange={(e) => setConfigForm({ ...configForm, smtp_from_email: e.target.value })} />
            <TextField label="发件人名称" fullWidth value={configForm.smtp_from_name} onChange={(e) => setConfigForm({ ...configForm, smtp_from_name: e.target.value })} />
            <FormControl fullWidth>
              <InputLabel>加密方式</InputLabel>
              <Select value={configForm.smtp_security} label="加密方式" onChange={(e) => setConfigForm({ ...configForm, smtp_security: e.target.value as SmtpSecurity })}>
                <MenuItem value="starttls">STARTTLS</MenuItem>
                <MenuItem value="ssl">SSL/TLS</MenuItem>
                <MenuItem value="none">无加密</MenuItem>
              </Select>
            </FormControl>
            <TextField label="描述 (可选)" fullWidth value={configForm.description} onChange={(e) => setConfigForm({ ...configForm, description: e.target.value })} />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfigDialogOpen(false)}>取消</Button>
          <Button variant="contained" onClick={handleSaveConfig} disabled={!configForm.smtp_host || !configForm.smtp_user || (!editingConfig && !configForm.smtp_password)}>
            保存
          </Button>
        </DialogActions>
      </Dialog>

      {/* Test Dialog */}
      <Dialog open={testDialogOpen} onClose={() => setTestDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>测试邮件配置</DialogTitle>
        <DialogContent>
          <TextField label="接收测试邮件的邮箱" fullWidth value={testEmail} onChange={(e) => setTestEmail(e.target.value)} sx={{ mt: 1 }} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTestDialogOpen(false)}>取消</Button>
          <Button variant="contained" onClick={handleTestConfig} disabled={!testEmail}>发送测试邮件</Button>
        </DialogActions>
      </Dialog>

      {/* Template Dialog */}
      <Dialog open={templateDialogOpen} onClose={() => setTemplateDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{editingTemplate ? '编辑邮件模板' : '新增邮件模板'}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField label="模板名称" fullWidth value={templateForm.name} onChange={(e) => setTemplateForm({ ...templateForm, name: e.target.value })} />
            <TextField label="描述" fullWidth value={templateForm.description} onChange={(e) => setTemplateForm({ ...templateForm, description: e.target.value })} />
            <TextField label="邮件主题" fullWidth value={templateForm.subject} onChange={(e) => setTemplateForm({ ...templateForm, subject: e.target.value })} />
            <TextField label="HTML 内容" fullWidth multiline rows={8} value={templateForm.html_body} onChange={(e) => setTemplateForm({ ...templateForm, html_body: e.target.value })} />
            <TextField label="纯文本内容 (可选)" fullWidth multiline rows={4} value={templateForm.text_body} onChange={(e) => setTemplateForm({ ...templateForm, text_body: e.target.value })} />
            <TextField label="变量 (逗号分隔，如: user_name, reset_url)" fullWidth value={templateForm.variables} onChange={(e) => setTemplateForm({ ...templateForm, variables: e.target.value })} />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTemplateDialogOpen(false)}>取消</Button>
          <Button variant="contained" onClick={handleSaveTemplate} disabled={!templateForm.name || !templateForm.subject || !templateForm.html_body}>
            保存
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}