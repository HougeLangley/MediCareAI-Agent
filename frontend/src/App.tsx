import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import patientTheme from './theme';
import ChatPage from './components/ChatPage';
import AdminLayout from './admin/layout/AdminLayout';
import DashboardPage from './admin/pages/DashboardPage';
import LLMProvidersPage from './admin/pages/LLMProvidersPage';
import SystemSettingsPage from './admin/pages/SystemSettingsPage';

function App() {
  return (
    <ThemeProvider theme={patientTheme}>
      <CssBaseline />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="providers" element={<LLMProvidersPage />} />
            <Route path="settings" element={<SystemSettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
