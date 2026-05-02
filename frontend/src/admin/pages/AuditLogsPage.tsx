import { useState, useEffect, useCallback } from 'react';
import {
  Box, Typography, Button, Paper, Table, TableBody, TableCell, TableContainer,
  TableHead, TableRow, Chip, Dialog, DialogTitle, DialogContent,
  DialogActions, TextField, FormControl, InputLabel, Select, MenuItem,
  CircularProgress, Alert, Pagination, Grid, Card, CardContent,
  IconButton, Tooltip,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import VisibilityIcon from '@mui/icons-material/Visibility';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import type { AuditLogItem, AuditLogStats, AuditActionType, AuditResourceType } from '../../types/admin';
import { listAuditLogs, getAuditLogStats } from '../../api/admin';
import { flexRowBetweenMb2 } from '../../styles/sxUtils';


const ACTION_LABELS: Record<string, string> = {
  LOGIN: '登录',
  LOGOUT: '登出',
  PASSWORD_CHANGE: '修改密码',
  ROLE_SWITCH: '切换角色',
  DOCTOR_VERIFY: '审核通过医生',
  DOCTOR_REJECT: '拒绝医生',
  DOCUMENT_CREATE: '创建文档',
  DOCUMENT_UPDATE: '更新文档',
  DOCUMENT_DELETE: '删除文档',
  DOCUMENT_REVIEW: '审核文档',
  DOCUMENT_TOGGLE: '切换文档状态',
  SETTINGS_CHANGE: '修改系统设置',
  LLM_CONFIG_CREATE: '创建LLM配置',
  LLM_CONFIG_UPDATE: '更新LLM配置',
  LLM_CONFIG_DELETE: '删除LLM配置',
  LLM_CONFIG_TEST: '测试LLM配置',
  USER_CREATE: '创建用户',
  USER_UPDATE: '更新用户',
  USER_DELETE: '删除用户',
  AGENT_SESSION: 'Agent会话',
  TOOL_CALL: '工具调用',
};

const RESOURCE_LABELS: Record<string, string> = {
  USER: '用户',
  DOCTOR: '医生',
  DOCUMENT: '文档',
  SYSTEM_SETTING: '系统设置',
  LLM_PROVIDER: 'LLM供应商',
  AGENT_SESSION: 'Agent会话',
  UNKNOWN: '未知',
};

const ACTION_OPTIONS: AuditActionType[] = [
  'LOGIN', 'LOGOUT', 'PASSWORD_CHANGE', 'ROLE_SWITCH',
  'DOCTOR_VERIFY', 'DOCTOR_REJECT',
  'DOCUMENT_CREATE', 'DOCUMENT_UPDATE', 'DOCUMENT_DELETE', 'DOCUMENT_REVIEW', 'DOCUMENT_TOGGLE',
  'SETTINGS_CHANGE',
  'LLM_CONFIG_CREATE', 'LLM_CONFIG_UPDATE', 'LLM_CONFIG_DELETE', 'LLM_CONFIG_TEST',
  'USER_CREATE', 'USER_UPDATE', 'USER_DELETE',
];

const RESOURCE_OPTIONS: AuditResourceType[] = [
  'USER', 'DOCTOR', 'DOCUMENT', 'SYSTEM_SETTING', 'LLM_PROVIDER', 'AGENT_SESSION', 'UNKNOWN',
];

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  const [stats, setStats] = useState<AuditLogStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);

  const [filters, setFilters] = useState({
    action: '',
    resource_type: '',
    date_from: '',
    date_to: '',
    success: '',
  });

  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listAuditLogs({
        action: filters.action || undefined,
        resource_type: filters.resource_type || undefined,
        date_from: filters.date_from || undefined,
        date_to: filters.date_to || undefined,
        success: filters.success === '' ? undefined : filters.success === 'true',
        skip: (page - 1) * pageSize,
        limit: pageSize,
      });
      setLogs(res);
      setTotal(res.length);
      if (res.length === pageSize) setTotal(page * pageSize + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取审计日志失败');
    } finally {
      setLoading(false);
    }
  }, [page, filters.action, filters.resource_type, filters.date_from, filters.date_to, filters.success]);

  const fetchStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const res = await getAuditLogStats();
      setStats(res);
    } catch {
      // silently ignore stats errors
    } finally {
      setStatsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLogs();
    fetchStats();
  }, [fetchLogs, fetchStats]);

  const openDetail = (log: AuditLogItem) => {
    setSelectedLog(log);
    setDetailOpen(true);
  };

  const actionColor = (action: string): 'success' | 'warning' | 'error' | 'info' | 'default' => {
    if (action.includes('CREATE') || action.includes('VERIFY')) return 'success';
    if (action.includes('DELETE') || action.includes('REJECT')) return 'error';
    if (action.includes('UPDATE') || action.includes('CHANGE')) return 'warning';
    if (action.includes('LOGIN') || action.includes('LOGOUT')) return 'info';
    return 'default';
  };

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={flexRowBetweenMb2}>
        <Typography variant="h5" sx={{ fontWeight: 600 }}>审计日志</Typography>
        <Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => { fetchLogs(); fetchStats(); }}>
          刷新
        </Button>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="text.secondary">今日操作</Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, mt: 1 }}>
                {statsLoading ? <CircularProgress size={24} /> : (stats?.total_today ?? 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="text.secondary">本周操作</Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, mt: 1 }}>
                {statsLoading ? <CircularProgress size={24} /> : (stats?.total_week ?? 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, sm: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="body2" color="text.secondary">今日失败</Typography>
              <Typography variant="h4" sx={{ fontWeight: 700, mt: 1, color: 'error.main' }}>
                {statsLoading ? <CircularProgress size={24} /> : (stats?.failed_today ?? 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={2} sx={{ alignItems: 'center' }}>
          <Grid size={{ xs: 12, sm: 3 }}>
            <FormControl fullWidth size="small">
              <InputLabel>操作类型</InputLabel>
              <Select
                value={filters.action}
                label="操作类型"
                onChange={(e) => setFilters((f) => ({ ...f, action: e.target.value }))}
              >
                <MenuItem value="">全部</MenuItem>
                {ACTION_OPTIONS.map((a) => (
                  <MenuItem key={a} value={a}>{ACTION_LABELS[a] || a}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid size={{ xs: 12, sm: 3 }}>
            <FormControl fullWidth size="small">
              <InputLabel>资源类型</InputLabel>
              <Select
                value={filters.resource_type}
                label="资源类型"
                onChange={(e) => setFilters((f) => ({ ...f, resource_type: e.target.value }))}
              >
                <MenuItem value="">全部</MenuItem>
                {RESOURCE_OPTIONS.map((r) => (
                  <MenuItem key={r} value={r}>{RESOURCE_LABELS[r] || r}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid size={{ xs: 12, sm: 2 }}>
            <TextField
              type="date"
              label="起始日期"
              size="small"
              fullWidth
              value={filters.date_from}
              onChange={(e) => setFilters((f) => ({ ...f, date_from: e.target.value }))}
              slotProps={{ inputLabel: { shrink: true } }}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 2 }}>
            <TextField
              type="date"
              label="结束日期"
              size="small"
              fullWidth
              value={filters.date_to}
              onChange={(e) => setFilters((f) => ({ ...f, date_to: e.target.value }))}
              slotProps={{ inputLabel: { shrink: true } }}
            />
          </Grid>
          <Grid size={{ xs: 12, sm: 2 }}>
            <FormControl fullWidth size="small">
              <InputLabel>状态</InputLabel>
              <Select
                value={filters.success}
                label="状态"
                onChange={(e) => setFilters((f) => ({ ...f, success: e.target.value }))}
              >
                <MenuItem value="">全部</MenuItem>
                <MenuItem value="true">成功</MenuItem>
                <MenuItem value="false">失败</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Table */}
      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell width={160}>时间</TableCell>
              <TableCell width={120}>操作人</TableCell>
              <TableCell width={140}>操作</TableCell>
              <TableCell width={100}>资源</TableCell>
              <TableCell>资源ID</TableCell>
              <TableCell width={80}>状态</TableCell>
              <TableCell width={60}>详情</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {logs.map((log) => (
              <TableRow key={log.id} hover>
                <TableCell>{formatDate(log.created_at)}</TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>{log.user_email || '系统'}</Typography>
                  {log.user_role && (
                    <Typography variant="caption" color="text.secondary">{log.user_role}</Typography>
                  )}
                </TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    label={ACTION_LABELS[log.action] || log.action}
                    color={actionColor(log.action)}
                    variant="outlined"
                  />
                </TableCell>
                <TableCell>{RESOURCE_LABELS[log.resource_type] || log.resource_type}</TableCell>
                <TableCell>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                    {log.resource_id ? log.resource_id.slice(0, 8) + '...' : '-'}
                  </Typography>
                </TableCell>
                <TableCell>
                  {log.success ? (
                    <CheckCircleIcon fontSize="small" color="success" />
                  ) : (
                    <ErrorIcon fontSize="small" color="error" />
                  )}
                </TableCell>
                <TableCell>
                  <Tooltip title="查看详情">
                    <IconButton size="small" onClick={() => openDetail(log)}>
                      <VisibilityIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
            {logs.length === 0 && !loading && (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">暂无审计日志</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
          <CircularProgress />
        </Box>
      )}

      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
        <Pagination
          count={Math.ceil(total / pageSize)}
          page={page}
          onChange={(_, p) => setPage(p)}
          color="primary"
        />
      </Box>

      {/* Detail Dialog */}
      <Dialog open={detailOpen} onClose={() => setDetailOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>审计详情</DialogTitle>
        <DialogContent>
          {selectedLog && (
            <Box sx={{ mt: 1 }}>
              <Grid container spacing={2}>
                <Grid size={{ xs: 6 }}>
                  <Typography variant="caption" color="text.secondary">操作</Typography>
                  <Typography variant="body1">{ACTION_LABELS[selectedLog.action] || selectedLog.action}</Typography>
                </Grid>
                <Grid size={{ xs: 6 }}>
                  <Typography variant="caption" color="text.secondary">时间</Typography>
                  <Typography variant="body1">{new Date(selectedLog.created_at).toLocaleString('zh-CN')}</Typography>
                </Grid>
                <Grid size={{ xs: 6 }}>
                  <Typography variant="caption" color="text.secondary">操作人</Typography>
                  <Typography variant="body1">{selectedLog.user_email || '系统'} ({selectedLog.user_role || 'unknown'})</Typography>
                </Grid>
                <Grid size={{ xs: 6 }}>
                  <Typography variant="caption" color="text.secondary">资源</Typography>
                  <Typography variant="body1">{RESOURCE_LABELS[selectedLog.resource_type] || selectedLog.resource_type}</Typography>
                </Grid>
                <Grid size={{ xs: 12 }}>
                  <Typography variant="caption" color="text.secondary">资源ID</Typography>
                  <Typography variant="body1" sx={{ fontFamily: 'monospace' }}>{selectedLog.resource_id || '-'}</Typography>
                </Grid>
                <Grid size={{ xs: 12 }}>
                  <Typography variant="caption" color="text.secondary">IP 地址</Typography>
                  <Typography variant="body1">{selectedLog.ip_address || '-'}</Typography>
                </Grid>
                <Grid size={{ xs: 12 }}>
                  <Typography variant="caption" color="text.secondary">User Agent</Typography>
                  <Typography variant="body2" sx={{ wordBreak: 'break-all' }}>{selectedLog.user_agent || '-'}</Typography>
                </Grid>
                <Grid size={{ xs: 12 }}>
                  <Typography variant="caption" color="text.secondary">详情</Typography>
                  <Box component="pre" sx={{ bgcolor: 'grey.50', p: 1.5, borderRadius: 1, fontSize: '0.8rem', overflow: 'auto' }}>
                    {JSON.stringify(selectedLog.details, null, 2)}
                  </Box>
                </Grid>
                {selectedLog.error_message && (
                  <Grid size={{ xs: 12 }}>
                    <Typography variant="caption" color="error">错误信息</Typography>
                    <Typography variant="body2" color="error">{selectedLog.error_message}</Typography>
                  </Grid>
                )}
              </Grid>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailOpen(false)}>关闭</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}