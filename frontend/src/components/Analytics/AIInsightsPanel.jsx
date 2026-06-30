import React, { useState, useEffect } from 'react'
import {
  Box, Paper, Typography, Button, Stack, Chip, TextField,
  CircularProgress, Alert, Divider, Tab, Tabs,
} from '@mui/material'
import {
  AutoAwesome, CalendarMonth, BugReport, Send, History,
} from '@mui/icons-material'
import { getAIInsight, getAIHistory } from '../../api/client'

const INSIGHT_TYPES = [
  { key: 'weekly_report', label: 'Weekly Report', icon: <CalendarMonth />, color: '#58a6ff' },
  { key: 'study_plan', label: 'Study Plan', icon: <AutoAwesome />, color: '#3fb950' },
  { key: 'mistake_analysis', label: 'Mistake Analysis', icon: <BugReport />, color: '#f85149' },
]

export default function AIInsightsPanel() {
  const [tab, setTab] = useState(0)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [chatMsg, setChatMsg] = useState('')
  const [history, setHistory] = useState([])
  const [histLoading, setHistLoading] = useState(false)

  const handleGenerate = async (type) => {
    setLoading(true)
    setResult(null)
    try {
      const data = await getAIInsight(type)
      setResult({ type, content: data.content, tokens: data.tokens_used })
    } catch {
      setResult({ type, content: 'Error: Could not connect to AI service.', tokens: 0 })
    } finally {
      setLoading(false)
    }
  }

  const handleChat = async () => {
    if (!chatMsg.trim()) return
    setLoading(true)
    setResult(null)
    const msg = chatMsg
    setChatMsg('')
    try {
      const data = await getAIInsight('chat', { message: msg })
      setResult({ type: 'chat', content: data.content, tokens: data.tokens_used, question: msg })
    } catch {
      setResult({ type: 'chat', content: 'Error: Could not connect to AI service.', tokens: 0 })
    } finally {
      setLoading(false)
    }
  }

  const loadHistory = async () => {
    setHistLoading(true)
    try {
      const h = await getAIHistory(20)
      setHistory(h)
    } catch {}
    finally { setHistLoading(false) }
  }

  return (
    <Box>
      <Tabs value={tab} onChange={(_, v) => { setTab(v); if (v === 1) loadHistory() }} sx={{ mb: 2 }}>
        <Tab label="Generate Insights" />
        <Tab label="History" icon={<History fontSize="small" />} iconPosition="start" />
      </Tabs>

      {tab === 0 && (
        <Stack gap={2}>
          {/* Quick actions */}
          <Stack direction="row" gap={2} flexWrap="wrap">
            {INSIGHT_TYPES.map(({ key, label, icon, color }) => (
              <Paper key={key} sx={{ p: 2, minWidth: 180, flex: 1 }}>
                <Stack gap={1}>
                  <Stack direction="row" gap={1} alignItems="center">
                    <Box sx={{ color }}>{icon}</Box>
                    <Typography variant="subtitle2" fontWeight={600}>{label}</Typography>
                  </Stack>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={() => handleGenerate(key)}
                    disabled={loading}
                    sx={{ borderColor: color, color, '&:hover': { borderColor: color, bgcolor: `${color}11` } }}
                  >
                    Generate
                  </Button>
                </Stack>
              </Paper>
            ))}
          </Stack>

          {/* Chat */}
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle2" fontWeight={600} mb={1}>
              Ask Your Coach
            </Typography>
            <Stack direction="row" gap={1}>
              <TextField
                fullWidth
                size="small"
                value={chatMsg}
                onChange={e => setChatMsg(e.target.value)}
                placeholder="e.g. Why am I struggling with graphs?"
                onKeyDown={e => e.key === 'Enter' && handleChat()}
              />
              <Button
                variant="contained"
                onClick={handleChat}
                disabled={loading || !chatMsg.trim()}
                startIcon={loading ? <CircularProgress size={14} /> : <Send />}
              >
                Ask
              </Button>
            </Stack>
          </Paper>

          {/* Result */}
          {loading && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, p: 2 }}>
              <CircularProgress size={20} />
              <Typography color="text.secondary">Generating AI insight…</Typography>
            </Box>
          )}

          {result && (
            <Paper sx={{ p: 2.5 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1.5}>
                <Stack direction="row" gap={1} alignItems="center">
                  <AutoAwesome sx={{ color: '#d29922', fontSize: 18 }} />
                  <Typography variant="subtitle2" fontWeight={600}>
                    {result.question ? `Q: "${result.question}"` : result.type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                  </Typography>
                </Stack>
                {result.tokens > 0 && (
                  <Chip size="small" label={`${result.tokens} tokens`} variant="outlined" />
                )}
              </Stack>
              <Divider sx={{ mb: 1.5 }} />
              {result.content.startsWith('⚠️') ? (
                <Alert severity="warning">{result.content}</Alert>
              ) : (
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
                  {result.content}
                </Typography>
              )}
            </Paper>
          )}
        </Stack>
      )}

      {tab === 1 && (
        <Box>
          {histLoading
            ? <CircularProgress />
            : history.length === 0
            ? <Typography color="text.secondary">No AI insights generated yet.</Typography>
            : history.map((h, i) => (
              <Paper key={h.id} sx={{ p: 2, mb: 1.5 }}>
                <Stack direction="row" justifyContent="space-between" mb={1}>
                  <Chip size="small" label={h.insight_type.replace(/_/g, ' ')} />
                  <Typography variant="caption" color="text.secondary">
                    {new Date(h.generated_at).toLocaleString()}
                  </Typography>
                </Stack>
                <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap',
                  maxHeight: 120, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {h.content}
                </Typography>
              </Paper>
            ))}
        </Box>
      )}
    </Box>
  )
}
