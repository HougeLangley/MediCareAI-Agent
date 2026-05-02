import { useEffect, useState, useCallback, startTransition } from 'react';
import {
  Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle,
  FormControl, FormControlLabel, IconButton, InputLabel, MenuItem, Select, Switch,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TextField,
  Typography, Alert, Paper, CircularProgress, Tooltip, Grid, Tabs, Tab, Divider,
} from '@mui/material';
import EditIcon from '@mui/icons-material/Edit';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import SearchIcon from '@mui/icons-material/Search';
import { listDoctors, verifyDoctor, updateUser } from '../../api/admin';
import type { UserItem, UserAdminUpdate } from '../../types/admin';
import { flexRowBetweenMb2 } from '../../styles/sxUtils';


const STATUS_TABS = [
  { value: 'all', label: '全部' },
  { value: 'pending', label: '待审核' },
  { value: 'verified', label: '已认证' },
  { value: 'rejected', label: '未通过' },
];

function getStatusChip(status: string, isVerified: boolean) {
  if (status === 'pending') {
    return <Chip size="small" label="待审核" color="warning" sx={{ fontWeight: 500 }} />;
  }
  if (status === 'inactive') {
    return <Chip size="small" label="未通过" color="error" sx={{ fontWeight: 500 }} />;
  }
  if (isVerified) {
    return <Chip size="small" label="已认证" color="success" sx={{ fontWeight: 500 }} />;
  }
  return <Chip size="small" label="正常" color="default" sx={{ fontWeight: 500 }} />;
}

