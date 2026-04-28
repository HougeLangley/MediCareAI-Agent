import { useEffect, useState, useCallback } from 'react';
import {
  Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle,
  IconButton, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField,
  Typography, Switch, FormControlLabel, Alert, Paper, CircularProgress, Tooltip,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import SaveIcon from '@mui/icons-material/Save';
import {
  listSettings, createSetting, updateSetting, deleteSetting, batchUpdateSettings,
} from '../../api/admin';
import type { SystemSetting, SystemSettingCreate } from '../../types/admin';

export default function SystemSettingsPage() {
  const [settings, setSettings] = useState<SystemSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [openDialog, setOpenDialog] = useState(false);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [form, setForm] = useState<SystemSettingCreate>({ key: '', value: '', description: '', is_sensitive: false });

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listSettings();
      setSettings(data);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleOpenAdd = () => {
    setEditingKey(null);
    setForm({ key: '', value: '', description: '', is_sensitive: false });
    setOpenDialog(true);
  };

  const handleOpenEdit = (s: SystemSetting) => {
    setEditingKey(s.key);
    setForm({ key: s.key, value: s.value, description: s.description || '', is_sensitive: s.is_sensitive });
    setOpenDialog(true);
  };

  const handleSave = async () => {
    try {
      if (editingKey) {
        await updateSetting(editingKey, { value: form.value, description: form.description || null, is_sensitive: form.is_sensitive });
      } else {
        await createSetting(form);
      }
      setOpenDialog(false);
      load();
    } catch (e: unknown) {
      setError((e as Error).message);
    }
  };

  const handleDelete = async (key: string) => {
    if (!window.confirm(`确定删除设置 "${key}" ？`)) return;
    try {
      await deleteSetting(key);
      load();
    } catch (e: unknown) {
      setError((e as Error).message);
    }
  };

  const handleBatchSave = async () => {
    try {
      const items = settings.map((s) => ({
        key: s.key,
        value: s.value,
        description: s.description,
        is_sensitive: s.is_sensitive,
      }));
      await batchUpdateSettings(items);
      setError('');
      load();
    } catch (e: unknown) {
      setError((e as Error).message);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 600 }}>系统设置管理</Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button variant="outlined" startIcon={<SaveIcon />} onClick={handleBatchSave}>
            批量保存
          </Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={handleOpenAdd}>
            新增设置
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      <Card>
        <CardContent sx={{ p: 0 }}>
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow sx={{ bgcolor: '#F5F7FA' }}>
                  <TableCell sx={{ width: '20%' }}>Key</TableCell>
                  <TableCell sx={{ width: '25%' }}>Value</TableCell>
                  <TableCell sx={{ width: '30%' }}>Description</TableCell>
                  <TableCell>敏感</TableCell>
                  <TableCell align="right">操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  <TableRow><TableCell colSpan={5} align="center"><CircularProgress size={24} /></TableCell></TableRow>
                ) : settings.length === 0 ? (
                  <TableRow><TableCell colSpan={5} align="center">暂无数据</TableCell></TableRow>
                ) : (
                  settings.map((s) => (
                    <TableRow key={s.key} hover>
                      <TableCell sx={{ fontWeight: 500, fontFamily: 'monospace' }}>{s.key}</TableCell>
                      <TableCell>
                        <TextField
                          size="small"
                          value={s.value}
                          onChange={(e) => {
                            const val = e.target.value;
                            setSettings((prev) => prev.map((p) => (p.key === s.key ? { ...p, value: val } : p)));
                          }}
                          fullWidth
                          variant="standard"
                          type={s.is_sensitive ? 'password' : 'text'}
                        />
                      </TableCell>
                      <TableCell>
                        <TextField
                          size="small"
                          value={s.description || ''}
                          onChange={(e) => {
                            const val = e.target.value;
                            setSettings((prev) => prev.map((p) => (p.key === s.key ? { ...p, description: val } : p)));
                          }}
                          fullWidth
                          variant="standard"
                          placeholder="描述..."
                        />
                      </TableCell>
                      <TableCell>
                        {s.is_sensitive ? <Chip label="敏感" color="warning" size="small" /> : '—'}
                      </TableCell>
                      <TableCell align="right">
                        <Tooltip title="编辑">
                          <IconButton size="small" onClick={() => handleOpenEdit(s)}><EditIcon fontSize="small" /></IconButton>
                        </Tooltip>
                        <Tooltip title="删除">
                          <IconButton size="small" color="error" onClick={() => handleDelete(s.key)}><DeleteIcon fontSize="small" /></IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingKey ? '编辑设置' : '新增设置'}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="Key"
              value={form.key}
              onChange={(e) => setForm({ ...form, key: e.target.value })}
              disabled={!!editingKey}
              required
              size="small"
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
            <FormControlLabel
              control={<Switch checked={form.is_sensitive} onChange={(e) => setForm({ ...form, is_sensitive: e.target.checked })} />}
              label="敏感设置（隐藏显示）"
            />
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
