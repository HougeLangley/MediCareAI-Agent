import { useState, useEffect, useCallback } from 'react';
import {
  Box, Typography, Button, TextField, Dialog, DialogTitle, DialogContent,
  DialogActions, FormControl, InputLabel, Select, MenuItem, Switch,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, Chip, IconButton, Tabs, Tab, Tooltip, CircularProgress,
  Alert, Pagination, FormControlLabel, Grid, Autocomplete,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import RefreshIcon from '@mui/icons-material/Refresh';
import type { DocumentItem, DocumentCreate, DocumentUpdate, DocumentType } from '../../types/admin';
import {
  listDocuments, createDocument, updateDocument, deleteDocument, toggleDocumentActive,
} from '../../api/admin';

const DOC_TYPE_OPTIONS: DocumentType[] = ['platform_guideline', 'drug_reference'];

const DEPARTMENT_OPTIONS = [
  '内科', '外科', '妇产科', '儿科', '骨科', '神经内科', '心血管内科',
  '呼吸内科', '消化内科', '内分泌科', '肿瘤科', '急诊科', 'ICU',
  '皮肤科', '眼科', '耳鼻喉科', '口腔科', '精神科', '康复科', '全科',
];

interface TabState {
  tab: number;
  page: number;
  search: string;
  isActive: boolean | null;
}

export default function KnowledgeBasePage() {
  const [tabs, setTabs] = useState<TabState>({ tab: 0, page: 1, search: '', isActive: null });
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const pageSize = 10;

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingDoc, setEditingDoc] = useState<DocumentItem | null>(null);
  const [form, setForm] = useState<DocumentCreate>({
    title: '', content: '', doc_type: 'platform_guideline',
    source_url: null, department: null, disease_tags: [], drug_name: null,
    language: 'zh', is_featured: false,
  });
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const currentDocType = DOC_TYPE_OPTIONS[tabs.tab];

  const fetchDocs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listDocuments({
        doc_type: currentDocType,
        search: tabs.search || undefined,
        is_active: tabs.isActive ?? undefined,
        skip: (tabs.page - 1) * pageSize,
        limit: pageSize,
      });
      setDocs(res);
      setTotal(res.length);
      if (res.length === pageSize) {
        setTotal(tabs.page * pageSize + 1);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取文档失败');
    } finally {
      setLoading(false);
    }
  }, [tabs.tab, tabs.page, tabs.search, tabs.isActive, currentDocType]);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  const handleTabChange = (_: React.SyntheticEvent, newTab: number) => {
    setTabs({ tab: newTab, page: 1, search: '', isActive: null });
  };

  const openCreate = () => {
    setEditingDoc(null);
    setForm({
      title: '', content: '', doc_type: currentDocType,
      source_url: null, department: null, disease_tags: [], drug_name: null,
      language: 'zh', is_featured: false,
    });
    setFormError(null);
    setDialogOpen(true);
  };

  const openEdit = (doc: DocumentItem) => {
    setEditingDoc(doc);
    setForm({
      title: doc.title,
      content: '', // content not in list view, will fetch if needed
      doc_type: doc.doc_type,
      source_url: doc.source_url || null,
      department: doc.department,
      disease_tags: doc.disease_tags || [],
      drug_name: doc.drug_name,
      language: 'zh',
      is_featured: doc.is_featured,
    });
    setFormError(null);
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!form.title.trim() || !form.content.trim()) {
      setFormError('标题和内容不能为空');
      return;
    }
    setSaving(true);
    setFormError(null);
    try {
      if (editingDoc) {
        const update: DocumentUpdate = {};
        if (form.title) update.title = form.title;
        if (form.content) update.content = form.content;
        if (form.source_url !== undefined) update.source_url = form.source_url;
        if (form.department !== undefined) update.department = form.department;
        if (form.disease_tags !== undefined) update.disease_tags = form.disease_tags;
        if (form.drug_name !== undefined) update.drug_name = form.drug_name;
        if (form.is_featured !== undefined) update.is_featured = form.is_featured;
        await updateDocument(editingDoc.id, update);
      } else {
        await createDocument(form);
      }
      setDialogOpen(false);
      fetchDocs();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : '保存失败');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('确定删除该文档吗？此操作不可撤销。')) return;
    try {
      await deleteDocument(id);
      fetchDocs();
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败');
    }
  };

  const handleToggle = async (doc: DocumentItem) => {
    try {
      await toggleDocumentActive(doc.id);
      setDocs(prev => prev.map(d => d.id === doc.id ? { ...d, is_active: !d.is_active } : d));
    } catch (err) {
      setError(err instanceof Error ? err.message : '切换状态失败');
    }
  };

  const statusChip = (isActive: boolean) => (
    <Chip size="small" label={isActive ? '启用' : '停用'}
      color={isActive ? 'success' : 'default'} variant="outlined" />
  );

  const reviewChip = (status: string) => {
    const map: Record<string, { label: string; color: 'success' | 'warning' | 'error' | 'info' | 'default' }> = {
      approved: { label: '已审核', color: 'success' },
      pending: { label: '待审核', color: 'warning' },
      agent_reviewed: { label: 'AI初审', color: 'info' },
      rejected: { label: '已拒绝', color: 'error' },
      revision_requested: { label: '需修改', color: 'warning' },
    };
    const s = map[status] || { label: status, color: 'default' };
    return <Chip size="small" label={s.label} color={s.color} variant="outlined" />;
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 600 }}>知识库管理</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
          新建文档
        </Button>
      </Box>

      <Paper sx={{ mb: 2 }}>
        <Tabs value={tabs.tab} onChange={handleTabChange}>
          <Tab label="平台指南" />
          <Tab label="核心药物参考" />
        </Tabs>
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={2} sx={{ alignItems: 'center' }}>
          <Grid size={{ xs: 12, md: 4 }}>
            <TextField
              fullWidth size="small" placeholder="搜索标题..."
              value={tabs.search} onChange={e => setTabs(t => ({ ...t, search: e.target.value, page: 1 }))}
            />
          </Grid>
          <Grid size={{ xs: 6, md: 2 }}>
            <FormControl fullWidth size="small">
              <InputLabel>状态</InputLabel>
              <Select value={tabs.isActive === null ? '' : String(tabs.isActive)}
                onChange={e => {
                  const v = e.target.value;
                  setTabs(t => ({ ...t, isActive: v === '' ? null : v === 'true', page: 1 }));
                }}>
                <MenuItem value="">全部</MenuItem>
                <MenuItem value="true">启用</MenuItem>
                <MenuItem value="false">停用</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid size={{ xs: 6, md: 2 }}>
            <Button variant="outlined" startIcon={<RefreshIcon />} onClick={fetchDocs} fullWidth>
              刷新
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ bgcolor: '#F5F7FA' }}>
              <TableCell>标题</TableCell>
              <TableCell>科室/标签</TableCell>
              <TableCell>状态</TableCell>
              <TableCell>审核状态</TableCell>
              <TableCell>分块数</TableCell>
              <TableCell>更新时间</TableCell>
              <TableCell align="right">操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading && docs.length === 0 ? (
              <TableRow><TableCell colSpan={7} align="center"><CircularProgress size={24} /></TableCell></TableRow>
            ) : docs.length === 0 ? (
              <TableRow><TableCell colSpan={7} align="center" sx={{ py: 4, color: 'text.secondary' }}>
                暂无文档
              </TableCell></TableRow>
            ) : docs.map(doc => (
              <TableRow key={doc.id} hover>
                <TableCell>
                  <Typography sx={{ fontWeight: 500 }}>{doc.title}</Typography>
                  {doc.is_featured && <Chip size="small" label="精选" color="primary" sx={{ mt: 0.5 }} />}
                </TableCell>
                <TableCell>
                  {doc.department && <Chip size="small" label={doc.department} sx={{ mr: 0.5 }} />}
                  {doc.disease_tags?.slice(0, 2).map(tag => (
                    <Chip key={tag} size="small" label={tag} variant="outlined" sx={{ mr: 0.5 }} />
                  ))}
                  {doc.drug_name && <Chip size="small" label={doc.drug_name} color="secondary" />}
                </TableCell>
                <TableCell>{statusChip(doc.is_active)}</TableCell>
                <TableCell>{reviewChip(doc.review_status)}</TableCell>
                <TableCell>{doc.chunk_count}</TableCell>
                <TableCell>{new Date(doc.updated_at).toLocaleString('zh-CN')}</TableCell>
                <TableCell align="right">
                  <Tooltip title="编辑"><IconButton size="small" onClick={() => openEdit(doc)}><EditIcon fontSize="small" /></IconButton></Tooltip>
                  <Tooltip title="启停"><Switch size="small" checked={doc.is_active} onChange={() => handleToggle(doc)} /></Tooltip>
                  <Tooltip title="删除"><IconButton size="small" color="error" onClick={() => handleDelete(doc.id)}><DeleteIcon fontSize="small" /></IconButton></Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {total > pageSize && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
          <Pagination count={Math.ceil(total / pageSize)} page={tabs.page}
            onChange={(_, p) => setTabs(t => ({ ...t, page: p }))} />
        </Box>
      )}

      {/* Create / Edit Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{editingDoc ? '编辑文档' : '新建文档'}</DialogTitle>
        <DialogContent>
          {formError && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setFormError(null)}>{formError}</Alert>}
          <Grid container spacing={2} sx={{ mt: 0.5 }}>
            <Grid size={{ xs: 12 }}>
              <TextField fullWidth label="标题" value={form.title}
                onChange={e => setForm(f => ({ ...f, title: e.target.value }))} />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Autocomplete
                freeSolo options={DEPARTMENT_OPTIONS}
                value={form.department || ''}
                onChange={(_, v) => setForm(f => ({ ...f, department: v || null }))}
                renderInput={params => <TextField {...params} label="科室" />}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField fullWidth label="来源 URL" value={form.source_url || ''}
                onChange={e => setForm(f => ({ ...f, source_url: e.target.value || null }))} />
            </Grid>
            <Grid size={{ xs: 12 }}>
              <Autocomplete
                multiple freeSolo options={[]}
                value={form.disease_tags || []}
                onChange={(_, v) => setForm(f => ({ ...f, disease_tags: v }))}
                renderInput={params => <TextField {...params} label="疾病标签" placeholder="输入后回车添加" />}
              />
            </Grid>
            {currentDocType === 'drug_reference' && (
              <Grid size={{ xs: 12, md: 6 }}>
                <TextField fullWidth label="药物名称" value={form.drug_name || ''}
                  onChange={e => setForm(f => ({ ...f, drug_name: e.target.value || null }))} />
              </Grid>
            )}
            <Grid size={{ xs: 12 }}>
              <FormControlLabel
                control={<Switch checked={form.is_featured}
                  onChange={e => setForm(f => ({ ...f, is_featured: e.target.checked }))} />}
                label="设为精选"
              />
            </Grid>
            <Grid size={{ xs: 12 }}>
              <TextField fullWidth multiline rows={8} label="内容（支持 Markdown）"
                value={form.content}
                onChange={e => setForm(f => ({ ...f, content: e.target.value }))}
                placeholder="请输入文档内容，系统将自动分块并建立向量索引..."
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>取消</Button>
          <Button variant="contained" onClick={handleSave} disabled={saving}>
            {saving ? <CircularProgress size={20} /> : '保存'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
