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
  Checkbox,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
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
  terms: boolean;
}

interface FormErrors {
  name?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
  phone?: string;
  terms?: string;
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
  if (!data.terms) {
    errors.terms = '请同意用户协议和隐私政策';
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
    terms: false,
  });

  const [errors, setErrors] = useState<FormErrors>({});
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toastOpen, setToastOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState('');
  const [termsDialogOpen, setTermsDialogOpen] = useState(false);
  const [privacyDialogOpen, setPrivacyDialogOpen] = useState(false);

  const passwordStrength = useMemo(() => checkPasswordStrength(formData.password), [formData.password]);
  const strengthPercent = useMemo(() => Math.min((passwordStrength.score / 6) * 100, 100), [passwordStrength.score]);

  const handleChange = useCallback((field: keyof FormData) => (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = field === 'terms' ? event.target.checked : event.target.value;
    setFormData((prev) => ({ ...prev, [field]: value }));
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
                mb: 1.5,
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2,
                },
              }}
            />

            <Box sx={{ mb: 2, display: 'flex', alignItems: 'flex-start' }}>
              <Checkbox
                checked={formData.terms}
                onChange={handleChange('terms')}
                disabled={isSubmitting}
                sx={{ pt: 0.5 }}
              />
              <Box>
                <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                  我已阅读并同意{' '}
                  <Link
                    component="button"
                    type="button"
                    variant="body2"
                    onClick={() => setTermsDialogOpen(true)}
                    sx={{ verticalAlign: 'baseline', fontWeight: 600 }}
                  >
                    用户协议
                  </Link>{' '}
                  和{' '}
                  <Link
                    component="button"
                    type="button"
                    variant="body2"
                    onClick={() => setPrivacyDialogOpen(true)}
                    sx={{ verticalAlign: 'baseline', fontWeight: 600 }}
                  >
                    隐私政策
                  </Link>
                </Typography>
                {errors.terms && (
                  <Typography variant="caption" color="error">
                    {errors.terms}
                  </Typography>
                )}
              </Box>
            </Box>

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

      <Dialog open={termsDialogOpen} onClose={() => setTermsDialogOpen(false)} maxWidth="md" fullWidth scroll="paper">
        <DialogTitle sx={{ bgcolor: 'primary.main', color: 'white' }}>用户服务协议</DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2" paragraph sx={{ color: 'text.secondary', fontSize: '0.75rem' }}>
            最后更新日期：2025年2月
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', color: 'error.main' }}>
            重要提示
          </Typography>
          <Typography variant="body2" paragraph>
            欢迎使用 MediCareAI（以下简称"本服务"）！本协议是您（以下简称"用户"）与本服务提供方（以下简称"我们"）之间就使用 MediCareAI 服务所订立的协议。请您在使用本服务前仔细阅读并充分理解本协议的全部内容。当您点击"同意"按钮、注册账号或以其他任何方式使用本服务时，即表示您已阅读、理解并同意接受本协议的全部约束。若您不同意本协议的任何内容，请勿使用本服务。
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2 }}>
            第一条 术语定义
          </Typography>
          <Typography variant="body2" paragraph>
            1.1 <strong>本服务</strong>：指由我们开发、运营的基于人工智能的智能疾病管理系统，包括但不限于患者档案管理、AI智能诊断、文档智能处理、医疗记录管理、知识库系统、医生协作平台等功能模块。<br /><br />
            1.2 <strong>用户</strong>：指注册、登录并使用本服务的自然人、医疗机构或组织。<br /><br />
            1.3 <strong>患者</strong>：指其个人信息和健康数据被录入本系统进行管理的自然人。<br /><br />
            1.4 <strong>医生</strong>：指经过我们认证审核，具备相应医疗资质的专业医师。<br /><br />
            1.5 <strong>管理员</strong>：指负责系统运营、管理、监控及知识库维护的我们授权人员。
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2 }}>
            第二条 协议的接受与适用
          </Typography>
          <Typography variant="body2" paragraph>
            2.1 <strong>协议的接受</strong>：您通过点击"同意"按钮、注册账号或以其他任何方式使用本服务，即视为您已充分阅读、理解并同意接受本协议的全部内容。<br /><br />
            2.2 <strong>协议更新</strong>：我们有权根据法律法规变化、技术发展及业务需要，对本协议进行修改。修改后的协议将在本平台公布，一经公布即生效。您继续使用本服务，视为您接受修改后的协议。<br /><br />
            2.3 <strong>单独协议</strong>：本协议为用户服务协议，与本服务同时提供的《隐私保护政策》及其他相关规则共同构成您与我们之间的完整协议。
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2 }}>
            第三条 用户注册与账号管理
          </Typography>
          <Typography variant="body2" paragraph>
            3.1 <strong>注册要求</strong>：用户注册时应当提供真实、准确、完整的信息，包括但不限于真实姓名、身份证号码、联系方式等。如提供的信息不真实、不准确或不完整，我们将有权暂停或终止您的账号使用权。<br /><br />
            3.2 <strong>账号安全</strong>：用户应当妥善保管账号及密码，因您保管不善可能导致账号被盗用。您对以其账号进行的所有活动负责。<br /><br />
            3.3 <strong>账号权限</strong>：本服务支持患者、医生、管理员三种用户角色，不同角色拥有不同的权限。<br /><br />
            3.4 <strong>账号注销</strong>：您可随时申请注销账号。账号注销后，您的个人信息将被删除或匿名化处理，但法律法规另有规定的除外。
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2 }}>
            第四条 用户个人信息保护
          </Typography>
          <Typography variant="body2" paragraph>
            4.1 <strong>信息收集范围</strong>：根据《中华人民共和国个人信息保护法》及《中华人民共和国民法典》的相关规定，我们可能会收集身份信息、联系方式、生物识别信息、健康信息、文档信息等。<br /><br />
            4.2 <strong>敏感个人信息处理</strong>：健康信息属于《个人信息保护法》规定的"敏感个人信息"。处理敏感个人信息，应当取得您的单独同意，并采取严格保护措施。<br /><br />
            4.3 <strong>信息使用目的</strong>：我们收集和使用您的信息，仅用于提供AI智能诊断服务、完善患者档案和病史记录、实现疾病追踪和随访管理、医生诊疗辅助和协作、改进服务质量。未经您同意，我们不会将您的个人信息用于与上述目的无关的其他用途。<br /><br />
            4.4 <strong>信息共享与披露</strong>：除获得您的明确同意、为完成服务所必需的第三方服务提供商、依法向有关主管部门报告或配合执法机关查询、为维护公共利益或国家利益所必需的情况外，我们不会向第三方共享您的个人信息。<br /><br />
            4.5 <strong>信息存储与安全</strong>：我们将在法律法规规定的期限内保存您的个人信息，采用加密、脱敏等技术手段保护您的信息安全，定期进行安全审计和风险评估，建立应急响应机制，防范数据泄露风险。<br /><br />
            4.6 <strong>您的权利</strong>：根据《个人信息保护法》的规定，您享有访问权、更正权、删除权、撤回同意权、注销账号权。<br /><br />
            4.7 <strong>未成年人保护</strong>：我们非常重视对未成年人的保护。如您是未成年人，请在监护人的陪同下使用本服务。
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2 }}>
            第五条 用户行为规范
          </Typography>
          <Typography variant="body2" paragraph>
            5.1 <strong>合法合规使用</strong>：您应当遵守国家法律法规，不得利用本服务从事传播违法、不良信息，侵犯他人知识产权或其他合法权益，进行网络攻击、黑客行为，恶意注册账号、刷量作弊等行为。<br /><br />
            5.2 <strong>内容真实性</strong>：您上传的病历资料、诊断信息等应当真实、准确。如因信息不实导致损害，您应承担相应责任。<br /><br />
            5.3 <strong>不得滥用AI功能</strong>：您不得利用AI诊断功能进行欺诈、误导或其他不当目的。<br /><br />
            5.4 <strong>不得传播AI诊断结果</strong>：AI诊断结果仅供参考，不得作为医疗诊断的唯一依据，不得用于医疗纠纷中的不当用途。
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2 }}>
            第六条 知识产权声明
          </Typography>
          <Typography variant="body2" paragraph>
            6.1 <strong>软件知识产权</strong>：本服务的软件、代码、文档、数据等知识产权归我们或相关权利人所有，受《中华人民共和国著作权法》、《中华人民共和国专利法》等法律保护。<br /><br />
            6.2 <strong>用户内容归属</strong>：您上传至本服务的文档、病历资料等内容的知识产权归您或相关权利人所有。您授予我们在本服务范围内非独家、免费的使用许可。<br /><br />
            6.3 <strong>禁止反向工程</strong>：您不得对本软件进行反向工程、反编译、反汇编或其他逆向操作。
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2, color: 'error.main' }}>
            第七条 免责声明与责任限制（重要）
          </Typography>
          <Typography variant="body2" paragraph>
            7.1 <strong>AI诊断免责声明</strong>：<br />
            • AI诊断结果仅供参考，不构成正式医疗诊断<br />
            • AI系统可能存在误诊、漏诊风险，不承担医疗损害赔偿责任<br />
            • 重大疾病诊断应以专业医生的诊断为准<br />
            • 您使用AI诊断结果产生的任何后果由您自行承担<br /><br />
            7.2 <strong>服务中断与故障</strong>：因不可抗力（包括但不限于自然灾害、政府行为、网络故障等）导致的服务中断，我们不承担责任。因用户设备问题或网络原因导致的服务异常，我们不承担责任。我们不保证服务连续性、稳定性和无错误。<br /><br />
            7.3 <strong>第三方服务免责</strong>：本服务可能使用第三方服务，如阿里云OSS、OpenAI API等。对于第三方服务的质量、安全、合规性，我们不承担任何责任。
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2 }}>
            第八条 争议解决
          </Typography>
          <Typography variant="body2" paragraph>
            8.1 <strong>法律适用</strong>：本协议的订立、执行、解释及争议解决均适用中华人民共和国法律。<br /><br />
            8.2 <strong>争议解决方式</strong>：双方应友好协商解决；协商不成的，任何一方均可向本服务提供方所在地人民法院提起诉讼。
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2, color: 'warning.main' }}>
            特别提示
          </Typography>
          <Typography variant="body2" paragraph>
            1. MediCareAI 是医疗辅助工具，AI诊断结果仅供参考，不替代专业医生的诊断<br />
            2. 您上传的所有文档和医疗信息将受到严格保护，我们将按照法律法规要求进行处理<br />
            3. 使用本服务即表示您理解并接受以上条款<br /><br />
            如对本协议有任何疑问，请联系我们：邮箱：hougelangley1987@gmail.com
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTermsDialogOpen(false)} variant="contained">我已阅读并理解</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={privacyDialogOpen} onClose={() => setPrivacyDialogOpen(false)} maxWidth="md" fullWidth scroll="paper">
        <DialogTitle sx={{ bgcolor: 'secondary.main', color: 'white' }}>隐私保护政策</DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2" paragraph sx={{ color: 'text.secondary', fontSize: '0.75rem' }}>
            最后更新日期：2025年2月
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', color: 'primary.main' }}>
            欢迎使用 MediCareAI（以下简称"我们"或"本服务"）！
          </Typography>
          <Typography variant="body2" paragraph>
            我们深知个人信息对您的重要性，并将按照法律法规的要求，采取相应的安全保护措施，尽力保护您的个人信息安全可控。本隐私政策将帮助您了解我们如何收集、使用、存储、保护您的个人信息。
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2 }}>
            第一条 政策更新与生效
          </Typography>
          <Typography variant="body2" paragraph>
            1.1 <strong>政策更新</strong>：我们有权根据法律法规变化、业务发展及技术进步，对本隐私政策进行修改。修改后的隐私政策将在本平台公布，一经公布即生效。<br /><br />
            1.2 <strong>继续使用即视为同意</strong>：如果您不同意修改后的隐私政策内容，您有权停止使用本服务；如果您继续使用本服务，则视为您同意接受修改后的隐私政策。<br /><br />
            1.3 <strong>生效日期</strong>：本隐私政策自 2025年2月20日 起生效。
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2 }}>
            第二条 我们如何收集和使用您的个人信息
          </Typography>
          <Typography variant="body2" paragraph>
            2.1 <strong>信息收集范围</strong>：根据《中华人民共和国个人信息保护法》及《中华人民共和国民法典》的相关规定，我们可能会收集以下信息：<br /><br />
            <strong>身份信息</strong>：真实姓名、身份证号码、出生日期、性别等（用于用户身份认证、服务提供、法律合规要求）<br /><br />
            <strong>联系信息</strong>：手机号码、电子邮箱、地址等（用于服务通知、沟通联系、身份验证）<br /><br />
            <strong>生物识别信息</strong>：指纹、面部特征等（如适用，用于设备识别、安全验证、防止账号被盗用）<br /><br />
            <strong style={{color: 'error.main'}}>健康信息</strong>：病历、诊断结果、症状描述、病史、用药记录等（用于AI智能诊断、疾病管理、随访计划、病史追踪）<br /><br />
            <strong>文档信息</strong>：上传的病历资料、检查报告、影像资料等（用于疾病追踪、健康管理、AI辅助诊断）<br /><br />
            <strong>设备与网络信息</strong>：设备型号、操作系统、IP地址、使用日志等（用于设备兼容性、用户体验优化、安全防护）
          </Typography>

          <Typography variant="body2" paragraph>
            2.2 <strong>信息使用目的</strong>：我们收集和使用您的个人信息，仅用于以下目的：<br />
            • 提供AI智能诊断服务<br />
            • 完善患者档案和病史记录<br />
            • 实现疾病追踪和随访管理<br />
            • 医生诊疗辅助和协作<br />
            • 改进服务质量<br />
            • 安全防护<br />
            • 法律合规<br /><br />
            未经您同意，我们不会将您的个人信息用于与上述目的无关的其他用途。
          </Typography>

          <Typography variant="body2" paragraph>
            2.3 <strong>不收集的信息</strong>：我们不会主动收集您的银行卡、支付账户等敏感金融信息；您的浏览记录、消费习惯等行为数据；您的社交关系、通讯录等非必要信息。
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2, color: 'error.main' }}>
            第三条 敏感个人信息特别说明
          </Typography>
          <Typography variant="body2" paragraph>
            3.1 <strong>什么是敏感个人信息？</strong>：根据《个人信息保护法》第二十八条，敏感个人信息是指一旦泄露或者非法使用，可能导致自然人的人格尊严受到侵害或者人身、财产安全受到危害的个人信息，包括生物识别、宗教信仰、特定身份、医疗健康、金融账户、行踪轨迹等信息，以及不满十四周岁未成年人的个人信息。
          </Typography>

          <Typography variant="body2" paragraph>
            3.2 <strong>医疗健康信息的特殊保护</strong>：健康信息属于敏感个人信息，处理敏感个人信息应当具备以下条件：<br />
            • 取得您的<strong>单独同意</strong><br />
            • 具有特定的目的和充分的必要性<br />
            • 对该类个人信息进行严格保护
          </Typography>

          <Typography variant="body2" paragraph>
            3.3 <strong>敏感信息处理原则</strong>：<br />
            • <strong>单独同意原则</strong>：在收集前会明确告知您，并取得您的单独同意<br />
            • <strong>最小必要原则</strong>：仅收集实现服务功能所必需的最小范围信息<br />
            • <strong>明确告知原则</strong>：会在收集前明确告知信息收集的目的、方式和范围<br />
            • <strong>严格保护原则</strong>：采用加密、脱敏、访问控制等技术措施严格保护<br />
            • <strong>用途限定原则</strong>：严格限定在医疗健康相关用途范围内使用
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2 }}>
            第四条 我们如何共享、转让、公开披露您的个人信息
          </Typography>
          <Typography variant="body2" paragraph>
            4.1 <strong>共享</strong>：我们不会与任何公司、组织和个人共享您的个人信息，除非：<br />
            • <strong>获得您的明确同意</strong><br />
            • <strong>为完成服务所必需</strong>：与提供技术支持的第三方服务提供商共享（如阿里云OSS、OpenAI API等）<br />
            • <strong>为履行法定职责</strong>：依法向有关主管部门报告或配合执法机关查询<br />
            • <strong>为维护公共利益</strong>：为维护公共利益或国家利益所必需<br />
            • <strong>与授权合作伙伴共享</strong>：在获得您授权后，与授权合作伙伴（如医疗机构）共享
          </Typography>

          <Typography variant="body2" paragraph>
            4.2 <strong>转让</strong>：我们不会将您的个人信息转让给任何公司、组织和个人，除非获得您的同意、发生合并收购（我们会向您告知新的接收方，并要求其继续履行本隐私政策）或法律法规规定的情况。
          </Typography>

          <Typography variant="body2" paragraph>
            4.3 <strong>公开披露</strong>：我们仅会在获得您明确同意或法律法规规定的情况下公开披露您的个人信息。
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2 }}>
            第五条 我们如何存储您的个人信息
          </Typography>
          <Typography variant="body2" paragraph>
            5.1 <strong>存储地点</strong>：<br />
            • <strong>一般个人信息</strong>：中华人民共和国境内服务器<br />
            • <strong>敏感个人信息</strong>：在中华人民共和国境内存储，法律法规另有规定的除外
          </Typography>

          <Typography variant="body2" paragraph>
            5.2 <strong>存储期限</strong>：<br />
            • <strong>身份信息</strong>：为提供和保障服务所必需，最长不超过您注销账号后1年<br />
            • <strong>健康信息</strong>：为提供和保障服务所必需，最长不超过您注销账号后5年<br />
            • <strong>使用日志</strong>：为维护服务安全所必需，保存期限不少于6个月<br />
            • <strong>其他信息</strong>：当您停止使用本服务时，我们会及时删除或匿名化处理
          </Typography>

          <Typography variant="body2" paragraph>
            5.3 <strong>存储安全措施</strong>：<br />
            • <strong>加密存储</strong>：敏感信息采用加密方式存储<br />
            • <strong>访问控制</strong>：实施严格的访问权限管理，仅授权人员可访问<br />
            • <strong>安全审计</strong>：定期进行安全审计和风险评估<br />
            • <strong>数据备份</strong>：定期对重要数据进行备份<br />
            • <strong>应急响应</strong>：建立数据泄露应急响应机制
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2 }}>
            第六条 您的权利
          </Typography>
          <Typography variant="body2" paragraph>
            根据《个人信息保护法》的规定，您享有以下权利：
          </Typography>

          <Typography variant="body2" paragraph>
            6.1 <strong>访问权</strong>：您有权访问您的个人信息，包括您的基本信息、健康档案和病历信息、文档上传记录、使用日志。您可以在"设置"或"个人中心"中查看和导出您的个人信息。
          </Typography>

          <Typography variant="body2" paragraph>
            6.2 <strong>更正权</strong>：您有权更正不准确或不完整的个人信息。您可以在"设置"或"个人中心"中修改您的个人信息。
          </Typography>

          <Typography variant="body2" paragraph>
            6.3 <strong>删除权</strong>：在以下情形中，您可以要求删除您的个人信息：不再使用本服务、提供的目的实现、您撤回同意、法律规定的删除情形。您可在"设置"→"账号管理"→"申请删除"中提交申请，我们将在15个工作日内处理。
          </Typography>

          <Typography variant="body2" paragraph>
            6.4 <strong>撤回同意权</strong>：您有权随时撤回对个人信息处理的同意。您可以在"设置"→"隐私设置"中撤回同意，或通过 hougelangley1987@gmail.com 联系我们。
          </Typography>

          <Typography variant="body2" paragraph>
            6.5 <strong>注销账号权</strong>：您有权随时申请注销账号。您可在"设置"→"账号管理"→"注销账号"中提交申请。账号注销后，您的个人信息将被删除或匿名化处理，且无法恢复。
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2 }}>
            第七条 未成年人信息保护
          </Typography>
          <Typography variant="body2" paragraph>
            7.1 <strong>定义</strong>：不满十四周岁的未成年人为儿童，其个人信息为儿童个人信息。
          </Typography>

          <Typography variant="body2" paragraph>
            7.2 <strong>保护原则</strong>：我们非常重视对未成年人的保护，处理儿童个人信息时将遵循以下原则：<br />
            • <strong>专门保护</strong>：采取专门的保护措施保护儿童个人信息<br />
            • <strong>家长同意</strong>：处理儿童个人信息应当取得其监护人的同意<br />
            • <strong>最小收集</strong>：仅收集实现服务功能所必需的最小范围信息
          </Typography>

          <Typography variant="body2" paragraph>
            7.3 <strong>儿童信息处理</strong>：我们不会主动收集未成年人的个人信息，特别是敏感的健康信息。如发现已收集未成年人的个人信息，我们将尽快删除。
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2 }}>
            第八条 数据跨境传输
          </Typography>
          <Typography variant="body2" paragraph>
            8.1 <strong>数据本地化存储</strong>：根据《个人信息保护法》第三十八条的规定，我们目前将所有个人信息存储在中华人民共和国境内服务器。
          </Typography>

          <Typography variant="body2" paragraph>
            8.2 <strong>数据出境情形</strong>：如需将个人信息传输至境外，我们将：<br />
            • 取得您的单独同意<br />
            • 通过国家网信部门组织的安全评估<br />
            • 签订个人信息出境标准合同<br />
            • 通过个人信息保护认证<br />
            • 通过专业机构进行个人信息保护认证
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2 }}>
            第九条 响应您的请求
          </Typography>
          <Typography variant="body2" paragraph>
            9.1 <strong>请求处理流程</strong>：<br />
            • 验证您的身份和权限<br />
            • 核实您请求的合理性<br />
            • 按照法律法规要求处理您的请求<br />
            • 将处理结果通知您
          </Typography>

          <Typography variant="body2" paragraph>
            9.2 <strong>处理时限</strong>：<br />
            • <strong>访问权、更正权、删除权</strong>：15个工作日内<br />
            • <strong>其他请求</strong>：30个工作日内
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2 }}>
            第十条 Cookie 和类似技术的使用
          </Typography>
          <Typography variant="body2" paragraph>
            我们使用 Cookie 和类似技术用于用户识别、安全防护、统计分析、功能实现。您可以通过浏览器设置拒绝或删除 Cookie，但拒绝 Cookie 可能会影响本服务的正常使用。
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2 }}>
            第十一条 第三方服务说明
          </Typography>
          <Typography variant="body2" paragraph>
            本服务可能使用以下第三方服务：<br />
            • <strong>阿里云</strong>：对象存储服务（OSS），用于存储用户上传的文档<br />
            • <strong>OpenAI</strong>：AI大模型服务，用于AI智能诊断功能<br />
            • <strong>其他服务</strong>：技术支持、云服务等
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2 }}>
            第十二条 您的个人信息安全
          </Typography>
          <Typography variant="body2" paragraph>
            12.1 <strong>安全措施</strong>：我们采用加密技术（SSL加密、数据加密）、访问控制、安全审计、安全培训、应急响应机制等措施保护您的个人信息安全。
          </Typography>

          <Typography variant="body2" paragraph>
            12.2 <strong>数据泄露通知</strong>：如发生个人信息泄露事件，我们将立即启动应急预案，向监管部门报告，通知您（如可能对您造成风险），并采取补救措施。
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2 }}>
            第十三条 联系我们
          </Typography>
          <Typography variant="body2" paragraph>
            如您对本隐私政策有任何疑问、意见或建议，或需要行使您的个人信息相关权利，请通过以下方式联系我们：<br /><br />
            <strong>电子邮件</strong>：hougelangley1987@gmail.com<br /><br />
            我们将在收到您的请求后15个工作日内予以回复。
          </Typography>

          <Typography variant="body1" paragraph sx={{ fontWeight: 'bold', mt: 2, color: 'warning.main' }}>
            特别提示
          </Typography>
          <Typography variant="body2" paragraph>
            1. <strong>AI诊断免责声明</strong>：AI诊断结果仅供参考，不构成正式医疗诊断，不承担医疗损害赔偿责任。<br />
            2. <strong>信息真实性</strong>：您上传的病历资料、诊断信息等应当真实、准确。<br />
            3. <strong>健康信息敏感</strong>：健康信息属于敏感个人信息，将受到严格保护。<br />
            4. <strong>数据安全</strong>：我们采用多种技术措施保护您的数据安全，但无法绝对保证数据安全。<br />
            5. <strong>法律合规</strong>：我们严格遵守《个人信息保护法》、《网络安全法》、《数据安全法》等法律法规要求。
          </Typography>

          <Typography variant="body2" paragraph sx={{ mt: 2, fontStyle: 'italic' }}>
            感谢您对 MediCareAI 的信任与支持！
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPrivacyDialogOpen(false)} variant="contained">我已阅读并理解</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default RegisterPage;
