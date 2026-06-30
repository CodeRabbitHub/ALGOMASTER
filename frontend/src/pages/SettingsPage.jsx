import React, { useState, useEffect } from 'react'
import {
  Box, Typography, Paper, TextField, Button, Stack,
  Alert, Divider, Chip, CircularProgress, IconButton,
  InputAdornment, Tooltip,
} from '@mui/material'
import {
  Key, Save, CheckCircle, Info, Delete, Visibility,
  VisibilityOff, SmartToy,
} from '@mui/icons-material'
import { getOpenAIKeyStatus, setOpenAIKey, deleteOpenAIKey } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

export default function SettingsPage() {
  const { user } = useAuth()

  // ── OpenAI key state ─────────────────────────────────────────────────────
  const [keyStatus, setKeyStatus]   = useState(null)   // { configured, source }
  const [keyInput, setKeyInput]     = useState('')
  const [showKey, setShowKey]       = useState(false)
  const [saving, setSaving]         = useState(false)
  const [deleting, setDeleting]     = useState(false)
  const [feedback, setFeedback]     = useState(null)   // { severity, msg }

  useEffect(() => {
    getOpenAIKeyStatus()
      .then(setKeyStatus)
      .catch(() => setKeyStatus({ configured: false, source: 'none' }))
  }, [])

  const flash = (severity, msg) => {
    setFeedback({ severity, msg })
    setTimeout(() => setFeedback(null), 5000)
  }

  const handleSave = async () => {
    const trimmed = keyInput.trim()
    if (!trimmed) { flash('error', 'Enter an API key first.'); return }
    setSaving(true)
    try {
      const result = await setOpenAIKey(trimmed)
      setKeyStatus(result)
      setKeyInput('')
      flash('success', 'API key saved and activated — AI features are ready.')
    } catch (err) {
      flash('error', err?.response?.data?.detail || 'Failed to save key.')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    try {
      await deleteOpenAIKey()
      setKeyStatus({ configured: false, source: 'none' })
      flash('info', 'API key removed. AI features are now disabled.')
    } catch (err) {
      flash('error', err?.response?.data?.detail || 'Failed to remove key.')
    } finally {
      setDeleting(false)
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <Box sx={{ p: 3, maxWidth: 680 }}>
      <Typography variant="h4" fontWeight={700} mb={3}>Settings</Typography>

      {/* ── OpenAI API Key ───────────────────────────────────────────────── */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Stack direction="row" gap={1} alignItems="center" mb={1}>
          <SmartToy sx={{ color: 'primary.main' }} />
          <Typography variant="h6" fontWeight={600}>OpenAI API Key</Typography>
          {keyStatus === null && <CircularProgress size={14} sx={{ ml: 1 }} />}
          {keyStatus?.configured && (
            <Chip
              icon={<CheckCircle />}
              label={keyStatus.source === 'database' ? 'Configured (DB)' : 'Configured (env)'}
              color="success"
              size="small"
              sx={{ ml: 1 }}
            />
          )}
          {keyStatus && !keyStatus.configured && (
            <Chip label="Not configured" color="warning" size="small" sx={{ ml: 1 }} />
          )}
        </Stack>

        <Typography variant="body2" color="text.secondary" mb={2.5}>
          Required for AI hints, mistake explainer, code review, weekly reports, and study plans.
          The key is encrypted with AES-256 before storage — it is never stored in plaintext.
        </Typography>

        {/* Input row */}
        <Stack direction="row" gap={1} alignItems="flex-start" mb={2}>
          <TextField
            fullWidth
            type={showKey ? 'text' : 'password'}
            label={keyStatus?.configured ? 'Enter new key to replace' : 'OpenAI API Key'}
            placeholder="sk-proj-..."
            value={keyInput}
            onChange={e => setKeyInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSave()}
            size="small"
            InputProps={{
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    size="small"
                    onClick={() => setShowKey(v => !v)}
                    edge="end"
                    tabIndex={-1}
                  >
                    {showKey ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                  </IconButton>
                </InputAdornment>
              ),
            }}
          />
          <Button
            variant="contained"
            startIcon={saving ? <CircularProgress size={14} color="inherit" /> : <Save />}
            onClick={handleSave}
            disabled={saving || !keyInput.trim()}
            sx={{ whiteSpace: 'nowrap', minWidth: 100 }}
          >
            {saving ? 'Saving…' : 'Save Key'}
          </Button>
          {keyStatus?.configured && keyStatus?.source === 'database' && (
            <Tooltip title="Remove stored key">
              <span>
                <IconButton
                  color="error"
                  onClick={handleDelete}
                  disabled={deleting}
                  size="medium"
                >
                  {deleting ? <CircularProgress size={18} color="inherit" /> : <Delete />}
                </IconButton>
              </span>
            </Tooltip>
          )}
        </Stack>

        {feedback && (
          <Alert severity={feedback.severity} sx={{ mb: 1 }}>{feedback.msg}</Alert>
        )}

        <Alert severity="info" icon={<Key fontSize="small" />}>
          Get your key at{' '}
          <a href="https://platform.openai.com/api-keys" target="_blank" rel="noreferrer"
             style={{ color: 'inherit' }}>
            platform.openai.com/api-keys
          </a>.
          {' '}The key activates immediately — no Docker restart needed.
        </Alert>
      </Paper>

      {/* ── About ────────────────────────────────────────────────────────── */}
      <Paper sx={{ p: 3 }}>
        <Stack direction="row" gap={1} alignItems="center" mb={2}>
          <Info sx={{ color: 'text.secondary' }} />
          <Typography variant="h6" fontWeight={600}>About</Typography>
        </Stack>
        <Divider sx={{ mb: 2 }} />
        {[
          ['Signed in as', `${user?.username} (${user?.email})`],
          ['Platform', 'AlgoMaster v1.0'],
          ['Problems', '600 across 59 categories'],
          ['Database', 'PostgreSQL + TimescaleDB'],
          ['Code Runner', 'Sandboxed Python 3.12'],
          ['AI Model', 'GPT-4o'],
        ].map(([k, v]) => (
          <Stack key={k} direction="row" justifyContent="space-between" py={0.5}>
            <Typography variant="body2" color="text.secondary">{k}</Typography>
            <Typography variant="body2" sx={{ textAlign: 'right' }}>{v}</Typography>
          </Stack>
        ))}
      </Paper>
    </Box>
  )
}
