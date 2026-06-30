import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box, Paper, Typography, TextField, Button,
  Tab, Tabs, Alert, Stack, CircularProgress,
} from '@mui/material'
import { Code } from '@mui/icons-material'
import { useAuth } from '../contexts/AuthContext'

export default function LoginPage() {
  const { login, register } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState(0)          // 0 = login, 1 = register
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Login fields
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPw, setLoginPw]       = useState('')

  // Register fields
  const [regEmail, setRegEmail]     = useState('')
  const [regUser, setRegUser]       = useState('')
  const [regPw, setRegPw]           = useState('')
  const [regPw2, setRegPw2]         = useState('')

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(loginEmail, loginPw)
      navigate('/tracker')
    } catch (err) {
      setError(err?.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (e) => {
    e.preventDefault()
    setError('')
    if (regPw !== regPw2) { setError('Passwords do not match'); return }
    if (regPw.length < 6) { setError('Password must be at least 6 characters'); return }
    setLoading(true)
    try {
      await register(regEmail, regUser, regPw)
      navigate('/tracker')
    } catch (err) {
      setError(err?.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box sx={{
      minHeight: '100vh', bgcolor: 'background.default',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <Paper sx={{ p: 4, width: 400, bgcolor: '#161b22' }}>
        {/* Logo */}
        <Stack direction="row" alignItems="center" gap={1.5} mb={3} justifyContent="center">
          <Code sx={{ color: 'primary.main', fontSize: 32 }} />
          <Typography variant="h5" fontWeight={700} color="primary.main">
            AlgoMaster
          </Typography>
        </Stack>

        <Tabs value={tab} onChange={(_, v) => { setTab(v); setError('') }} sx={{ mb: 3 }}>
          <Tab label="Sign In" sx={{ flex: 1 }} />
          <Tab label="Create Account" sx={{ flex: 1 }} />
        </Tabs>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        {tab === 0 ? (
          <Box component="form" onSubmit={handleLogin}>
            <Stack gap={2}>
              <TextField
                label="Email" type="email" fullWidth required
                value={loginEmail} onChange={e => setLoginEmail(e.target.value)}
                autoFocus
              />
              <TextField
                label="Password" type="password" fullWidth required
                value={loginPw} onChange={e => setLoginPw(e.target.value)}
              />
              <Button
                type="submit" variant="contained" fullWidth size="large"
                disabled={loading}
                startIcon={loading ? <CircularProgress size={18} color="inherit" /> : null}
              >
                {loading ? 'Signing in…' : 'Sign In'}
              </Button>
            </Stack>
          </Box>
        ) : (
          <Box component="form" onSubmit={handleRegister}>
            <Stack gap={2}>
              <TextField
                label="Email" type="email" fullWidth required
                value={regEmail} onChange={e => setRegEmail(e.target.value)}
                autoFocus
              />
              <TextField
                label="Username" fullWidth required
                value={regUser} onChange={e => setRegUser(e.target.value)}
                inputProps={{ minLength: 3 }}
              />
              <TextField
                label="Password" type="password" fullWidth required
                value={regPw} onChange={e => setRegPw(e.target.value)}
                inputProps={{ minLength: 6 }}
              />
              <TextField
                label="Confirm Password" type="password" fullWidth required
                value={regPw2} onChange={e => setRegPw2(e.target.value)}
              />
              <Button
                type="submit" variant="contained" fullWidth size="large"
                disabled={loading}
                startIcon={loading ? <CircularProgress size={18} color="inherit" /> : null}
              >
                {loading ? 'Creating account…' : 'Create Account'}
              </Button>
              <Typography variant="caption" color="text.secondary" textAlign="center">
                First account created gets all existing progress data.
              </Typography>
            </Stack>
          </Box>
        )}
      </Paper>
    </Box>
  )
}
