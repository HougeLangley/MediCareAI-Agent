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
  Avatar,
  Divider,
  Button,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import DashboardIcon from '@mui/icons-material/Dashboard';
import PeopleIcon from '@mui/icons-material/People';
import MessageIcon from '@mui/icons-material/Message';
import SettingsIcon from '@mui/icons-material/Settings';
import LogoutIcon from '@mui/icons-material/Logout';
import SwitchAccountIcon from '@mui/icons-material/SwitchAccount';
import { logout, getMe } from '../../api/auth';
import type { UserInfo } from '../../api/auth';
import { flexRowGap1, flexRowGap2, pageCenter } from '../../styles/sxUtils';


const DRAWER_WIDTH = 240;

const NAV_ITEMS = [
  { path: '/doctor', label: '工作台', icon: <DashboardIcon /> },
  { path: '/doctor/cases', label: '患者列表', icon: <PeopleIcon /> },
  { path: '/doctor/messages', label: '消息中心', icon: <MessageIcon /> },
  { path: '/doctor/settings', label: '设置', icon: <SettingsIcon /> },
];

export default function DoctorLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    let mounted = true;
    getMe()
      .then((data) => {
        if (mounted) {
          setUser(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (mounted) {
          setLoading(false);
          navigate('/login');
        }
      });
    return () => {
      mounted = false;
    };
  }, [navigate]);

  const handleDrawerToggle = () => setMobileOpen(!mobileOpen);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleSwitchToPatient = () => {
    localStorage.setItem('user_role', 'patient');
    navigate('/chat');
  };

  if (loading) {
    return (
      <Box sx={pageCenter}>
        <CircularProgress sx={{ color: 'primary.main' }} />
      </Box>
    );
  }

  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Toolbar sx={{ justifyContent: 'center' }}>
        <Typography variant="h6" sx={{ fontWeight: 700, color: 'primary.main' }}>
          MediCareAI 医生端
        </Typography>
      </Toolbar>
      <Divider />
      <List sx={{ flexGrow: 1 }}>
        {NAV_ITEMS.map((item) => {
          const isSelected =
            location.pathname === item.path ||
            (item.path !== '/doctor' && location.pathname.startsWith(item.path));
          return (
            <ListItem key={item.path} disablePadding>
              <ListItemButton
                component={Link}
                to={item.path}
                selected={isSelected}
                sx={{
                  '&.Mui-selected': {
                    bgcolor: 'primary.light',
                    borderRight: '3px solid #2196F3',
                  },
                }}
              >
                <ListItemIcon sx={{ color: isSelected ? 'primary.main' : 'text.secondary' }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={item.label}
                  primaryTypographyProps={{
                    fontWeight: isSelected ? 600 : 500,
                    color: isSelected ? 'primary.main' : 'text.primary',
                  }}
                />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
      <Divider />
      <Box sx={{ p: 2 }}>
        <Button
          fullWidth
          variant="outlined"
          startIcon={<SwitchAccountIcon />}
          onClick={handleSwitchToPatient}
          sx={{
            borderColor: 'secondary.light',
            color: 'text.secondary',
            textTransform: 'none',
            fontWeight: 500,
            borderRadius: 2,
            mb: 1,
            '&:hover': {
              borderColor: 'primary.main',
              color: 'primary.main',
              bgcolor: 'rgba(33,150,243,0.04)',
            },
          }}
        >
          切换到患者端
        </Button>
        <Button
          fullWidth
          variant="text"
          startIcon={<LogoutIcon />}
          onClick={handleLogout}
          sx={{
            color: 'text.secondary',
            textTransform: 'none',
            fontWeight: 500,
            borderRadius: 2,
            '&:hover': { color: '#E53935', bgcolor: 'rgba(229,57,53,0.04)' },
          }}
        >
          退出登录
        </Button>
      </Box>
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
          color: 'text.primary',
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
              (i) =>
                i.path === location.pathname ||
                (i.path !== '/doctor' && location.pathname.startsWith(i.path))
            )?.label || '医生工作台'}
          </Typography>
          <Box sx={flexRowGap2}>
            <Tooltip title={user?.name || user?.email || '医生'}>
              <Box sx={flexRowGap1}>
                <Avatar
                  sx={{
                    width: 36,
                    height: 36,
                    bgcolor: 'primary.main',
                    fontSize: '0.875rem',
                    fontWeight: 600,
                  }}
                >
                  {(user?.name || user?.email || 'D')[0].toUpperCase()}
                </Avatar>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, display: { xs: 'none', sm: 'block' } }}>
                  {user?.name || user?.email || '医生'}
                </Typography>
              </Box>
            </Tooltip>
            <Button
              variant="outlined"
              size="small"
              startIcon={<LogoutIcon fontSize="small" />}
              onClick={handleLogout}
              sx={{
                textTransform: 'none',
                borderColor: 'secondary.light',
                color: 'text.secondary',
                borderRadius: 2,
                '&:hover': {
                  borderColor: '#E53935',
                  color: '#E53935',
                  bgcolor: 'rgba(229,57,53,0.04)',
                },
              }}
            >
              退出
            </Button>
          </Box>
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ width: { md: DRAWER_WIDTH }, flexShrink: { md: 0 } }}>
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