import { createTheme } from '@mui/material/styles';

/**
 * 医生端主题 — 冷色调专业感
 * 主色: 医疗蓝 #2196F3
 * 辅色: 深灰蓝 #37474F
 * 背景: 极浅灰蓝 #F5F7FA
 */
export const doctorTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#2196F3',
      light: '#64B5F6',
      dark: '#1976D2',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#607D8B',
      light: '#90A4AE',
      dark: '#455A64',
    },
    background: {
      default: '#F5F7FA',
      paper: '#FFFFFF',
    },
    text: {
      primary: '#263238',
      secondary: '#607D8B',
    },
    error: { main: '#E53935' },
    warning: { main: '#FB8C00' },
    success: { main: '#43A047' },
    info: { main: '#1E88E5' },
  },
  typography: {
    fontFamily: '"Inter", "PingFang SC", "Microsoft YaHei", sans-serif',
    h6: { fontWeight: 600, fontSize: '1.1rem' },
    subtitle1: { fontWeight: 500, fontSize: '0.95rem' },
    body1: { fontSize: '0.9375rem', lineHeight: 1.6 },
    body2: { fontSize: '0.875rem', lineHeight: 1.6 },
    caption: { fontSize: '0.75rem', color: '#607D8B' },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          fontWeight: 500,
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          '& fieldset': { borderColor: '#E0E6ED' },
          '&:hover fieldset': { borderColor: '#2196F3' },
          '&.Mui-focused fieldset': { borderColor: '#2196F3' },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 1px 4px rgba(38,50,56,0.08)',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 6,
          fontWeight: 500,
        },
      },
    },
  },
});

export default doctorTheme;
