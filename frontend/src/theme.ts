import { createTheme } from '@mui/material/styles';

export const patientTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#E8956A',
      light: '#FFCCB0',
      dark: '#D4835A',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#8B7355',
      light: '#B8A084',
      dark: '#5C4033',
    },
    background: {
      default: '#FFFBF5',
      paper: '#FFFFFF',
    },
    text: {
      primary: '#5C4033',
      secondary: '#8B7355',
    },
    error: { main: '#E57373' },
    warning: { main: '#FFB300' },
    success: { main: '#81C784' },
    info: { main: '#64B5F6' },
  },
  typography: {
    fontFamily: '"Inter", "PingFang SC", "Microsoft YaHei", sans-serif',
    h6: { fontWeight: 600, fontSize: '1.1rem' },
    subtitle1: { fontWeight: 500, fontSize: '0.95rem' },
    body1: { fontSize: '0.9375rem', lineHeight: 1.6 },
    body2: { fontSize: '0.875rem', lineHeight: 1.6 },
    caption: { fontSize: '0.75rem', color: '#8B7355' },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          textTransform: 'none',
          fontWeight: 500,
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          '& fieldset': { borderColor: '#F5E6D3' },
          '&:hover fieldset': { borderColor: '#E8956A' },
          '&.Mui-focused fieldset': { borderColor: '#E8956A' },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          boxShadow: '0 2px 8px rgba(92,64,51,0.06)',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          fontWeight: 500,
        },
      },
    },
  },
});

export default patientTheme;
