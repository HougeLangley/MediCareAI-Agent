import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Button, Card, CardContent, TextField, Typography, Alert, CircularProgress,
} from '@mui/material';
import { changePassword } from '../../api/admin';

export default function ChangePasswordPage() {
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (newPassword.length < 8) {
      setError('密码至少 8 位');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('两次密码不一致');
      return;
    }

    setLoading(true);
    try {
      await changePassword({ new_password: newPassword });
      setSuccess(true);
      setTimeout(() => navigate('/admin'), 1500);
    } catch (e: unknown) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        bgcolor: '#F5F7FA',
        p: 2,
      }}
    >
      <Card sx={{ maxWidth: 400, width: '100%' }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h5" sx={{ mb: 1, fontWeight: 700, color: '#1565C0', textAlign: 'center' }}>
            修改默认密码
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3, textAlign: 'center' }}>
            首次登录，请修改默认密码以确保安全
          </Typography>

          {success && (
            <Alert severity="success" sx={{ mb: 2 }}>
              密码修改成功，正在跳转...
            </Alert>
          )}
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="新密码"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              size="small"
              helperText="至少 8 位"
            />
            <TextField
              label="确认新密码"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              size="small"
            />
            <Button
              type="submit"
              variant="contained"
              size="large"
              disabled={loading || success}
              sx={{ mt: 1, bgcolor: '#1565C0' }}
            >
              {loading ? <CircularProgress size={20} color="inherit" /> : '确认修改'}
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
