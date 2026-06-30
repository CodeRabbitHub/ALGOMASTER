import React from 'react'
import {
  Box, Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText,
  Typography, Divider, Avatar, Stack, Tooltip, IconButton,
} from '@mui/material'
import {
  FormatListBulleted, BarChart, Code, Settings, Logout,
} from '@mui/icons-material'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

const DRAWER_WIDTH = 220

const NAV = [
  { label: 'Problem Tracker', icon: <FormatListBulleted />, path: '/tracker' },
  { label: 'Analytics', icon: <BarChart />, path: '/analytics' },
  { label: 'Settings', icon: <Settings />, path: '/settings' },
]

export default function Layout({ children }) {
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const { user, logout } = useAuth()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
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
      </Drawer>

      {/* Main content */}
      <Box component="main" sx={{ flexGrow: 1, overflow: 'auto', bgcolor: 'background.default' }}>
        {children}
      </Box>
    </Box>
  )
}
