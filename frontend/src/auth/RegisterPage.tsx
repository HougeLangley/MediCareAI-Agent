import React, { useState, useMemo, useCallback } from 'react';
import {
  Box,
  Container,
  Paper,
  Typography,
  TextField,
  Button,
  Alert,
  CircularProgress,
  Link,
  ToggleButton,
  ToggleButtonGroup,
  InputAdornment,
  IconButton,
  Snackbar,
  LinearProgress,
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Email,
  Lock,
  Person,
  Phone,
  LocalHospital,
  PersonOutlined,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { register, type RegisterRequest } from '../api/auth';

interface FormData {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
  phone: string;
  role: 'patient' | 'doctor';
}

interface FormErrors {
  name?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
  phone?: string;
  general?: string;
}

function checkPasswordStrength(password: string): { score: number; label: string; color: 'error' | 'warning' | 'success' } {
  let score = 0;
  if (password.length >= 8) score += 1;
  if (password.length >= 12) score += 1;
  if (/[A-Z]/.test(password)) score += 1;
  if (/[a-z]/.test(password)) score += 1;
  if (/[0-9]/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;

  if (score <= 2) return { score, label: '弱', color: 'error' };
  if (score <= 4) return { score, label: '中等', color: 'warning' };
  return { score, label: '强', color: 'success' };
}

function validateForm(data: FormData): FormErrors {
  const errors: FormErrors = {};
  if (!data.name.trim()) {
    errors.name = '请输入姓名';
  }
  if (!data.email.trim()) {
    errors.email = '请输入邮箱地址';
  } else if (!/^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i.test(data.email)) {
    errors.email = '请输入有效的邮箱地址';
  }
  if (!data.password) {
    errors.password = '请输入密码';
  } else if (data.password.length < 6) {
    errors.password = '密码长度至少为 6 个字符';
  }
  if (!data.confirmPassword) {
    errors.confirmPassword = '请再次输入密码';
  } else if (data.password !== data.confirmPassword) {
    errors.confirmPassword = '两次输入的密码不一致';
  }
  if (data.phone && !/^1[3-9]\d{9}$/.test(data.phone)) {
    errors.phone = '请输入有效的手机号码';
  }
  return errors;
}

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();

  const [formData, setFormData] = useState<FormData>({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    phone: '',
    role: 'patient',
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toastOpen, setToastOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState('');

  const passwordStrength = useMemo(() => checkPasswordStrength(formData.password), [formData.password]);
  const strengthPercent = useMemo(() => Math.min((passwordStrength.score / 6) * 100, 100), [passwordStrength.score]);

  const handleChange = useCallback((field: keyof FormData) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setFormData((prev) => ({ ...prev, [field]: event.target.value }));
    setErrors((prev) => ({ ...prev, [field]: undefined, general: undefined }));
  }, []);

  const handleRoleChange = useCallback((_: React.MouseEvent<HTMLElement>, newRole: 'patient' | 'doctor' | null) => {
    if (newRole) {
      setFormData((prev) => ({ ...prev, role: newRole }));
    }
  }, []);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const validationErrors = validateForm(formData);
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setIsSubmitting(true);
    setErrors({});

    try {
      const payload: RegisterRequest = {
        name: formData.name.trim(),
        email: formData.email.trim(),
        password: formData.password,
        role: formData.role,
        phone: formData.phone.trim() || undefined,
      };
      await register(payload);

      setToastMessage('注册成功！请查收邮件激活账号');
      setToastOpen(true);

      setTimeout(() => {
        navigate('/login');
      }, 2000);
    } catch (err: any) {
      setErrors({ general: err.message || '注册失败，请稍后重试' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCloseToast = () => {
    setToastOpen(false);
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        backgroundColor: '#FFFBF5',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        py: 4,
      }}
    >
      <Container maxWidth="sm">
        <Paper
          elevation={3}
          sx={{
            borderRadius: 4,
            padding: { xs: 3, sm: 5 },
            maxWidth: 480,
            margin: '0 auto',
            backgroundColor: 'background.paper',
            border: '1px solid #F5E6D3',
          }}
        >
          <Box sx={{ textAlign: 'center', mb: 4 }}>
            <LocalHospital sx={{ fontSize: 56, color: 'primary.main', mb: 2 }} />
            <Typography variant="h4" component="h1" sx={{ color: 'text.primary', fontWeight: 'bold' }} gutterBottom>
              创建账户
            </Typography>
            <Typography variant="body1" sx={{ color: 'text.secondary' }}>
              加入 MediCareAI，开启智能医疗之旅
            </Typography>
          </Box>

          {errors.general && (
            <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
              {errors.general}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit} noValidate>
            <Box sx={{ mb: 3, display: 'flex', justifyContent: 'center' }}>
              <ToggleButtonGroup
                value={formData.role}
                exclusive
                onChange={handleRoleChange}
                aria-label="选择角色"
                sx={{
                  '& .MuiToggleButton-root': {
                    borderRadius: '12px !important',
                    px: 4,
                    py: 1,
                    textTransform: 'none',
                    fontWeight: 500,
                    borderColor: '#F5E6D3',
                    color: 'text.secondary',
                    '&.Mui-selected': {
                      backgroundColor: 'primary.main',
                      color: 'background.paper',
                      borderColor: 'primary.main',
                      '&:hover': {
                        backgroundColor: 'primary.dark',
                      },
                    },
                  },
                }}
              >
                <ToggleButton value="patient" aria-label="患者">
                  <PersonOutlined sx={{ mr: 1, fontSize: 20 }} />
                  患者
                </ToggleButton>
                <ToggleButton value="doctor" aria-label="医生">
                  <LocalHospital sx={{ mr: 1, fontSize: 20 }} />
                  医生
                </ToggleButton>
              </ToggleButtonGroup>
            </Box>

            <TextField
              fullWidth
              label="姓名"
              placeholder="请输入您的姓名"
              value={formData.name}
              onChange={handleChange('name')}
              error={!!errors.name}
              helperText={errors.name}
              disabled={isSubmitting}
              margin="normal"
              required
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <Person sx={{ color: 'text.secondary' }} />
                    </InputAdornment>
                  ),
                },
              }}
              sx={{
                mb: 1.5,
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2,
                },
              }}
            />

            <TextField
              fullWidth
              label="邮箱地址"
              type="email"
              placeholder="example@email.com"
              autoComplete="email"
              value={formData.email}
              onChange={handleChange('email')}
              error={!!errors.email}
              helperText={errors.email}
              disabled={isSubmitting}
              margin="normal"
              required
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <Email sx={{ color: 'text.secondary' }} />
                    </InputAdornment>
                  ),
                },
              }}
              sx={{
                mb: 1.5,
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2,
                },
              }}
            />

            <TextField
              fullWidth
              label="密码"
              type={showPassword ? 'text' : 'password'}
              placeholder="请输入密码"
              autoComplete="new-password"
              value={formData.password}
              onChange={handleChange('password')}
              error={!!errors.password}
              helperText={errors.password}
              disabled={isSubmitting}
              margin="normal"
              required
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <Lock sx={{ color: 'text.secondary' }} />
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        aria-label="切换密码可见性"
                        onClick={() => setShowPassword((prev) => !prev)}
                        edge="end"
                        disabled={isSubmitting}
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
                    </InputAdornment>
                  ),
                },
              }}
              sx={{
                mb: 1,
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2,
                },
              }}
            />

            {formData.password && (
              <Box sx={{ mb: 1.5, px: 0.5 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 0.5 }}>
                  <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                    密码强度
                  </Typography>
                  <Typography variant="caption" sx={{ color: passwordStrength.color === 'error' ? 'error.main' : passwordStrength.color === 'warning' ? '#FFB300' : '#81C784', fontWeight: 600 }}>
                    {passwordStrength.label}
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={strengthPercent}
                  color={passwordStrength.color}
                  sx={{
                    height: 6,
                    borderRadius: 3,
                    backgroundColor: '#F5E6D3',
                  }}
                />
              </Box>
            )}

            <TextField
              fullWidth
              label="确认密码"
              type={showConfirmPassword ? 'text' : 'password'}
              placeholder="请再次输入密码"
              autoComplete="new-password"
              value={formData.confirmPassword}
              onChange={handleChange('confirmPassword')}
              error={!!errors.confirmPassword}
              helperText={errors.confirmPassword}
              disabled={isSubmitting}
              margin="normal"
              required
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Lock sx={{ color: 'text.secondary' }} />
                  </InputAdornment>
                ),
                endAdornment: (
                  <InputAdornment position="end">
                    <IconButton
                      aria-label="切换确认密码可见性"
                      onClick={() => setShowConfirmPassword((prev) => !prev)}
                      edge="end"
                      disabled={isSubmitting}
                    >
                      {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                    </IconButton>
                  </InputAdornment>
                ),
              }}
              sx={{
                mb: 1.5,
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2,
                },
              }}
            />

            <TextField
              fullWidth
              label="手机号码"
              type="tel"
              placeholder="请输入手机号码（可选）"
              autoComplete="tel"
              value={formData.phone}
              onChange={handleChange('phone')}
              error={!!errors.phone}
              helperText={errors.phone}
              disabled={isSubmitting}
              margin="normal"
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Phone sx={{ color: 'text.secondary' }} />
                  </InputAdornment>
                ),
              }}
              sx={{
                mb: 3,
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2,
                },
              }}
            />

            <Button
              type="submit"
              fullWidth
              variant="contained"
              size="large"
              disabled={isSubmitting}
              sx={{
                py: 1.5,
                borderRadius: 3,
                backgroundColor: 'primary.main',
                fontWeight: 600,
                fontSize: '1rem',
                textTransform: 'none',
                '&:hover': {
                  backgroundColor: 'primary.dark',
                },
                '&.Mui-disabled': {
                  backgroundColor: 'primary.light',
                  color: 'background.paper',
                },
              }}
            >
              {isSubmitting ? (
                <CircularProgress size={24} color="inherit" />
              ) : (
                '注册'
              )}
            </Button>
          </Box>

          <Box sx={{ textAlign: 'center', mt: 3 }}>
            <Typography variant="body2" sx={{ color: 'text.secondary' }}>
              已有账号？{' '}
              <Link
                component="button"
                type="button"
                variant="body2"
                onClick={() => navigate('/login')}
                sx={{
                  color: 'primary.main',
                  fontWeight: 600,
                  textDecoration: 'none',
                  '&:hover': {
                    textDecoration: 'underline',
                  },
                }}
              >
                去登录
              </Link>
            </Typography>
          </Box>
        </Paper>
      </Container>

      <Snackbar
        open={toastOpen}
        autoHideDuration={3000}
        onClose={handleCloseToast}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert
          onClose={handleCloseToast}
          severity="success"
          sx={{
            width: '100%',
            borderRadius: 2,
            backgroundColor: '#FFF8E1',
            color: 'text.primary',
            '& .MuiAlert-icon': {
              color: '#81C784',
            },
          }}
        >
          {toastMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default RegisterPage;
