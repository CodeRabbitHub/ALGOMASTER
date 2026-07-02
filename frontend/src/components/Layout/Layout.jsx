import React, { useEffect, useState } from 'react'
import {
  Box, Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText,
  Typography, Divider, Avatar, Stack, Tooltip, IconButton, Chip,
  useTheme, useMediaQuery, AppBar, Toolbar,
} from '@mui/material'
import {
  FormatListBulleted, BarChart, Code, Settings, Logout, Whatshot, EmojiEvents, Menu as MenuIcon,
} from '@mui/icons-material'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { getOverviewStats } from '../../api/client'
import api from '../../api/client'

const DRAWER_WIDTH = 220
const MOBILE_APPBAR_HEIGHT = 56

const NAV = [
  { label: 'Problem Tracker',     icon: <FormatListBulleted />, path: '/tracker'   },
  { label: 'Interview Readiness', icon: <EmojiEvents />,        path: '/interview' },
  { label: 'Analytics',           icon: <BarChart />,           path: '/analytics' },
  { label: 'Settings',            icon: <Settings />,           path: '/settings'  },
]

export default function Layout({ children }) {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const { user, token, logout } = useAuth()
  const [sidebarStats, setSidebarStats] = useState(null)
  const theme = useTheme()
  // Previously the Drawer was `variant="permanent"` unconditionally, which
  // on narrow/mobile viewports permanently ate ~220px of horizontal space
  // from content that often needed all of it (e.g. the Monaco editor split
  // pane). Below the `md` breakpoint we now render a temporary, off-canvas
  // drawer toggled by a menu button instead.
  const isMobile = useMediaQuery(theme.breakpoints.down('md'))
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    if (!token) return
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
    getOverviewStats().then(s => setSidebarStats(s)).catch(() => {})
  }, [token])

  // Close the drawer automatically after navigating on mobile, otherwise
  // it stays open over the newly-loaded page.
  useEffect(() => {
    if (isMobile) setMobileOpen(false)
  }, [pathname, isMobile])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const streak = sidebarStats?.current_streak ?? 0

  const drawerContent = (
    <>
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        <Code sx={{ color: 'primary.main', fontSize: 28 }} />
        <Typography variant="h6" fontWeight={700} color="primary.main">
          AlgoMaster
        </Typography>
      </Box>
      <Divider />
      <List sx={{ mt: 1 }}>
        {NAV.map(({ label, icon, path }) => (
          <ListItem key={path} disablePadding>
            <ListItemButton
              selected={pathname.startsWith(path)}
              onClick={() => navigate(path)}
              sx={{
                mx: 1, borderRadius: 1,
                '&.Mui-selected': {
                  bgcolor: 'rgba(88,166,255,0.12)',
                  color: 'primary.main',
                  '& .MuiListItemIcon-root': { color: 'primary.main' },
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 36 }}>{icon}</ListItemIcon>
              <ListItemText primary={label} primaryTypographyProps={{ fontSize: 14 }} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>

      {/* Spacer */}
      <Box sx={{ flexGrow: 1 }} />

      {/* Streak chip */}
      {streak > 0 && (
        <Box sx={{ px: 2, pb: 1.5 }}>
          <Tooltip title={`${streak}-day solve streak — keep it up!`}>
            <Chip
              icon={<Whatshot sx={{ fontSize: '16px !important', color: '#f85149 !important' }} />}
              label={`${streak} day streak`}
              size="small"
              sx={{
                width: '100%', justifyContent: 'flex-start',
                bgcolor: '#2b0c0c', color: '#f85149',
                border: '1px solid #3d1515',
                fontWeight: 600, fontSize: 12,
                '& .MuiChip-icon': { ml: 0.5 },
              }}
            />
          </Tooltip>
        </Box>
      )}

      {/* User info + logout */}
      <Divider />
      <Box sx={{ p: 1.5 }}>
        <Stack direction="row" alignItems="center" gap={1}>
          <Avatar
            sx={{ width: 32, height: 32, bgcolor: 'primary.main', fontSize: 13, fontWeight: 700 }}
          >
            {user?.username?.[0]?.toUpperCase() || '?'}
          </Avatar>
          <Box sx={{ flexGrow: 1, minWidth: 0 }}>
            <Typography variant="body2" fontWeight={600} noWrap>
              {user?.username}
            </Typography>
            <Typography variant="caption" color="text.secondary" noWrap display="block">
              {user?.email}
            </Typography>
          </Box>
          <Tooltip title="Sign out">
            <IconButton size="small" onClick={handleLogout} sx={{ color: 'text.secondary' }}>
              <Logout fontSize="small" />
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>
    </>
  )

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* Mobile top bar with menu toggle — only rendered below `md` */}
      {isMobile && (
        <AppBar
          position="fixed"
          elevation={0}
          sx={{
            bgcolor: 'background.paper',
            borderBottom: '1px solid',
            borderColor: 'divider',
            zIndex: theme.zIndex.drawer + 1,
          }}
        >
          <Toolbar variant="dense" sx={{ minHeight: MOBILE_APPBAR_HEIGHT }}>
            <IconButton
              edge="start"
              color="inherit"
              aria-label="Open navigation menu"
              onClick={() => setMobileOpen(true)}
              sx={{ mr: 1.5, color: 'text.primary' }}
            >
              <MenuIcon />
            </IconButton>
            <Code sx={{ color: 'primary.main', fontSize: 22, mr: 1 }} />
            <Typography variant="subtitle1" fontWeight={700} color="primary.main">
              AlgoMaster
            </Typography>
          </Toolbar>
        </AppBar>
      )}

      {/* Sidebar */}
      <Drawer
        variant={isMobile ? 'temporary' : 'permanent'}
        open={isMobile ? mobileOpen : true}
        onClose={() => setMobileOpen(false)}
        ModalProps={{ keepMounted: true }} // better open perf on mobile
        sx={{
          width: isMobile ? 0 : DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            bgcolor: 'background.paper',
            borderRight: '1px solid',
            borderColor: 'divider',
            display: 'flex',
            flexDirection: 'column',
          },
        }}
      >
        {drawerContent}
      </Drawer>

      {/* Main content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          overflow: 'auto',
          bgcolor: 'background.default',
          width: isMobile ? '100%' : `calc(100% - ${DRAWER_WIDTH}px)`,
          mt: isMobile ? `${MOBILE_APPBAR_HEIGHT}px` : 0,
        }}
      >
        {children}
      </Box>
    </Box>
  )
}