export default function DoctorVerificationPage() {
  const [doctors, setDoctors] = useState<UserItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Tabs: all | pending | verified | rejected
  const [tab, setTab] = useState('all');
  const [search, setSearch] = useState('');

  // Verify dialog
  const [verifyOpen, setVerifyOpen] = useState(false);
  const [verifyUser, setVerifyUser] = useState<UserItem | null>(null);
  const [verifyAction, setVerifyAction] = useState<'approve' | 'reject'>('approve');
  const [verifyReason, setVerifyReason] = useState('');
  const [verifying, setVerifying] = useState(false);

  // Edit dialog
  const [editOpen, setEditOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<UserItem | null>(null);
  const [form, setForm] = useState<UserAdminUpdate>({});
  const [saving, setSaving] = useState(false);

  // 数据获取：内联到 effect 中，避免间接 setState
  useEffect(() => {
    let cancelled = false;

    startTransition(() => {
      setLoading(true);
      setError('');
    });

    const params: Record<string, unknown> = { role: 'doctor', limit: 100 };
    if (search) params.search = search;

    if (tab === 'pending') {
      params.status = 'pending';
    } else if (tab === 'verified') {
      params.is_verified = true;
    } else if (tab === 'rejected') {
      params.status = 'inactive';
      params.is_verified = false;
    }

    listDoctors(params)
      .then((data) => {
        if (!cancelled) setDoctors(data);
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
  }, [tab, search]);

  // 手动刷新
  const handleRefresh = useCallback(() => {
    const cancelled = false;

    startTransition(() => {
      setLoading(true);
      setError('');
    });

    const params: Record<string, unknown> = { role: 'doctor', limit: 100 };
    if (search) params.search = search;

    if (tab === 'pending') {
      params.status = 'pending';
    } else if (tab === 'verified') {
      params.is_verified = true;
    } else if (tab === 'rejected') {
      params.status = 'inactive';
      params.is_verified = false;
    }

    listDoctors(params)
      .then((data) => {
        if (!cancelled) setDoctors(data);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError((e as Error).message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
  }, [tab, search]);

  const handleOpenVerify = (u: UserItem, action: 'approve' | 'reject') => {
    setVerifyUser(u);
    setVerifyAction(action);
    setVerifyReason('');
    setVerifyOpen(true);
  };

  const handleVerify = async () => {
    if (!verifyUser) return;
    setVerifying(true);
    setError('');
    setSuccess('');
    try {
      await verifyDoctor(verifyUser.id, {
        action: verifyAction,
        reason: verifyReason || undefined,
      });
      setSuccess(verifyAction === 'approve' ? '医生认证已通过' : '医生认证已拒绝');
      setVerifyOpen(false);
      handleRefresh();
      setTimeout(() => setSuccess(''), 3000);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setVerifying(false);
    }
  };

  const handleOpenEdit = (u: UserItem) => {
    setEditingUser(u);
    setForm({
      full_name: u.full_name,
      status: u.status,
      is_verified: u.is_verified,
      license_number: u.license_number,
      hospital: u.hospital,
      department: u.department,
      title: u.title,
    });
    setEditOpen(true);
  };

  const handleSave = async () => {
    if (!editingUser) return;
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await updateUser(editingUser.id, form);
      setSuccess('医生信息已更新');
      setEditOpen(false);
      handleRefresh();
      setTimeout(() => setSuccess(''), 3000);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const counts = {
    all: doctors.length,
    pending: doctors.filter((d) => d.status === 'pending').length,
    verified: doctors.filter((d) => d.is_verified).length,
    rejected: doctors.filter((d) => d.status === 'inactive' && !d.is_verified).length,
  };

  return (
    <Box>
      <Box sx={flexRowBetweenMb2}>
        <Typography variant="h5" sx={{ fontWeight: 600 }}>
          医生认证
        </Typography>
        <Typography variant="body2" color="text.secondary">
          共 {doctors.length} 位医生
        </Typography>
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

      {/* Search + Tabs */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={2} sx={{ alignItems: 'center', mb: 2 }}>
          <Grid size={{ xs: 12, md: 6 }}>
            <TextField
              size="small"
              fullWidth
              placeholder="搜索邮箱或姓名..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              slotProps={{
                input: {
                  endAdornment: <SearchIcon fontSize="small" color="action" />,
                },
              }}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 3 }}>
            <Button variant="outlined" fullWidth onClick={handleRefresh} disabled={loading}>
              {loading ? <CircularProgress size={16} /> : '刷新'}
            </Button>
          </Grid>
        </Grid>

        <Tabs value={tab} onChange={(_, v) => setTab(v)} textColor="primary" indicatorColor="primary">
          {STATUS_TABS.map((t) => (
            <Tab
              key={t.value}
              value={t.value}
              label={`${t.label} (${counts[t.value as keyof typeof counts]})`}
            />
          ))}
        </Tabs>
      </Paper>

      {/* Table */}
      <Card>
        <CardContent sx={{ p: 0 }}>
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow sx={{ bgcolor: '#F5F7FA' }}>
                  <TableCell>姓名 / 邮箱</TableCell>
                  <TableCell>执业证号</TableCell>
                  <TableCell>医院 / 科室</TableCell>
                  <TableCell>认证状态</TableCell>
                  <TableCell>创建时间</TableCell>
                  <TableCell align="right">操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <CircularProgress size={24} sx={{ my: 2 }} />
                    </TableCell>
                  </TableRow>
                ) : doctors.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                      暂无医生数据
                    </TableCell>
                  </TableRow>
                ) : (
                  doctors.map((d) => (
                    <TableRow key={d.id} hover>
                      <TableCell>
                        <Box>
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>
                            {d.full_name}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {d.email}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {d.license_number || <span style={{ color: '#94a3b8' }}>—</span>}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box>
                          {d.hospital && (
                            <Typography variant="body2">{d.hospital}</Typography>
                          )}
                          {d.department && (
                            <Typography variant="caption" color="text.secondary">
                              {d.department} {d.title && `· ${d.title}`}
                            </Typography>
                          )}
                          {!d.hospital && !d.department && (
                            <Typography variant="caption" color="text.secondary">—</Typography>
                          )}
                        </Box>
                      </TableCell>
                      <TableCell>{getStatusChip(d.status, d.is_verified)}</TableCell>
                      <TableCell>
                        <Typography variant="caption" color="text.secondary">
                          {new Date(d.created_at).toLocaleDateString('zh-CN')}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 0.5 }}>
                          {d.status === 'pending' && (
                            <>
                              <Tooltip title="通过认证">
                                <IconButton
                                  size="small"
                                  color="success"
                                  onClick={() => handleOpenVerify(d, 'approve')}
                                >
                                  <CheckCircleIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="拒绝认证">
                                <IconButton
                                  size="small"
                                  color="error"
                                  onClick={() => handleOpenVerify(d, 'reject')}
                                >
                                  <CancelIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </>
                          )}
                          <Tooltip title="编辑">
                            <IconButton size="small" onClick={() => handleOpenEdit(d)}>
                              <EditIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Verify Dialog */}
      <Dialog open={verifyOpen} onClose={() => setVerifyOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {verifyAction === 'approve' ? '通过医生认证' : '拒绝医生认证'}
          {verifyUser && ` — ${verifyUser.full_name}`}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <Typography variant="body2" color="text.secondary">
              医生: {verifyUser?.full_name} ({verifyUser?.email})
            </Typography>
            <Typography variant="body2" color="text.secondary">
              执业证号: {verifyUser?.license_number || '未填写'}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              医院: {verifyUser?.hospital || '未填写'} / 科室: {verifyUser?.department || '未填写'}
            </Typography>
            <Divider />
            <TextField
              label={verifyAction === 'reject' ? '拒绝原因（可选）' : '备注（可选）'}
              value={verifyReason}
              onChange={(e) => setVerifyReason(e.target.value)}
              size="small"
              fullWidth
              multiline
              rows={2}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setVerifyOpen(false)}>取消</Button>
          <Button
            variant="contained"
            color={verifyAction === 'approve' ? 'success' : 'error'}
            onClick={handleVerify}
            disabled={verifying}
          >
            {verifying ? <CircularProgress size={16} /> : verifyAction === 'approve' ? '通过' : '拒绝'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={editOpen} onClose={() => setEditOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>编辑医生信息: {editingUser?.full_name}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="姓名"
              value={form.full_name || ''}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              size="small"
              fullWidth
            />
            <FormControl size="small" fullWidth>
              <InputLabel>状态</InputLabel>
              <Select
                value={form.status || ''}
                label="状态"
                onChange={(e) => setForm({ ...form, status: e.target.value })}
              >
                <MenuItem value="active">正常</MenuItem>
                <MenuItem value="inactive">禁用</MenuItem>
                <MenuItem value="pending">待审核</MenuItem>
              </Select>
            </FormControl>
            <FormControlLabel
              control={
                <Switch
                  checked={form.is_verified || false}
                  onChange={(e) => setForm({ ...form, is_verified: e.target.checked })}
                />
              }
              label={form.is_verified ? '已认证' : '未认证'}
            />
            <TextField
              label="执业证号"
              value={form.license_number || ''}
              onChange={(e) => setForm({ ...form, license_number: e.target.value || null })}
              size="small"
              fullWidth
            />
            <TextField
              label="所在医院"
              value={form.hospital || ''}
              onChange={(e) => setForm({ ...form, hospital: e.target.value || null })}
              size="small"
              fullWidth
            />
            <TextField
              label="科室"
              value={form.department || ''}
              onChange={(e) => setForm({ ...form, department: e.target.value || null })}
              size="small"
              fullWidth
            />
            <TextField
              label="职称"
              value={form.title || ''}
              onChange={(e) => setForm({ ...form, title: e.target.value || null })}
              size="small"
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditOpen(false)}>取消</Button>
          <Button variant="contained" onClick={handleSave} disabled={saving}>
            {saving ? <CircularProgress size={16} /> : '保存'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}