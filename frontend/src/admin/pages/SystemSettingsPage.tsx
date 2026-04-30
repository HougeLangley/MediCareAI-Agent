import { useEffect, useState, useCallback, startTransition } from 'react';
import {
  Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle,
  FormControl, FormControlLabel, InputLabel, MenuItem, Select, Switch, Tab, Tabs,
  TextField, Typography, Alert, Paper, CircularProgress, Grid,
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import AddIcon from '@mui/icons-material/Add';
import { listSettings, createSetting, batchUpdateSettings } from '../../api/admin';
import type { SystemSetting, SystemSettingCreate } from '../../types/admin';

const CATEGORIES: Record<string, { label: string; color: string }> = {
  general: { label: '⚙️ 通用', color: '#64748B' },
  auth: { label: '🔐 注册认证', color: '#3B82F6' },
  diagnosis: { label: '🏥 医疗诊断', color: '#10B981' },
  agent: { label: '🤖 Agent 配置', color: '#8B5CF6' },
  notification: { label: '📧 通知', color: '#F59E0B' },
  security: { label: '🛡️ 安全', color: '#EF4444' },
};

const CATEGORY_ORDER = ['general', 'auth', 'diagnosis', 'agent', 'notification', 'security'];

function getCategoryLabel(cat: string): string {
  return CATEGORIES[cat]?.label || cat;
}

function getCategoryColor(cat: string): string {
  return CATEGORIES[cat]?.color || '#64748B';
}

function parseBoolean(val: string): boolean {
  return val.toLowerCase() === 'true' || val === '1';
}

function SettingInput({
  setting,
  onChange,
}: {
  setting: SystemSetting;
  onChange: (val: string) => void;
}) {
  const { value_type, value, options, is_sensitive } = setting;

  if (value_type === 'boolean') {
    return (
      <FormControlLabel
        control={
          <Switch
            checked={parseBoolean(value)}
            onChange={(e) => onChange(e.target.checked ? 'true' : 'false')}
          />
        }
        label={parseBoolean(value) ? '启用' : '禁用'}
      />
    );
  }

  if (value_type === 'number') {
    return (
      <TextField
        type="number"
        size="small"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        fullWidth
        variant="outlined"
        sx={{ maxWidth: 200 }}
      />
    );
  }

  if (value_type === 'select' && options) {
    const opts = options.split(',').map((o) => o.trim());
    return (
      <FormControl size="small" fullWidth sx={{ maxWidth: 240 }}>
        <Select value={value} onChange={(e) => onChange(e.target.value)}>
          {opts.map((opt) => (
            <MenuItem key={opt} value={opt}>
              {opt}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    );
  }

  return (
    <TextField
      size="small"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      fullWidth
      variant="outlined"
      type={is_sensitive ? 'password' : 'text'}
    />
  );
}

export default function SystemSettingsPage() {
  const [settings, setSettings] = useState<SystemSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [activeTab, setActiveTab] = useState('general');
  const [openDialog, setOpenDialog] = useState(false);
  const [form, setForm] = useState<SystemSettingCreate>({
    key: '',
    value: '',
    description: '',
    is_sensitive: false,
    category: 'general',
    value_type: 'string',
    options: '',
  });

  // 数据获取：内联到 effect 中
  useEffect(() => {
    let cancelled = false;

    startTransition(() => {
      setLoading(true);
      setError('');
    });

    listSettings()
      .then((data) => {
        if (!cancelled) {
          setSettings(data);
          const cats = Array.from(new Set(data.map((s) => s.category)));
          if (cats.length > 0 && !cats.includes(activeTab)) {
            const first = CATEGORY_ORDER.find((c) => cats.includes(c)) || cats[0];
            setActiveTab(first);
          }
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) setError((e as Error).message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [activeTab]);

  // 手动刷新
  const handleRefresh = useCallback(() => {
    const cancelled = false;

    startTransition(() => {
      setLoading(true);
      setError('');
    });

    listSettings()
      .then((data) => {
        if (!cancelled) {
          setSettings(data);
          const cats = Array.from(new Set(data.map((s) => s.category)));
          if (cats.length > 0 && !cats.includes(activeTab)) {
            const first = CATEGORY_ORDER.find((c) => cats.includes(c)) || cats[0];
            setActiveTab(first);
          }
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) setError((e as Error).message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
  }, [activeTab]);

  const handleChange = (key: string, val: string) => {
    setSettings((prev) => prev.map((s) => (s.key === key ? { ...s, value: val } : s)));
  };

  const handleSaveCategory = async () => {
    const categorySettings = settings.filter((s) => s.category === activeTab);
    if (categorySettings.length === 0) return;

    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await batchUpdateSettings(
        categorySettings.map((s) => ({
          key: s.key,
          value: s.value,
          description: s.description,
          is_sensitive: s.is_sensitive,
          category: s.category,
          value_type: s.value_type,
          options: s.options,
        }))
      );
      setSuccess(`${getCategoryLabel(activeTab)} 设置已保存`);
      setTimeout(() => setSuccess(''), 3000);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveAll = async () => {
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await batchUpdateSettings(
        settings.map((s) => ({
          key: s.key,
          value: s.value,
          description: s.description,
          is_sensitive: s.is_sensitive,
          category: s.category,
          value_type: s.value_type,
          options: s.options,
        }))
      );
      setSuccess('所有设置已保存');
      setTimeout(() => setSuccess(''), 3000);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const handleCreate = async () => {
    try {
      await createSetting({
        ...form,
        options: form.options || null,
      });
      setOpenDialog(false);
      handleRefresh();
    } catch (e: unknown) {
      setError((e as Error).message);
    }
  };

  const grouped = settings.reduce<Record<string, SystemSetting[]>>((acc, s) => {
    acc[s.category] = acc[s.category] || [];
    acc[s.category].push(s);
    return acc;
  }, {});

  const availableCategories = CATEGORY_ORDER.filter((c) => grouped[c]?.length > 0);

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 600 }}>
          系统设置
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<SaveIcon />}
            onClick={handleSaveAll}
            disabled={saving || loading}
          >
            {saving ? <CircularProgress size={16} /> : '保存全部'}
          </Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setOpenDialog(true)}>
            自定义设置
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>
          {success}
        </Alert>
      )}

      {/* Category Tabs */}
      <Paper sx={{ mb: 2 }}>
        <Tabs
          value={activeTab}
          onChange={(_, v) => setActiveTab(v)}
          variant="scrollable"
          scrollButtons="auto"
        >
          {availableCategories.map((cat) => (
            <Tab
              key={cat}
              value={cat}
              label={
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <Chip
                    size="small"
                    sx={{
                      bgcolor: getCategoryColor(cat) + '20',
                      color: getCategoryColor(cat),
                      fontWeight: 600,
                      fontSize: '0.75rem',
                    }}
                    label={grouped[cat]?.length || 0}
                  />
                  {getCategoryLabel(cat)}
                </Box>
              }
            />
          ))}
        </Tabs>
      </Paper>

      {/* Settings Cards */}
      {loading ? (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={handleSaveCategory}
              disabled={saving}
              size="small"
            >
              保存当前分类
            </Button>
          </Box>

          <Grid container spacing={2}>
            {(grouped[activeTab] || []).map((s) => (
              <Grid size={{ xs: 12, md: 6, lg: 4 }} key={s.key}>
                <Card variant="outlined" sx={{ height: '100%' }}>
                  <CardContent sx={{ pb: 1.5 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                      <Typography
                        variant="subtitle2"
                        sx={{
                          fontFamily: 'monospace',
                          fontWeight: 600,
                          color: 'text.primary',
                          wordBreak: 'break-all',
                        }}
                      >
                        {s.key}
                      </Typography>
                      <Chip
                        size="small"
                        label={s.value_type}
                        sx={{
                          fontSize: '0.7rem',
                          height: 20,
                          bgcolor: 'action.hover',
                        }}
                      />
                    </Box>

                    {s.description && (
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5 }}>
                        {s.description}
                      </Typography>
                    )}

                    <SettingInput setting={s} onChange={(val) => handleChange(s.key, val)} />

                    {s.is_sensitive && (
                      <Typography variant="caption" color="warning.main" sx={{ mt: 0.5, display: 'block' }}>
                        🔒 敏感设置
                      </Typography>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </>
      )}

      {/* Add Custom Setting Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>新增自定义设置</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="Key"
              value={form.key}
              onChange={(e) => setForm({ ...form, key: e.target.value })}
              required
              size="small"
              placeholder="my.custom.setting"
            />
            <TextField
              label="Value"
              value={form.value}
              onChange={(e) => setForm({ ...form, value: e.target.value })}
              required
              size="small"
            />
            <TextField
              label="Description"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              size="small"
            />
            <FormControl size="small" fullWidth>
              <InputLabel>分类</InputLabel>
              <Select
                value={form.category}
                label="分类"
                onChange={(e) => setForm({ ...form, category: e.target.value })}
              >
                {Object.entries(CATEGORIES).map(([key, { label }]) => (
                  <MenuItem key={key} value={key}>
                    {label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" fullWidth>
              <InputLabel>值类型</InputLabel>
              <Select
                value={form.value_type}
                label="值类型"
                onChange={(e) => setForm({ ...form, value_type: e.target.value })}
              >
                <MenuItem value="string">文本 (string)</MenuItem>
                <MenuItem value="number">数字 (number)</MenuItem>
                <MenuItem value="boolean">开关 (boolean)</MenuItem>
                <MenuItem value="select">下拉选择 (select)</MenuItem>
              </Select>
            </FormControl>
            {form.value_type === 'select' && (
              <TextField
                label="选项（逗号分隔）"
                value={form.options}
                onChange={(e) => setForm({ ...form, options: e.target.value })}
                size="small"
                placeholder="option1, option2, option3"
              />
            )}
            <FormControlLabel
              control={
                <Switch
                  checked={form.is_sensitive}
                  onChange={(e) => setForm({ ...form, is_sensitive: e.target.checked })}
                />
              }
              label="敏感设置（隐藏显示）"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>取消</Button>
          <Button variant="contained" onClick={handleCreate}>
            创建
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
