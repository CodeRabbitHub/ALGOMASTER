import React, { useEffect, useState } from 'react'
import {
  Box, Typography, Tabs, Tab, Grid, Paper, Stack, Chip,
  CircularProgress, Avatar, Skeleton, Drawer, IconButton,
  ToggleButtonGroup, ToggleButton, Tooltip,
} from '@mui/material'
import {
  EmojiEvents, Whatshot, Speed, Psychology,
  AutoAwesome, Close, CalendarViewMonth, ShowChart, BarChart as BarChartIcon,
} from '@mui/icons-material'
import {
  LineChart, Line, BarChart, Bar, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, XAxis, YAxis, Tooltip as ReTooltip, CartesianGrid,
  ResponsiveContainer, Legend, Cell,
} from 'recharts'
import {
  getOverviewStats, getDailyStats, getTopicMastery,
  getErrorPatterns,
} from '../api/client'
import api from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import GitHubHeatmap from '../components/Analytics/GitHubHeatmap'
import AIInsightsPanel from '../components/Analytics/AIInsightsPanel'
import { BugReport } from '@mui/icons-material'

const DIFF_COLORS = { Easy: '#3fb950', Medium: '#d29922', Hard: '#f85149' }

function StatCard({ icon, label, value, sub, color = 'primary.main' }) {
  return (
    <Paper sx={{ p: 2.5 }}>
      <Stack direction="row" alignItems="center" gap={1.5}>
        <Avatar sx={{ bgcolor: `${color}22`, color }}>
          {icon}
        </Avatar>
        <Box>
          <Typography variant="h5" fontWeight={700}>{value}</Typography>
          <Typography variant="body2" color="text.secondary">{label}</Typography>
          {sub && <Typography variant="caption" color="text.secondary">{sub}</Typography>}
        </Box>
      </Stack>
    </Paper>
  )
}

