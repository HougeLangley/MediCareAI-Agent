import { useState, useEffect, useCallback } from 'react';
import {
  Box, Paper, Typography, Button, TextField, Dialog, DialogTitle, DialogContent,
  DialogActions, FormControl, InputLabel, Select, MenuItem, Chip, IconButton,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow, TablePagination,
  Tooltip, Badge, Alert,
} from '@mui/material';
import NotificationsIcon from '@mui/icons-material/Notifications';
import SendIcon from '@mui/icons-material/Send';
import CampaignIcon from '@mui/icons-material/Campaign';
import DeleteIcon from '@mui/icons-material/Delete';
import MarkEmailReadIcon from '@mui/icons-material/MarkEmailRead';
import VisibilityIcon from '@mui/icons-material/Visibility';
import type { NotificationItem, NotificationDetail, NotificationType, NotificationPriority, NotificationUnreadCount } from '../../types/admin';
import {
  listNotifications, getUnreadCount, getNotification, createNotification,
  broadcastNotification, markNotificationRead, deleteNotification,
} from '../../api/admin';

const TYPE_COLORS: Record<string, string> = {
  system: '#9C27B0',
  announcement: '#F59E0B',
  direct: '#1565C0',
  reminder: '#10B981',
};

const PRIORITY_COLORS: Record<string, string> = {
  high: '#EF4444',
  medium: '#F59E0B',
  low: '#6B7280',
};

