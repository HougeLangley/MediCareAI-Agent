import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Avatar,
  Chip,
  IconButton,
  Skeleton,
  Stack,
} from '@mui/material';
import PendingActionsIcon from '@mui/icons-material/PendingActions';
import MessageIcon from '@mui/icons-material/Message';
import EventBusyIcon from '@mui/icons-material/EventBusy';
import ShareIcon from '@mui/icons-material/Share';
import ArrowForwardIosIcon from '@mui/icons-material/ArrowForwardIos';
import { fetchDashboardStats, listPatients } from '../../api/doctor';
import type { DoctorStats, PatientSummary } from '../../api/doctor';
import { cardStyle } from '../../styles/sxUtils';


const demoStats: DoctorStats = {
  pending_count: 12,
  new_messages: 5,
  followup_due: 3,
  data_shares: 8,
};

const demoPatients: PatientSummary[] = [
  {
    id: 'p-001',
    name: '张伟',
    avatar: '',
    last_activity: '2分钟前提交了血压记录',
    agent_summary: '血压略高，建议继续监测，无明显不适。',
    status: 'followup',
    risk_level: 'medium',
  },
  {
    id: 'p-002',
    name: '李芳',
    avatar: '',
    last_activity: '1小时前询问用药问题',
    agent_summary: '血糖控制良好，服药依从性佳，建议按旧方案继续。',
    status: 'stable',
    risk_level: 'low',
  },
  {
    id: 'p-003',
    name: '王强',
    avatar: '',
    last_activity: '昨天上传了检查报告',
    agent_summary: '心电图异常，建议尽快复查，注意休息。',
    status: 'pending',
    risk_level: 'high',
  },
  {
    id: 'p-004',
    name: '赵敏',
    avatar: '',
    last_activity: '3小时前完成随访',
    agent_summary: '术后恢复良好，伤口愈合正常，无感染迹象。',
    status: 'stable',
    risk_level: 'low',
  },
  {
    id: 'p-005',
    name: '陈宏',
    avatar: '',
    last_activity: '今天早上发来消息',
    agent_summary: '头痛频率增加，建议排除睡眠因素并评估是否需要调整用药。',
    status: 'pending',
    risk_level: 'medium',
  },
];

const statMeta = [
  { key: 'pending_count' as const, label: '待处理', icon: <PendingActionsIcon />, color: '#FB8C00' },
  { key: 'new_messages' as const, label: '新消息', icon: <MessageIcon />, color: '#1E88E5' },
  { key: 'followup_due' as const, label: '随访到期', icon: <EventBusyIcon />, color: '#E53935' },
  { key: 'data_shares' as const, label: '数据分享', icon: <ShareIcon />, color: '#43A047' },
];

const statusMap: Record<string, { label: string; color: 'default' | 'primary' | 'success' | 'warning' | 'error' }> = {
  pending: { label: '待处理', color: 'warning' },
  followup: { label: '随访中', color: 'primary' },
  stable: { label: '稳定', color: 'success' },
};

const riskMap: Record<string, { label: string; color: 'default' | 'primary' | 'success' | 'warning' | 'error' }> = {
  low: { label: '低风险', color: 'success' },
  medium: { label: '中风险', color: 'warning' },
  high: { label: '高风险', color: 'error' },
};

