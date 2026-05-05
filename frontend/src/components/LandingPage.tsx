import { useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Typography,
  Button,
  Stack,
  Paper,
} from '@mui/material';
import MedicalServicesIcon from '@mui/icons-material/MedicalServices';
import ChatBubbleOutlineRoundedIcon from '@mui/icons-material/ChatBubbleOutlineRounded';
import SecurityIcon from '@mui/icons-material/Security';
import SpeedIcon from '@mui/icons-material/Speed';

const warmPrimary = '#E8956A';
const warmText = '#5C4033';
const warmBg = '#FFFBF5';

export default function LandingPage() {
  const navigate = useNavigate();

  const features = [
    {
      icon: <ChatBubbleOutlineRoundedIcon sx={{ fontSize: 40, color: warmPrimary }} />,
      title: '智能对话',
      desc: '基于大语言模型的医疗问答，支持症状分析、检查报告解读',
    },
    {
      icon: <SecurityIcon sx={{ fontSize: 40, color: warmPrimary }} />,
      title: '安全可靠',
      desc: '符合医疗数据安全规范，保护您的隐私信息',
    },
    {
      icon: <SpeedIcon sx={{ fontSize: 40, color: warmPrimary }} />,
      title: '实时响应',
      desc: 'SSE 流式输出，实时显示 AI 思考过程和诊断结果',
    },
  ];

  return (
    <Box sx={{ minHeight: '100vh', bgcolor: warmBg }}>
      {/* Hero Section */}
      <Box
        sx={{
          pt: { xs: 8, md: 12 },
          pb: { xs: 6, md: 10 },
          textAlign: 'center',
          background: `linear-gradient(135deg, ${warmBg} 0%, #FFF5EB 100%)`,
        }}
      >
        <Container maxWidth="md">
          <Box sx={{ mb: 3 }}>
            <MedicalServicesIcon sx={{ fontSize: 64, color: warmPrimary }} />
          </Box>
          <Typography
            variant="h2"
            sx={{
              fontWeight: 800,
              color: warmText,
              mb: 2,
              fontSize: { xs: '2rem', md: '3rem' },
            }}
          >
            MediCareAI-Agent
          </Typography>
          <Typography
            variant="h5"
            sx={{
              color: '#8B7355',
              mb: 4,
              fontWeight: 400,
              fontSize: { xs: '1.1rem', md: '1.5rem' },
            }}
          >
            您的智能医疗助手
          </Typography>
          <Typography
            variant="body1"
            sx={{
              color: '#8B7355',
              mb: 5,
              maxWidth: 600,
              mx: 'auto',
              lineHeight: 1.8,
            }}
          >
            基于先进的 AI 技术，提供智能问诊、症状分析、健康检查报告解读等服务。
            无需等待，立即获得专业的医疗建议。
          </Typography>

          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={2}
            justifyContent="center"
            alignItems="center"
          >
            <Button
              variant="contained"
              size="large"
              onClick={() => navigate('/chat')}
              sx={{
                bgcolor: warmPrimary,
                color: '#fff',
                px: 4,
                py: 1.5,
                borderRadius: 3,
                fontSize: '1.1rem',
                fontWeight: 600,
                textTransform: 'none',
                '&:hover': { bgcolor: '#D4835A' },
              }}
            >
              🚀 立即体验
            </Button>
            <Button
              variant="outlined"
              size="large"
              onClick={() => navigate('/login')}
              sx={{
                borderColor: warmPrimary,
                color: warmPrimary,
                px: 4,
                py: 1.5,
                borderRadius: 3,
                fontSize: '1.1rem',
                fontWeight: 600,
                textTransform: 'none',
                '&:hover': { borderColor: '#D4835A', bgcolor: 'rgba(232,149,106,0.04)' },
              }}
            >
              登录 / 注册
            </Button>
          </Stack>
        </Container>
      </Box>

      {/* Features Section */}
      <Container maxWidth="lg" sx={{ py: 8 }}>
        <Typography
          variant="h4"
          sx={{
            textAlign: 'center',
            fontWeight: 700,
            color: warmText,
            mb: 6,
          }}
        >
          核心功能
        </Typography>
        <Stack
          direction={{ xs: 'column', md: 'row' }}
          spacing={3}
          justifyContent="center"
        >
          {features.map((feature, idx) => (
            <Paper
              key={idx}
              elevation={0}
              sx={{
                p: 4,
                flex: 1,
                maxWidth: 360,
                borderRadius: 4,
                bgcolor: '#fff',
                border: '1px solid rgba(232,149,106,0.15)',
                textAlign: 'center',
                transition: 'transform 0.2s, box-shadow 0.2s',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: '0 8px 24px rgba(92,64,51,0.08)',
                },
              }}
            >
              <Box sx={{ mb: 2 }}>{feature.icon}</Box>
              <Typography
                variant="h6"
                sx={{ fontWeight: 700, color: warmText, mb: 1 }}
              >
                {feature.title}
              </Typography>
              <Typography variant="body2" sx={{ color: '#8B7355', lineHeight: 1.7 }}>
                {feature.desc}
              </Typography>
            </Paper>
          ))}
        </Stack>
      </Container>

      {/* Footer */}
      <Box sx={{ py: 4, textAlign: 'center', borderTop: '1px solid #F5E6D3' }}>
        <Typography variant="body2" sx={{ color: '#8B7355' }}>
          © 2026 MediCareAI-Agent. 本系统提供的医疗建议仅供参考，不替代专业医生诊断。
        </Typography>
      </Box>
    </Box>
  );
}