export default function NotificationsPage() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unread, setUnread] = useState<NotificationUnreadCount | null>(null);

  const [filterType, setFilterType] = useState<string>('');
  const [filterPriority, setFilterPriority] = useState<string>('');
  const [filterRead, setFilterRead] = useState<string>('');
  const [search, setSearch] = useState('');

  const [detailOpen, setDetailOpen] = useState(false);
  const [detail, setDetail] = useState<NotificationDetail | null>(null);

  const [sendOpen, setSendOpen] = useState(false);
  const [sendMode, setSendMode] = useState<'direct' | 'broadcast'>('direct');
  const [sendForm, setSendForm] = useState({
    subject: '', content: '', recipient_id: '', priority: 'medium' as NotificationPriority,
    notification_type: 'direct' as NotificationType, action_url: '',
  });
  const [sendLoading, setSendLoading] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: any = { page: page + 1, page_size: pageSize };
      if (filterType) params.notification_type = filterType;
      if (filterPriority) params.priority = filterPriority;
      if (filterRead !== '') params.is_read = filterRead === 'read';
      if (search) params.search = search;
      const res = await listNotifications(params);
      setItems(res.items);
      setTotal(res.total);
      setUnread({
        total: res.unread_count,
        system: 0, announcement: 0, direct: 0, reminder: 0,
      });
    } catch (e: any) {
      setError(e.message || 'Failed to load notifications');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, filterType, filterPriority, filterRead, search]);

  const fetchUnread = useCallback(async () => {
    try {
      const res = await getUnreadCount();
      setUnread(res);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);
  useEffect(() => { fetchUnread(); }, []);

  const handleView = async (id: string) => {
    try {
      const res = await getNotification(id);
      setDetail(res);
      setDetailOpen(true);
      if (!res.is_read) {
        await markNotificationRead(id, true);
        fetchData();
        fetchUnread();
      }
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定删除这条消息？')) return;
    try {
      await deleteNotification(id);
      fetchData();
      fetchUnread();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleMarkRead = async (id: string) => {
    try {
      await markNotificationRead(id, true);
      fetchData();
      fetchUnread();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleSend = async () => {
    setSendLoading(true);
    try {
      if (sendMode === 'broadcast') {
        await broadcastNotification({
          subject: sendForm.subject,
          content: sendForm.content,
          priority: sendForm.priority,
          action_url: sendForm.action_url || undefined,
        });
      } else {
        await createNotification({
          subject: sendForm.subject,
          content: sendForm.content,
          recipient_id: sendForm.recipient_id || null,
          priority: sendForm.priority,
          notification_type: sendForm.notification_type,
          action_url: sendForm.action_url || null,
        });
      }
      setSendOpen(false);
      setSendForm({ subject: '', content: '', recipient_id: '', priority: 'medium', notification_type: 'direct', action_url: '' });
      fetchData();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSendLoading(false);
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 700 }}>
          <NotificationsIcon sx={{ mr: 1, verticalAlign: 'middle', color: '#1565C0' }} />
          站内信管理
          {unread && unread.total > 0 && (
            <Badge badgeContent={unread.total} color="error" sx={{ ml: 2 }}>
              <NotificationsIcon color="action" />
            </Badge>
          )}
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button variant="outlined" onClick={fetchData} disabled={loading}>
            刷新
          </Button>
          <Button variant="contained" startIcon={<SendIcon />} onClick={() => { setSendMode('direct'); setSendOpen(true); }}>
            发消息
          </Button>
          <Button variant="contained" color="secondary" startIcon={<CampaignIcon />} onClick={() => { setSendMode('broadcast'); setSendOpen(true); }}>
            广播
          </Button>
        </Box>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      {/* Filters */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <TextField label="搜索" size="small" value={search} onChange={(e) => setSearch(e.target.value)} sx={{ minWidth: 200 }} />
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>类型</InputLabel>
            <Select value={filterType} label="类型" onChange={(e) => setFilterType(e.target.value)}>
              <MenuItem value="">全部</MenuItem>
              <MenuItem value="system">系统</MenuItem>
              <MenuItem value="announcement">公告</MenuItem>
              <MenuItem value="direct">私信</MenuItem>
              <MenuItem value="reminder">提醒</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>优先级</InputLabel>
            <Select value={filterPriority} label="优先级" onChange={(e) => setFilterPriority(e.target.value)}>
              <MenuItem value="">全部</MenuItem>
              <MenuItem value="high">高</MenuItem>
              <MenuItem value="medium">中</MenuItem>
              <MenuItem value="low">低</MenuItem>
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>状态</InputLabel>
            <Select value={filterRead} label="状态" onChange={(e) => setFilterRead(e.target.value)}>
              <MenuItem value="">全部</MenuItem>
              <MenuItem value="read">已读</MenuItem>
              <MenuItem value="unread">未读</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </Paper>

      {/* Table */}
      <Paper>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: '#F3F4F6' }}>
                <TableCell>类型</TableCell>
                <TableCell>优先级</TableCell>
                <TableCell>标题</TableCell>
                <TableCell>发送者</TableCell>
                <TableCell>状态</TableCell>
                <TableCell>时间</TableCell>
                <TableCell align="right">操作</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map((item) => (
                <TableRow key={item.id} sx={!item.is_read ? { bgcolor: '#F0F9FF' } : {}}>
                  <TableCell>
                    <Chip label={item.notification_type} size="small" sx={{ color: '#fff', bgcolor: TYPE_COLORS[item.notification_type] || '#888' }} />
                  </TableCell>
                  <TableCell>
                    <Chip label={item.priority} size="small" sx={{ color: '#fff', bgcolor: PRIORITY_COLORS[item.priority] || '#888' }} />
                  </TableCell>
                  <TableCell>
                    {item.broadcast && <CampaignIcon fontSize="small" sx={{ mr: 0.5, color: '#F59E0B', verticalAlign: 'middle' }} />}
                    <strong>{item.subject}</strong>
                    <Typography variant="caption" sx={{ display: 'block' }} color="text.secondary">{item.content_preview}</Typography>
                  </TableCell>
                  <TableCell>{item.sender?.full_name || '系统'}</TableCell>
                  <TableCell>{item.is_read ? <Chip label="已读" size="small" color="success" /> : <Chip label="未读" size="small" color="warning" />}</TableCell>
                  <TableCell>{new Date(item.created_at).toLocaleString()}</TableCell>
                  <TableCell align="right">
                    <Tooltip title="查看"><IconButton size="small" onClick={() => handleView(item.id)}><VisibilityIcon fontSize="small" /></IconButton></Tooltip>
                    {!item.is_read && <Tooltip title="标为已读"><IconButton size="small" onClick={() => handleMarkRead(item.id)}><MarkEmailReadIcon fontSize="small" /></IconButton></Tooltip>}
                    <Tooltip title="删除"><IconButton size="small" color="error" onClick={() => handleDelete(item.id)}><DeleteIcon fontSize="small" /></IconButton></Tooltip>
                  </TableCell>
                </TableRow>
              ))}
              {items.length === 0 && !loading && (
                <TableRow><TableCell colSpan={7} align="center" sx={{ py: 4, color: '#9CA3AF' }}>暂无消息</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          component="div"
          count={total}
          page={page}
          onPageChange={(_, p) => setPage(p)}
          rowsPerPage={pageSize}
          onRowsPerPageChange={(e) => { setPageSize(parseInt(e.target.value, 10)); setPage(0); }}
          rowsPerPageOptions={[10, 20, 50]}
          labelRowsPerPage="每页"
        />
      </Paper>

      {/* Detail Dialog */}
      <Dialog open={detailOpen} onClose={() => setDetailOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>消息详情</DialogTitle>
        <DialogContent>
          {detail && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Chip label={detail.notification_type} size="small" sx={{ color: '#fff', bgcolor: TYPE_COLORS[detail.notification_type] || '#888' }} />
                <Chip label={detail.priority} size="small" sx={{ color: '#fff', bgcolor: PRIORITY_COLORS[detail.priority] || '#888' }} />
                {detail.broadcast && <Chip label="广播" size="small" color="secondary" />}
              </Box>
              <Typography variant="h6">{detail.subject}</Typography>
              <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', bgcolor: '#F9FAFB', p: 2, borderRadius: 1 }}>{detail.content}</Typography>
              {detail.action_url && <Typography variant="body2"><a href={detail.action_url} target="_blank" rel="noreferrer">{detail.action_url}</a></Typography>}
              <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                <Typography variant="caption">发送者: {detail.sender?.full_name || '系统'} ({detail.sender?.role || 'system'})</Typography>
                <Typography variant="caption">{new Date(detail.created_at).toLocaleString()}</Typography>
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailOpen(false)}>关闭</Button>
        </DialogActions>
      </Dialog>

      {/* Send Dialog */}
      <Dialog open={sendOpen} onClose={() => setSendOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{sendMode === 'broadcast' ? '发送系统广播' : '发送站内信'}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField label="标题" fullWidth value={sendForm.subject} onChange={(e) => setSendForm({ ...sendForm, subject: e.target.value })} />
            <TextField label="内容" fullWidth multiline rows={4} value={sendForm.content} onChange={(e) => setSendForm({ ...sendForm, content: e.target.value })} />
            {sendMode === 'direct' && (
              <>
                <TextField label="接收者用户ID (留空则发送给所有管理员)" fullWidth value={sendForm.recipient_id} onChange={(e) => setSendForm({ ...sendForm, recipient_id: e.target.value })} />
                <FormControl fullWidth>
                  <InputLabel>消息类型</InputLabel>
                  <Select value={sendForm.notification_type} label="消息类型" onChange={(e) => setSendForm({ ...sendForm, notification_type: e.target.value as NotificationType })}>
                    <MenuItem value="direct">私信</MenuItem>
                    <MenuItem value="system">系统通知</MenuItem>
                    <MenuItem value="reminder">提醒</MenuItem>
                  </Select>
                </FormControl>
              </>
            )}
            <FormControl fullWidth>
              <InputLabel>优先级</InputLabel>
              <Select value={sendForm.priority} label="优先级" onChange={(e) => setSendForm({ ...sendForm, priority: e.target.value as NotificationPriority })}>
                <MenuItem value="low">低</MenuItem>
                <MenuItem value="medium">中</MenuItem>
                <MenuItem value="high">高</MenuItem>
              </Select>
            </FormControl>
            <TextField label="跳转链接 (可选)" fullWidth value={sendForm.action_url} onChange={(e) => setSendForm({ ...sendForm, action_url: e.target.value })} />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSendOpen(false)}>取消</Button>
          <Button variant="contained" onClick={handleSend} disabled={sendLoading || !sendForm.subject || !sendForm.content}>
            {sendLoading ? '发送中...' : '发送'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
