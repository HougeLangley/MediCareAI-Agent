import React, { useState } from 'react';
import {
  Box,
  Button,
  TextField,
  Typography,
  Paper,
  IconButton,
  InputAdornment,
  Snackbar,
  Alert,
  Link,
  CircularProgress,
  useTheme,
} from '@mui/material';
import { Visibility, VisibilityOff, Email, Lock } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { login, getMe } from '../api/auth';

const LoginPage: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'error' | 'success';
  }>({
    open: false,
    message: '',
    severity: 'error',
  });

  const handleTogglePassword = () => setShowPassword((prev) => !prev);

  const handleCloseSnackbar = () =>
    setSnackbar((prev) => ({ ...prev, open: false }));

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      setSnackbar({
        open: true,
        message: '请输入邮箱和密码',
        severity: 'error',
      });
      return;
    }
    setLoading(true);
    try {
      await login({ email: email.trim(), password, role: 'patient' });
      const user = await getMe();
      const role = user.role;
      const routes: Record<string, string> = {
        patient: '/chat',
        doctor: '/doctor',
        admin: '/admin',
      };
      navigate(routes[role] || '/chat', { replace: true });
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : '登录失败，请稍后重试';
      setSnackbar({ open: true, message, severity: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        display: 'flex',
        minHeight: '100vh',
        bgcolor: theme.palette.background.default,
      }}
    >
      {/* 左侧品牌展示 */}
      <Box
        sx={{
          flex: 1,
          display: { xs: 'none', md: 'flex' },
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          bgcolor: '#FFF5EB',
          p: 6,
          color: theme.palette.text.primary,
        }}
      >
        <Typography
          variant="h2"
          sx={{
            fontWeight: 700,
            mb: 2,
            color: theme.palette.primary.main,
            fontFamily: theme.typography.fontFamily,
          }}
        >
          MediCareAI
        </Typography>
        <Typography
          variant="h5"
          sx={{ mb: 4, textAlign: 'center', fontWeight: 500 }}
        >
          智能健康管理平台
        </Typography>
        <Typography
          variant="body1"
          sx={{
            maxWidth: 400,
            textAlign: 'center',
            lineHeight: 1.8,
            color: theme.palette.text.secondary,
          }}
        >
          依托人工智能技术，为您提供专业的疾病管理、随访与健康咨询服务。让医疗更温暖，让健康更简单。
        </Typography>
      </Box>

      {/* 右侧登录表单 */}
      <Box
        sx={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          p: { xs: 2, sm: 4 },
        }}
      >
        <Paper
          elevation={0}
          sx={{
            width: '100%',
            maxWidth: 420,
            p: { xs: 3, sm: 4 },
            borderRadius: 3,
            bgcolor: 'background.paper',
            border: '1px solid #F0E6DC',
          }}
        >
          <Typography
            variant="h4"
            sx={{ fontWeight: 700, mb: 1, color: theme.palette.text.primary }}
          >
            欢迎回来
          </Typography>
          <Typography
            variant="body2"
            sx={{ mb: 4, color: theme.palette.text.secondary }}
          >
            请登录您的患者账号
          </Typography>

          <Box component="form" onSubmit={handleSubmit} noValidate>
            <TextField
              fullWidth
              label="邮箱地址"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              margin="normal"
              required
              autoComplete="email"
              disabled={loading}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Email sx={{ color: theme.palette.primary.main }} />
                  </InputAdornment>
                ),
              }}
              sx={{ mb: 2 }}
            />
            <TextField
              fullWidth
              label="密码"
              type={showPassword ? 'text' : 'password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              margin="normal"
              required
              autoComplete="current-password"
              disabled={loading}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Lock sx={{ color: theme.palette.primary.main }} />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      onClick={handleTogglePassword}
                      edge="end"
                      tabIndex={-1}
                      aria-label="切换密码可见性"
                    >
                      {showPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
              sx={{ mb: 3 }}
            />

            <Button
              type="submit"
              fullWidth
              variant="contained"
              size="large"
              disabled={loading}
              sx={{
                py: 1.5,
                borderRadius: 2,
                fontWeight: 600,
                fontSize: '1rem',
                textTransform: 'none',
              }}
            >
              {loading ? (
                <CircularProgress size={24} color="inherit" />
              ) : (
                '登录'
              )}
            </Button>
          </Box>

          <Box sx={{ mt: 3, textAlign: 'center' }}>
            <Typography
              variant="body2"
              sx={{ color: theme.palette.text.secondary }}
            >
              没有账号？{' '}
              <Link
                component="button"
                type="button"
                onClick={() => navigate('/register')}
                sx={{
                  color: theme.palette.primary.main,
                  fontWeight: 600,
                  textDecoration: 'none',
                  '&:hover': { textDecoration: 'underline' },
                }}
              >
                去注册
              </Link>
            </Typography>
          </Box>
        </Paper>
      </Box>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default LoginPage;
