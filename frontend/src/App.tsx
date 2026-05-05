import { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Box, CircularProgress } from '@mui/material';
import patientTheme from './theme';
import doctorTheme from './themes/doctorTheme';
import { getUserRole, isLoggedIn } from './api/auth';

// 公共路由
const LandingPage = lazy(() => import('./components/LandingPage'));
const ChatPage = lazy(() => import('./components/ChatPage'));
const HealthProfilePage = lazy(() => import('./patient/pages/HealthProfilePage'));
const FollowUpPage = lazy(() => import('./patient/pages/FollowUpPage'));

// 医生端
const DoctorLayout = lazy(() => import('./doctor/layout/DoctorLayout'));
const DoctorDashboard = lazy(() => import('./doctor/pages/DoctorDashboard'));
const DoctorCases = lazy(() => import('./doctor/pages/DoctorCases'));
const CaseDetailPage = lazy(() => import('./doctor/pages/CaseDetailPage'));

// 认证
const LoginPage = lazy(() => import('./auth/LoginPage'));
const RegisterPage = lazy(() => import('./auth/RegisterPage'));

// 管理员端 (原有)
import AdminLayout from './admin/layout/AdminLayout';
import DashboardPage from './admin/pages/DashboardPage';
import DoctorVerificationPage from './admin/pages/DoctorVerificationPage';
import LLMProvidersPage from './admin/pages/LLMProvidersPage';
import SystemSettingsPage from './admin/pages/SystemSettingsPage';
import KnowledgeBasePage from './admin/pages/KnowledgeBasePage';
import ReviewQueuePage from './admin/pages/ReviewQueuePage';
import AuditLogsPage from './admin/pages/AuditLogsPage';
import UsersPage from './admin/pages/UsersPage';
import NotificationsPage from './admin/pages/NotificationsPage';
import EmailManagementPage from './admin/pages/EmailManagementPage';

function LoadingFallback() {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <CircularProgress sx={{ color: 'primary.main' }} />
    </Box>
  );
}

/** 路由守卫 — 检查登录状态 */
function RequireAuth({ children }: { children: React.ReactNode }) {
  if (!isLoggedIn()) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

/** 路由守卫 — 检查角色 */
function RequireRole({ role, children }: { role: string; children: React.ReactNode }) {
  if (!isLoggedIn()) return <Navigate to="/login" replace />;
  const userRole = getUserRole();
  if (userRole !== role) {
    // 如果是 admin，允许访问所有页面
    if (userRole === 'admin') return <>{children}</>;
    // 否则跳转到对应首页
    return <Navigate to={userRole === 'doctor' ? '/doctor' : '/chat'} replace />;
  }
  return <>{children}</>;
}

/** 医生端 Theme Provider */
function DoctorThemeProvider({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider theme={doctorTheme}>
      <CssBaseline />
      {children}
    </ThemeProvider>
  );
}

function App() {
  return (
    <ThemeProvider theme={patientTheme}>
      <CssBaseline />
      <BrowserRouter>
        <Suspense fallback={<LoadingFallback />}>
          <Routes>
            {/* 公共路由 */}
            <Route path="/" element={<LandingPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* 患者端 */}
            <Route path="/health" element={<RequireRole role="patient"><HealthProfilePage /></RequireRole>} />
            <Route path="/followups" element={<RequireRole role="patient"><FollowUpPage /></RequireRole>} />

            {/* 医生端 — 独立蓝色主题 */}
            <Route path="/doctor" element={<RequireRole role="doctor"><DoctorThemeProvider><DoctorLayout /></DoctorThemeProvider></RequireRole>}>
              <Route index element={<DoctorDashboard />} />
              <Route path="cases" element={<DoctorCases />} />
              <Route path="cases/:caseId" element={<CaseDetailPage />} />
            </Route>

            {/* 管理员端 */}
            <Route path="/admin" element={<AdminLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="users" element={<UsersPage />} />
              <Route path="doctors" element={<DoctorVerificationPage />} />
              <Route path="providers" element={<LLMProvidersPage />} />
              <Route path="settings" element={<SystemSettingsPage />} />
              <Route path="knowledge" element={<KnowledgeBasePage />} />
              <Route path="reviews" element={<ReviewQueuePage />} />
              <Route path="audit-logs" element={<AuditLogsPage />} />
              <Route path="notifications" element={<NotificationsPage />} />
              <Route path="email" element={<EmailManagementPage />} />
            </Route>

            {/* 默认重定向 */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;
