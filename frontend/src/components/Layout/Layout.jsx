import React, { useEffect, useState } from 'react'
import {
  Box, Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText,
  Typography, Divider, Avatar, Stack, Tooltip, IconButton, Badge, Chip,
} from '@mui/material'
import {
  FormatListBulleted, BarChart, Code, Settings, Logout, Whatshot, EmojiEvents,
} from '@mui/icons-material'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { getOverviewStats } from '../../api/client'
import api from '../../api/client'

const DRAWER_WIDTH = 220

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

  useEffect(() => {
    if (!token) return
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
    getOverviewStats().then(s => setSidebarStats(s)).catch(() => {})
  }, [token])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const unsolved = sidebarStats
    ? Math.max(0, sidebarStats.total_problems - sidebarStats.total_solved)
    : null
  const streak = sidebarStats?.current_streak ?? 0

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
          {NAV.map(({ label, icon, path }) => {
            const showBadge = path === '/tracker' && unsolved !== null && unsolved > 0
            return (
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
                  <ListItemIcon sx={{ minWidth: 36 }}>
                    {showBadge
                      ? <Badge badgeContent={unsolved > 99 ? '99+' : unsolved}
                          sx={{ '& .MuiBadge-badge': { bgcolor: '#238636', color: '#fff', fontSize: 10 } }}>
                          {icon}
                        </Badge>
                      : icon}
                  </ListItemIcon>
                  <ListItemText primary={label} primaryTypographyProps={{ fontSize: 14 }} />
                </ListItemButton>
              </ListItem>
            )
          })}
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
      </Drawer>

      {/* Main content */}
      <Box component="main" sx={{ flexGrow: 1, overflow: 'auto', bgcolor: 'background.default' }}>
        {children}
      </Box>
    </Box>
  )
}
