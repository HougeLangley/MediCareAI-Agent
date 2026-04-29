import { useEffect, useState } from 'react';
import { Box, Card, CardContent, Grid, Typography, CircularProgress } from '@mui/material';
import PeopleIcon from '@mui/icons-material/People';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import SettingsIcon from '@mui/icons-material/Settings';
import { fetchDashboardStats } from '../../api/admin';
import type { DashboardStats } from '../../types/admin';

function StatCard({ title, value, icon, color }: { title: string; value: number | string; icon: React.ReactNode; color: string }) {
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box>
            <Typography color="text.secondary" variant="body2" sx={{ mb: 1 }}>
              {title}
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 700, color }}>
              {value}
            </Typography>
          </Box>
          <Box sx={{ color, opacity: 0.3 }}>
            {icon}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchDashboardStats()
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography color="error">加载失败: {error}</Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 3, fontWeight: 600 }}>
        仪表盘
      </Typography>

      <Grid container spacing={3}>
        <Grid size={{ xs: 12, sm: 6, md: 4 }}>
          <StatCard
            title="总用户数"
            value={stats?.users.total ?? 0}
            icon={<PeopleIcon sx={{ fontSize: 48 }} />}
            color="#1565C0"
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4 }}>
          <StatCard
            title="LLM 供应商"
            value={stats?.llm_providers.total ?? 0}
            icon={<SmartToyIcon sx={{ fontSize: 48 }} />}
            color="#2E7D32"
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4 }}>
          <StatCard
            title="系统设置项"
            value={stats?.system_settings ?? 0}
            icon={<SettingsIcon sx={{ fontSize: 48 }} />}
            color="#ED6C02"
          />
        </Grid>
      </Grid>

      {stats?.users.by_role && Object.keys(stats.users.by_role).length > 0 && (
        <Card sx={{ mt: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
              用户角色分布
            </Typography>
            <Grid container spacing={2}>
              {Object.entries(stats.users.by_role).map(([role, count]) => {
                const roleNames: Record<string, string> = {
                  patient: '患者',
                  doctor: '医生',
                  admin: '管理员',
                };
                return (
                  <Grid size={{ xs: 6, sm: 4, md: 3 }} key={role}>
                    <Box sx={{ textAlign: 'center', p: 2, bgcolor: '#F5F7FA', borderRadius: 1 }}>
                      <Typography variant="h5" sx={{ fontWeight: 700, color: '#1565C0' }}>
                        {count}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {roleNames[role] || role}
                      </Typography>
                    </Box>
                  </Grid>
                );
              })}
            </Grid>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
