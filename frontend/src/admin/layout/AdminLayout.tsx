import { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation, Link } from 'react-router-dom';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  Typography,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  IconButton,
  Divider,
  CircularProgress,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import DashboardIcon from '@mui/icons-material/Dashboard';
import SettingsIcon from '@mui/icons-material/Settings';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import PeopleIcon from '@mui/icons-material/People';
import LocalHospitalIcon from '@mui/icons-material/LocalHospital';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import AssignmentIcon from '@mui/icons-material/Assignment';
import LogoutIcon from '@mui/icons-material/Logout';
import { logout, getMe } from '../../api/admin';
import AdminLoginPage from '../pages/AdminLoginPage';
import ChangePasswordPage from '../pages/ChangePasswordPage';

const DRAWER_WIDTH = 240;

const NAV_ITEMS = [
  { path: '/admin', label: '仪表盘', icon: <DashboardIcon /> },
  { path: '/admin/users', label: '用户管理', icon: <PeopleIcon /> },
  { path: '/admin/doctors', label: '医生认证', icon: <LocalHospitalIcon /> },
  { path: '/admin/providers', label: 'LLM 供应商', icon: <SmartToyIcon /> },
  { path: '/admin/knowledge', label: '知识库管理', icon: <MenuBookIcon /> },
  { path: '/admin/reviews', label: '病例审核', icon: <AssignmentIcon /> },
  { path: '/admin/settings', label: '系统设置', icon: <SettingsIcon /> },
];

export default function AdminLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  // 将 localStorage 检查移到初始状态计算，避免在 effect 同步体中 setState
  const [authState, setAuthState] = useState(() => {
    const token = localStorage.getItem('access_token');
    return {
      checked: !token,      // 无 token 时已检查完毕
      authenticated: !!token,
      needPasswordChange: false,
    };
  });
  const navigate = useNavigate();
  const location = useLocation();

  const { checked: authChecked, authenticated: isAuthenticated, needPasswordChange } = authState;

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      // 无 token 时初始状态已正确，无需同步 setState
      return;
    }
    // 异步验证 token
    getMe()
      .then((user) => {
        setAuthState({
          checked: true,
          authenticated: true,
          needPasswordChange:
            user.password_change_required ||
            localStorage.getItem('password_change_required') === 'true',
        });
      })
      .catch(() => {
        logout();
        setAuthState({ checked: true, authenticated: false, needPasswordChange: false });
      });
  }, [location.pathname]);

  const handleDrawerToggle = () => setMobileOpen(!mobileOpen);

  const handleLogout = () => {
    logout();
    setAuthState({ checked: true, authenticated: false, needPasswordChange: false });
    navigate('/admin');
  };

  // Show loading while checking auth
  if (!authChecked) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  // Not authenticated → show login page
  if (!isAuthenticated) {
    return <AdminLoginPage />;
  }

  // Authenticated but need password change → show change password page
  if (needPasswordChange) {
    return <ChangePasswordPage />;
  }

  const drawer = (
    <Box>
      <Toolbar sx={{ justifyContent: 'center' }}>
        <Typography variant="h6" sx={{ fontWeight: 700, color: '#1565C0' }}>
          MediCareAI 管理
        </Typography>
      </Toolbar>
      <Divider />
      <List>
        {NAV_ITEMS.map((item) => {
          const isSelected =
            location.pathname === item.path ||
            (item.path !== '/admin' && location.pathname.startsWith(item.path));
          return (
            <ListItem key={item.path} disablePadding>
              <ListItemButton
                component={Link}
                to={item.path}
                selected={isSelected}
                sx={{
                  '&.Mui-selected': {
                    bgcolor: '#E3F2FD',
                    borderRight: '3px solid #1565C0',
                  },
                }}
              >
                <ListItemIcon sx={{ color: isSelected ? '#1565C0' : 'inherit' }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText primary={item.label} />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
      <Divider />
      <List>
        <ListItem disablePadding>
          <ListItemButton onClick={handleLogout}>
            <ListItemIcon><LogoutIcon /></ListItemIcon>
            <ListItemText primary="退出登录" />
          </ListItemButton>
        </ListItem>
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: '#F5F7FA' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { md: `calc(100% - ${DRAWER_WIDTH}px)` },
          ml: { md: `${DRAWER_WIDTH}px` },
          bgcolor: '#fff',
          color: '#333',
          boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { md: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" sx={{ flexGrow: 1, fontWeight: 600 }}>
            {NAV_ITEMS.find(
              (i) => i.path === location.pathname || (i.path !== '/admin' && location.pathname.startsWith(i.path))
            )?.label || '管理后台'}
          </Typography>
        </Toolbar>
      </AppBar>

      <Box
        component="nav"
        sx={{ width: { md: DRAWER_WIDTH }, flexShrink: { md: 0 } }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', md: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: DRAWER_WIDTH },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', md: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: DRAWER_WIDTH },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { md: `calc(100% - ${DRAWER_WIDTH}px)` },
          mt: 8,
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
}