export default function AnalyticsPage() {
  const { token } = useAuth()
  const [tab, setTab] = useState(0)
  const [curveView, setCurveView] = useState('progress')   // 'progress' | 'time' | 'activity'
  const [stats, setStats] = useState(null)
  const [daily, setDaily] = useState([])
  const [topics, setTopics] = useState([])
  const [errors, setErrors] = useState([])
  const [loading, setLoading] = useState(true)
  const [aiOpen, setAiOpen] = useState(false)

  useEffect(() => {
    if (!token) return
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
    Promise.all([
      getOverviewStats(),
      getDailyStats(90),
      getTopicMastery(),
      getErrorPatterns(),
    ]).then(([s, d, t, e]) => {
      setStats(s)
      setDaily(d.map(r => ({ ...r, day: r.day?.slice(0, 10) })))
      setTopics(t)
      setErrors(e)
    }).catch(console.error).finally(() => setLoading(false))
  }, [token])

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <Skeleton variant="text" width={240} height={44} sx={{ mb: 3 }} />
        <Grid container spacing={2} mb={3}>
          {[...Array(4)].map((_, i) => (
            <Grid item xs={12} sm={6} md={3} key={i}>
              <Paper sx={{ p: 2.5 }}>
                <Stack direction="row" alignItems="center" gap={1.5}>
                  <Skeleton variant="circular" width={40} height={40} />
                  <Box sx={{ flex: 1 }}>
                    <Skeleton variant="text" width="60%" height={32} />
                    <Skeleton variant="text" width="80%" height={20} />
                  </Box>
                </Stack>
              </Paper>
            </Grid>
          ))}
        </Grid>
        <Skeleton variant="rounded" height={40} width={480} sx={{ mb: 3 }} />
        <Paper sx={{ p: 2 }}>
          <Skeleton variant="rounded" height={300} />
        </Paper>
      </Box>
    )
  }

  const radarData = topics.slice(0, 12).map(t => ({
    category: t.category.length > 14 ? t.category.slice(0, 14) + '…' : t.category,
    mastery: t.mastery_score,
  }))

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Stack direction="row" alignItems="center" justifyContent="space-between" mb={3}>
        <Typography variant="h4" fontWeight={700}>Learning Analytics</Typography>
        <Tooltip title="AI Coach — personalized analysis of your learning data">
          <Box
            onClick={() => setAiOpen(true)}
            sx={{
              display: 'flex', alignItems: 'center', gap: 1, px: 2, py: 1,
              borderRadius: 2, cursor: 'pointer', border: '1px solid',
              borderColor: '#d2992244', bgcolor: '#d2992211',
              color: '#d29922', fontWeight: 600, fontSize: 14,
              '&:hover': { bgcolor: '#d2992222' },
              transition: 'background 0.2s',
            }}
          >
            <AutoAwesome sx={{ fontSize: 18 }} />
            AI Coach
          </Box>
        </Tooltip>
      </Stack>

      {/* KPI cards */}
      {stats && (
        <Grid container spacing={2} mb={3}>
          <Grid item xs={12} sm={6} md={3}>
            <StatCard icon={<EmojiEvents />} label="Problems Solved"
              value={`${stats.total_solved} / ${stats.total_problems}`}
              sub={`${((stats.total_solved / Math.max(stats.total_problems, 1)) * 100).toFixed(1)}% complete`}
              color="#58a6ff" />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <StatCard icon={<Whatshot />} label="Current Streak"
              value={`${stats.current_streak}d`}
              sub={`Longest: ${stats.longest_streak}d`}
              color="#f85149" />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <StatCard icon={<Speed />} label="First-Attempt Rate"
              value={`${stats.first_attempt_success_rate}%`}
              sub={`Avg ${stats.avg_attempts_per_problem} attempts/problem`}
              color="#3fb950" />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <StatCard icon={<Psychology />} label="7-day Velocity"
              value={`${stats.solve_velocity_7d}/day`}
              sub={`30d: ${stats.solve_velocity_30d}/day`}
              color="#d29922" />
          </Grid>
        </Grid>
      )}

      {/* Tabs — 3 tabs */}
      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{ mb: 3, borderBottom: '1px solid', borderColor: 'divider' }}
      >
        <Tab label="Learning Curve" />
        <Tab label="Topic Mastery" />
        <Tab label="Error Patterns" />
      </Tabs>

      {/* ── Tab 0: Learning Curve ───────────────────────────────── */}
      {tab === 0 && (
        <Box>
          {/* Sub-view toggle */}
          <Stack direction="row" alignItems="center" justifyContent="flex-end" mb={2}>
            <ToggleButtonGroup
              value={curveView}
              exclusive
              onChange={(_, v) => v && setCurveView(v)}
              size="small"
            >
              <ToggleButton value="progress">
                <Tooltip title="Progress over time">
                  <Stack direction="row" alignItems="center" gap={0.5} sx={{ fontSize: 13 }}>
                    <ShowChart sx={{ fontSize: 16 }} /> Progress
                  </Stack>
                </Tooltip>
              </ToggleButton>
              <ToggleButton value="time">
                <Tooltip title="Time spent per day">
                  <Stack direction="row" alignItems="center" gap={0.5} sx={{ fontSize: 13 }}>
                    <BarChartIcon sx={{ fontSize: 16 }} /> Time
                  </Stack>
                </Tooltip>
              </ToggleButton>
              <ToggleButton value="activity">
                <Tooltip title="Activity heatmap">
                  <Stack direction="row" alignItems="center" gap={0.5} sx={{ fontSize: 13 }}>
                    <CalendarViewMonth sx={{ fontSize: 16 }} /> Activity
                  </Stack>
                </Tooltip>
              </ToggleButton>
            </ToggleButtonGroup>
          </Stack>

          {curveView === 'progress' && (
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle1" fontWeight={600} mb={2}>
                    Daily Solves (Last 90 Days)
                  </Typography>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={daily}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                      <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#8b949e' }}
                        tickFormatter={v => v?.slice(5)} />
                      <YAxis tick={{ fontSize: 11, fill: '#8b949e' }} />
                      <ReTooltip contentStyle={{ background: '#161b22', border: '1px solid #30363d' }}
                        labelStyle={{ color: '#e6edf3' }} />
                      <Legend />
                      <Line type="monotone" dataKey="solved" stroke="#3fb950" dot={false} name="Solved" strokeWidth={2} />
                      <Line type="monotone" dataKey="total_attempts" stroke="#58a6ff" dot={false} name="Attempts" strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </Paper>
              </Grid>
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 2 }}>
                  <Typography variant="subtitle1" fontWeight={600} mb={2}>Difficulty Breakdown</Typography>
                  {stats && (
                    <Stack gap={1.5} mt={1}>
                      {['easy_solved', 'medium_solved', 'hard_solved'].map((key, i) => {
                        const label = ['Easy', 'Medium', 'Hard'][i]
                        const totalKey = key.replace('_solved', '_total')
                        const val = stats[key] || 0
                        const total = stats[totalKey] || 0
                        const pct = total ? (val / total) * 100 : 0
                        return (
                          <Box key={key}>
                            <Stack direction="row" justifyContent="space-between" mb={0.5}>
                              <Typography variant="body2" sx={{ color: DIFF_COLORS[label] }}>{label}</Typography>
                              <Typography variant="body2" color="text.secondary">{val} / {total}</Typography>
                            </Stack>
                            <Box sx={{ height: 8, bgcolor: '#21262d', borderRadius: 4, overflow: 'hidden' }}>
                              <Box sx={{ height: '100%', width: `${pct}%`, bgcolor: DIFF_COLORS[label], borderRadius: 4, transition: 'width 1s' }} />
                            </Box>
                          </Box>
                        )
                      })}
                    </Stack>
                  )}
                </Paper>
              </Grid>
            </Grid>
          )}

          {curveView === 'time' && (
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle1" fontWeight={600} mb={2}>Time Spent (minutes/day — last 30 days)</Typography>
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={daily.slice(-30)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                  <XAxis dataKey="day" tick={{ fontSize: 10, fill: '#8b949e' }} tickFormatter={v => v?.slice(5)} />
                  <YAxis tick={{ fontSize: 11, fill: '#8b949e' }} />
                  <ReTooltip
                    contentStyle={{ background: '#161b22', border: '1px solid #30363d' }}
                    formatter={v => [`${Math.round(v / 60)} min`]}
                  />
                  <Bar dataKey="total_time_secs" fill="#58a6ff" name="Time" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </Paper>
          )}

          {curveView === 'activity' && (
            <Paper sx={{ p: 3 }}>
              <Typography variant="subtitle1" fontWeight={600} mb={2}>Activity Heatmap</Typography>
              <GitHubHeatmap data={daily} />
            </Paper>
          )}
        </Box>
      )}

      {/* ── Tab 1: Topic Mastery ─────────────────────────────────── */}
      {tab === 1 && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={5}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle1" fontWeight={600} mb={1}>Mastery Radar</Typography>
              <ResponsiveContainer width="100%" height={360}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#21262d" />
                  <PolarAngleAxis dataKey="category" tick={{ fontSize: 10, fill: '#8b949e' }} />
                  <Radar name="Mastery" dataKey="mastery" stroke="#58a6ff" fill="#58a6ff" fillOpacity={0.25} />
                  <ReTooltip contentStyle={{ background: '#161b22', border: '1px solid #30363d' }}
                    formatter={v => [`${v.toFixed(0)}%`, 'Mastery']} />
                </RadarChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>
          <Grid item xs={12} md={7}>
            <Paper sx={{ p: 2, maxHeight: 420, overflow: 'auto' }}>
              <Typography variant="subtitle1" fontWeight={600} mb={1}>Per-Topic Breakdown</Typography>
              <Stack gap={1}>
                {topics.map(t => (
                  <Box key={t.category}>
                    <Stack direction="row" justifyContent="space-between" mb={0.5}>
                      <Typography variant="body2">{t.category}</Typography>
                      <Stack direction="row" gap={1} alignItems="center">
                        <Typography variant="caption" color="text.secondary">
                          {t.solved}/{t.total_problems}
                        </Typography>
                        <Chip size="small" label={`${t.mastery_score?.toFixed(0)}%`}
                          sx={{ fontSize: 10, bgcolor: t.mastery_score > 60 ? '#3fb95022' : '#f8514922',
                            color: t.mastery_score > 60 ? 'success.main' : 'error.main' }} />
                      </Stack>
                    </Stack>
                    <Box sx={{ height: 6, bgcolor: '#21262d', borderRadius: 3, overflow: 'hidden' }}>
                      <Box sx={{ height: '100%', width: `${t.mastery_score || 0}%`, borderRadius: 3,
                        bgcolor: t.mastery_score > 60 ? '#3fb950' : t.mastery_score > 30 ? '#d29922' : '#f85149',
                        transition: 'width 0.8s' }} />
                    </Box>
                  </Box>
                ))}
              </Stack>
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* ── Tab 2: Error Patterns ────────────────────────────────── */}
      {tab === 2 && (
        <Grid container spacing={2}>
          <Grid item xs={12} md={7}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle1" fontWeight={600} mb={2}>Error Frequency</Typography>
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={errors} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                  <XAxis type="number" tick={{ fontSize: 11, fill: '#8b949e' }} />
                  <YAxis dataKey="error_category" type="category" width={130} tick={{ fontSize: 11, fill: '#8b949e' }} />
                  <ReTooltip contentStyle={{ background: '#161b22', border: '1px solid #30363d' }} />
                  <Bar dataKey="count" fill="#f85149" radius={[0, 4, 4, 0]} name="Count" />
                </BarChart>
              </ResponsiveContainer>
            </Paper>
          </Grid>
          <Grid item xs={12} md={5}>
            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle1" fontWeight={600} mb={2}>Error Summary</Typography>
              {errors.length === 0
                ? <Typography color="text.secondary">No errors recorded yet. Start solving!</Typography>
                : errors.map((e, i) => (
                  <Stack key={i} direction="row" justifyContent="space-between" py={0.75}
                    sx={{ borderBottom: '1px solid #21262d' }}>
                    <Stack direction="row" gap={1} alignItems="center">
                      <BugReport sx={{ fontSize: 14, color: 'error.main' }} />
                      <Typography variant="body2">{e.error_category}</Typography>
                    </Stack>
                    <Chip size="small" label={e.count} color="error" variant="outlined" />
                  </Stack>
                ))}
            </Paper>
          </Grid>
        </Grid>
      )}

      {/* ── AI Coach Drawer ──────────────────────────────────────── */}
      <Drawer
        anchor="right"
        open={aiOpen}
        onClose={() => setAiOpen(false)}
        PaperProps={{
          sx: {
            width: { xs: '100%', sm: 520 },
            bgcolor: '#0d1117',
            borderLeft: '1px solid #21262d',
            p: 3,
          },
        }}
      >
        <Stack direction="row" alignItems="center" justifyContent="space-between" mb={2}>
          <Stack direction="row" alignItems="center" gap={1}>
            <AutoAwesome sx={{ color: '#d29922' }} />
            <Typography variant="h6" fontWeight={700}>AI Coach</Typography>
          </Stack>
          <IconButton onClick={() => setAiOpen(false)} size="small">
            <Close />
          </IconButton>
        </Stack>
        <Typography variant="body2" color="text.secondary" mb={2.5}>
          Personalised analysis of your actual solve history, error patterns, and topic mastery.
        </Typography>
        <AIInsightsPanel />
      </Drawer>
    </Box>
  )
}