export default function DoctorDashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DoctorStats>(demoStats);
  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [loadingStats, setLoadingStats] = useState(true);
  const [loadingPatients, setLoadingPatients] = useState(true);

  useEffect(() => {
    let mounted = true;
    setLoadingStats(true);
    setLoadingPatients(true);

    fetchDashboardStats()
      .then((data) => {
        if (mounted) setStats(data);
      })
      .catch(() => {
        if (mounted) setStats(demoStats);
      })
      .finally(() => {
        if (mounted) setLoadingStats(false);
      });

    listPatients()
      .then((data) => {
        if (mounted) setPatients(data);
      })
      .catch(() => {
        if (mounted) setPatients([]);
      })
      .finally(() => {
        if (mounted) setLoadingPatients(false);
      });

    return () => {
      mounted = false;
    };
  }, []);

  const handlePatientClick = (id: string) => {
    navigate(`/doctor/cases/${id}`);
  };

  return (
    <Box>
      {/* 顶部统计卡片 */}
      <Typography variant="h5" sx={{ fontWeight: 700, color: 'text.primary', mb: 3 }}>
        工作台
      </Typography>
      <Grid container spacing={2} sx={{ mb: 4 }}>
        {statMeta.map((s) => (
          <Grid size={{ xs: 12, sm: 6, md: 3 }} key={s.key}>
            <Card sx={cardStyle}>
              <CardContent sx={flexRowGap2}>
                <Box
                  sx={{
                    width: 48,
                    height: 48,
                    borderRadius: 2,
                    bgcolor: `${s.color}14`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: s.color,
                  }}
                >
                  {s.icon}
                </Box>
                <Box>
                  <Typography variant="body2" sx={{ color: 'text.secondary', mb: 0.5 }}>
                    {s.label}
                  </Typography>
                  {loadingStats ? (
                    <Skeleton variant="text" width={40} height={32} />
                  ) : (
                    <Typography variant="h4" sx={{ fontWeight: 700, color: 'text.primary' }}>
                      {stats[s.key]}
                    </Typography>
                  )}
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* 患者列表概览 */}
      <Box sx={flexRowBetweenMb2}>
        <Typography variant="h6" sx={{ fontWeight: 700, color: 'text.primary' }}>
          最近患者
        </Typography>
        <IconButton size="small" onClick={() => navigate('/doctor/cases')} sx={{ color: 'primary.main' }}>
          <ArrowForwardIosIcon fontSize="small" />
        </IconButton>
      </Box>

      <Stack spacing={2}>
        {loadingPatients
          ? Array.from({ length: 4 }).map((_, idx) => (
              <Card key={idx} sx={{ borderRadius: 3 }}>
                <CardContent>
                  <Skeleton variant="rectangular" height={80} />
                </CardContent>
              </Card>
            ))
          : patients.map((p) => (
              <Card
                key={p.id}
                sx={{
                  borderRadius: 3,
                  boxShadow: '0 1px 4px rgba(38,50,56,0.08)',
                  cursor: 'pointer',
                  transition: 'box-shadow 0.2s',
                  '&:hover': { boxShadow: '0 4px 12px rgba(38,50,56,0.12)' },
                }}
                onClick={() => handlePatientClick(p.id)}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                    <Avatar sx={{ bgcolor: 'primary.main', fontWeight: 600 }}>
                      {p.name[0]}
                    </Avatar>
                    <Box sx={{ flexGrow: 1 }}>
                      <Box sx={flexRowGap1Mb05}>
                        <Typography variant="subtitle1" sx={{ fontWeight: 600, color: 'text.primary' }}>
                          {p.name}
                        </Typography>
                        <Chip
                          size="small"
                          label={statusMap[p.status]?.label || p.status}
                          color={statusMap[p.status]?.color || 'default'}
                        />
                        {p.risk_level && (
                          <Chip
                            size="small"
                            variant="outlined"
                            label={riskMap[p.risk_level]?.label || p.risk_level}
                            color={riskMap[p.risk_level]?.color || 'default'}
                          />
                        )}
                      </Box>
                      <Typography variant="body2" sx={{ color: 'text.secondary', mb: 0.5 }}>
                        {p.last_activity}
                      </Typography>
                      <Typography variant="body2" sx={{ color: 'text.primary' }}>
                        {p.agent_summary}
                      </Typography>
                    </Box>
                    <IconButton size="small" sx={{ color: 'secondary.light' }}>
                      <ArrowForwardIosIcon fontSize="small" />
                    </IconButton>
                  </Box>
                </CardContent>
              </Card>
            ))}
      </Stack>
    </Box>
  );
}