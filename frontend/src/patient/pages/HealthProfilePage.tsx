import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  Card,
  CardContent,
  TextField,
  Button,
  Chip,
  IconButton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Grid,
  Stack,
} from '@mui/material';
import ArrowBackIosNewIcon from '@mui/icons-material/ArrowBackIosNew';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import { getProfile, updateProfile } from '../../api/patient';
import type { PatientProfile } from '../../api/patient';
import { flexRowBetweenMb2, pageHeader } from '../../styles/sxUtils';


const warmText = '#5C4033';
const warmPrimary = '#E8956A';
const warmBg = '#FFFBF5';

const fallbackProfile: PatientProfile = {
  id: 'demo-001',
  name: '张三',
  email: 'zhangsan@example.com',
  phone: '13800138000',
  date_of_birth: '1985-06-15',
  gender: '男',
  height: 175,
  weight: 70,
  allergies: ['青霉素', '花生'],
  chronic_diseases: ['高血压', '2型糖尿病'],
  medications: [
    { name: '氨氯地平片', dosage: '5mg', frequency: '每日一次', start_date: '2023-01-10' },
    { name: '二甲双胍片', dosage: '500mg', frequency: '每日两次', start_date: '2023-02-20' },
  ],
};

export default function HealthProfilePage() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<PatientProfile>(fallbackProfile);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(true);

  // 用于编辑时的临时状态
  const [editProfile, setEditProfile] = useState<PatientProfile>(fallbackProfile);
  const [newAllergy, setNewAllergy] = useState('');
  const [newDisease, setNewDisease] = useState('');

  useEffect(() => {
    let mounted = true;
    getProfile()
      .then((data) => {
        if (mounted) {
          const merged = { ...fallbackProfile, ...data };
          setProfile(merged);
          setEditProfile(merged);
          setLoading(false);
        }
      })
      .catch(() => {
        if (mounted) {
          setProfile(fallbackProfile);
          setEditProfile(fallbackProfile);
          setLoading(false);
        }
      });
    return () => {
      mounted = false;
    };
  }, []);

  const handleToggleEdit = () => {
    if (isEditing) {
      // 取消编辑，恢复原始数据
      setEditProfile(profile);
    }
    setIsEditing(!isEditing);
  };

  const handleSave = async () => {
    try {
      const updated = await updateProfile(editProfile);
      const merged = { ...editProfile, ...updated };
      setProfile(merged);
      setEditProfile(merged);
      setIsEditing(false);
    } catch {
      // 如果 API 失败，仍然本地保存演示
      setProfile(editProfile);
      setIsEditing(false);
    }
  };

  const handleChange = (field: keyof PatientProfile, value: string | number) => {
    setEditProfile((prev) => ({ ...prev, [field]: value }));
  };

  const handleAddAllergy = () => {
    const val = newAllergy.trim();
    if (!val) return;
    setEditProfile((prev) => ({
      ...prev,
      allergies: [...(prev.allergies || []), val],
    }));
    setNewAllergy('');
  };

  const handleRemoveAllergy = (index: number) => {
    setEditProfile((prev) => ({
      ...prev,
      allergies: (prev.allergies || []).filter((_, i) => i !== index),
    }));
  };

  const handleAddDisease = () => {
    const val = newDisease.trim();
    if (!val) return;
    setEditProfile((prev) => ({
      ...prev,
      chronic_diseases: [...(prev.chronic_diseases || []), val],
    }));
    setNewDisease('');
  };

  const handleRemoveDisease = (index: number) => {
    setEditProfile((prev) => ({
      ...prev,
      chronic_diseases: (prev.chronic_diseases || []).filter((_, i) => i !== index),
    }));
  };

  const handleMedicationChange = (
    index: number,
    field: 'name' | 'dosage' | 'frequency' | 'start_date',
    value: string
  ) => {
    setEditProfile((prev) => {
      const meds = [...(prev.medications || [])];
      meds[index] = { ...meds[index], [field]: value };
      return { ...prev, medications: meds };
    });
  };

  const handleAddMedication = () => {
    setEditProfile((prev) => ({
      ...prev,
      medications: [...(prev.medications || []), { name: '', dosage: '', frequency: '' }],
    }));
  };

  const handleRemoveMedication = (index: number) => {
    setEditProfile((prev) => ({
      ...prev,
      medications: (prev.medications || []).filter((_, i) => i !== index),
    }));
  };

  const display = isEditing ? editProfile : profile;

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: warmBg, pb: 6 }}>
      <Container maxWidth="md">
        {/* Header */}
        <Box sx={pageHeader}>
          <IconButton onClick={() => navigate('/chat')} sx={{ color: warmText }}>
            <ArrowBackIosNewIcon />
          </IconButton>
          <Typography variant="h5" sx={{ fontWeight: 700, color: warmText, flex: 1 }}>
            健康档案
          </Typography>
          <Button
            variant={isEditing ? 'outlined' : 'contained'}
            startIcon={isEditing ? undefined : <EditIcon />}
            onClick={handleToggleEdit}
            sx={{
              borderRadius: 3,
              textTransform: 'none',
              color: isEditing ? warmPrimary : '#fff',
              borderColor: warmPrimary,
              bgcolor: isEditing ? 'transparent' : warmPrimary,
              '&:hover': {
                bgcolor: isEditing ? 'rgba(232,149,106,0.08)' : '#D4835A',
                borderColor: warmPrimary,
              },
            }}
          >
            {isEditing ? '取消' : '编辑'}
          </Button>
          {isEditing && (
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={handleSave}
              sx={{
                borderRadius: 3,
                textTransform: 'none',
                bgcolor: warmPrimary,
                '&:hover': { bgcolor: '#D4835A' },
              }}
            >
              保存
            </Button>
          )}
        </Box>

        {loading && (
          <Typography sx={{ color: warmText, textAlign: 'center', py: 4 }}>
            加载中...
          </Typography>
        )}

        {/* 基础信息 */}
        <Card sx={{ mb: 2, borderRadius: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ color: warmText, mb: 2, fontWeight: 600 }}>
              基础信息
            </Typography>
            <Grid container spacing={2}>
              {[
                { label: '姓名', field: 'name' as const, type: 'text' },
                { label: '邮箱', field: 'email' as const, type: 'email' },
                { label: '手机', field: 'phone' as const, type: 'tel' },
                { label: '出生日期', field: 'date_of_birth' as const, type: 'date' },
                { label: '性别', field: 'gender' as const, type: 'text' },
                { label: '身高 (cm)', field: 'height' as const, type: 'number' },
                { label: '体重 (kg)', field: 'weight' as const, type: 'number' },
              ].map((item) => (
                <Grid size={{ xs: 12, sm: 6 }} key={item.field}>
                  {isEditing ? (
                    <TextField
                      fullWidth
                      label={item.label}
                      type={item.type}
                      value={display[item.field] ?? ''}
                      onChange={(e) =>
                        handleChange(
                          item.field,
                          item.type === 'number' ? Number(e.target.value) : e.target.value
                        )
                      }
                      InputLabelProps={item.type === 'date' ? { shrink: true } : undefined}
                      sx={{
                        '& .MuiOutlinedInput-root': {
                          borderRadius: 2,
                        },
                      }}
                    />
                  ) : (
                    <Box>
                      <Typography variant="caption" sx={{ color: '#8B7355' }}>
                        {item.label}
                      </Typography>
                      <Typography variant="body1" sx={{ color: warmText, fontWeight: 500 }}>
                        {display[item.field] ?? '—'}
                      </Typography>
                    </Box>
                  )}
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </Card>

        {/* 过敏史 */}
        <Card sx={{ mb: 2, borderRadius: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ color: warmText, mb: 2, fontWeight: 600 }}>
              过敏史
            </Typography>
            <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
              {(display.allergies || []).map((allergy, idx) => (
                <Chip
                  key={`${allergy}-${idx}`}
                  label={allergy}
                  onDelete={isEditing ? () => handleRemoveAllergy(idx) : undefined}
                  sx={{
                    bgcolor: 'rgba(232,149,106,0.12)',
                    color: warmPrimary,
                    fontWeight: 500,
                    '& .MuiChip-deleteIcon': { color: warmPrimary },
                  }}
                />
              ))}
              {!(display.allergies || []).length && !isEditing && (
                <Typography variant="body2" sx={{ color: '#8B7355' }}>
                  暂无记录
                </Typography>
              )}
            </Stack>
            {isEditing && (
              <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                <TextField
                  size="small"
                  placeholder="添加过敏源"
                  value={newAllergy}
                  onChange={(e) => setNewAllergy(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleAddAllergy();
                  }}
                  sx={{ flex: 1, '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
                />
                <Button
                  variant="contained"
                  startIcon={<AddIcon />}
                  onClick={handleAddAllergy}
                  sx={{
                    bgcolor: warmPrimary,
                    '&:hover': { bgcolor: '#D4835A' },
                    borderRadius: 2,
                    textTransform: 'none',
                  }}
                >
                  添加
                </Button>
              </Box>
            )}
          </CardContent>
        </Card>

        {/* 慢性病 */}
        <Card sx={{ mb: 2, borderRadius: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ color: warmText, mb: 2, fontWeight: 600 }}>
              慢性病
            </Typography>
            <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap', gap: 1 }}>
              {(display.chronic_diseases || []).map((disease, idx) => (
                <Chip
                  key={`${disease}-${idx}`}
                  label={disease}
                  onDelete={isEditing ? () => handleRemoveDisease(idx) : undefined}
                  sx={{
                    bgcolor: 'rgba(139,115,85,0.12)',
                    color: '#8B7355',
                    fontWeight: 500,
                    '& .MuiChip-deleteIcon': { color: '#8B7355' },
                  }}
                />
              ))}
              {!(display.chronic_diseases || []).length && !isEditing && (
                <Typography variant="body2" sx={{ color: '#8B7355' }}>
                  暂无记录
                </Typography>
              )}
            </Stack>
            {isEditing && (
              <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                <TextField
                  size="small"
                  placeholder="添加慢性病"
                  value={newDisease}
                  onChange={(e) => setNewDisease(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleAddDisease();
                  }}
                  sx={{ flex: 1, '& .MuiOutlinedInput-root': { borderRadius: 2 } }}
                />
                <Button
                  variant="contained"
                  startIcon={<AddIcon />}
                  onClick={handleAddDisease}
                  sx={{
                    bgcolor: warmPrimary,
                    '&:hover': { bgcolor: '#D4835A' },
                    borderRadius: 2,
                    textTransform: 'none',
                  }}
                >
                  添加
                </Button>
              </Box>
            )}
          </CardContent>
        </Card>

        {/* 用药记录 */}
        <Card sx={{ borderRadius: 3 }}>
          <CardContent>
            <Box sx={flexRowBetweenMb2}>
              <Typography variant="h6" sx={{ color: warmText, fontWeight: 600 }}>
                用药记录
              </Typography>
              {isEditing && (
                <Button
                  variant="outlined"
                  startIcon={<AddIcon />}
                  onClick={handleAddMedication}
                  sx={{
                    borderRadius: 2,
                    textTransform: 'none',
                    color: warmPrimary,
                    borderColor: warmPrimary,
                    '&:hover': { borderColor: '#D4835A', bgcolor: 'rgba(232,149,106,0.06)' },
                  }}
                >
                  添加药物
                </Button>
              )}
            </Box>
            <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ bgcolor: 'rgba(232,149,106,0.08)' }}>
                    <TableCell sx={{ color: warmText, fontWeight: 600 }}>药物名称</TableCell>
                    <TableCell sx={{ color: warmText, fontWeight: 600 }}>剂量</TableCell>
                    <TableCell sx={{ color: warmText, fontWeight: 600 }}>频率</TableCell>
                    {isEditing && <TableCell sx={{ color: warmText, fontWeight: 600 }}>操作</TableCell>}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(display.medications || []).map((med, idx) => (
                    <TableRow key={idx}>
                      <TableCell>
                        {isEditing ? (
                          <TextField
                            size="small"
                            fullWidth
                            value={med.name}
                            onChange={(e) => handleMedicationChange(idx, 'name', e.target.value)}
                            placeholder="药物名称"
                            sx={{ '& .MuiOutlinedInput-root': { borderRadius: 1.5 } }}
                          />
                        ) : (
                          <Typography variant="body2" sx={{ color: warmText }}>
                            {med.name || '—'}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        {isEditing ? (
                          <TextField
                            size="small"
                            fullWidth
                            value={med.dosage}
                            onChange={(e) => handleMedicationChange(idx, 'dosage', e.target.value)}
                            placeholder="剂量"
                            sx={{ '& .MuiOutlinedInput-root': { borderRadius: 1.5 } }}
                          />
                        ) : (
                          <Typography variant="body2" sx={{ color: warmText }}>
                            {med.dosage || '—'}
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        {isEditing ? (
                          <TextField
                            size="small"
                            fullWidth
                            value={med.frequency}
                            onChange={(e) => handleMedicationChange(idx, 'frequency', e.target.value)}
                            placeholder="频率"
                            sx={{ '& .MuiOutlinedInput-root': { borderRadius: 1.5 } }}
                          />
                        ) : (
                          <Typography variant="body2" sx={{ color: warmText }}>
                            {med.frequency || '—'}
                          </Typography>
                        )}
                      </TableCell>
                      {isEditing && (
                        <TableCell>
                          <IconButton
                            size="small"
                            onClick={() => handleRemoveMedication(idx)}
                            sx={{ color: '#E57373' }}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </TableCell>
                      )}
                    </TableRow>
                  ))}
                  {!(display.medications || []).length && (
                    <TableRow>
                      <TableCell colSpan={isEditing ? 4 : 3} align="center">
                        <Typography variant="body2" sx={{ color: '#8B7355', py: 2 }}>
                          暂无用药记录
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      </Container>
    </Box>
  );
}