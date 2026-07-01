import React, { useEffect, useState, useCallback } from 'react'
import {
  Box, Typography, Tabs, Tab, Paper, Stack, Chip, Grid,
  CircularProgress, Skeleton, Button, IconButton, Tooltip,
  Table, TableHead, TableRow, TableCell, TableBody,
  Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Select, MenuItem, FormControl, InputLabel,
  LinearProgress, Avatar, Divider, Alert,
} from '@mui/material'
import {
  Psychology, Speed, BugReport, RecordVoiceOver, Warning,
  School, EmojiEvents, Schedule, Add, Delete, Whatshot,
  CheckCircle, RadioButtonUnchecked, OpenInNew, Star,
} from '@mui/icons-material'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  BarChart, Bar, XAxis, YAxis, Tooltip as RTooltip, ResponsiveContainer,
  CartesianGrid, LineChart, Line, Cell,
} from 'recharts'
import { useNavigate } from 'react-router-dom'
import {
  getInterviewReadiness, getPatternStats, getReviewsDue, getAllReviews,
  completeReview, removeFromReview, listMistakes, getMistakeSummary,
  logMistake, listContests, logContest, deleteContest,
  getDSFluency, updateDSFluency, getInterviewOptions,
} from '../api/client'
import api from '../api/client'
import { useAuth } from '../contexts/AuthContext'

// ── Helpers ───────────────────────────────────────────────────────────────────
const DIFF_COLORS = { Easy: '#3fb950', Medium: '#d29922', Hard: '#f85149' }

function ScoreGauge({ score, label, color }) {
  return (
    <Box sx={{ textAlign: 'center', p: 1 }}>
      <Box sx={{ position: 'relative', display: 'inline-flex' }}>
        <CircularProgress
          variant="determinate"
          value={score}
          size={100}
          thickness={6}
          sx={{ color, '& .MuiCircularProgress-circle': { strokeLinecap: 'round' } }}
        />
        <CircularProgress
          variant="determinate"
          value={100}
          size={100}
          thickness={6}
          sx={{ color: '#21262d', position: 'absolute', left: 0, top: 0 }}
        />
        <Box sx={{
          position: 'absolute', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column',
        }}>
          <Typography variant="h6" fontWeight={700} sx={{ color, lineHeight: 1 }}>{Math.round(score)}</Typography>
          <Typography variant="caption" color="text.secondary">/ 100</Typography>
        </Box>
      </Box>
      <Typography variant="caption" color="text.secondary" display="block" mt={0.5}>{label}</Typography>
    </Box>
  )
}

function DimBar({ label, pts, max, pct }) {
  const color = pct >= 70 ? '#3fb950' : pct >= 40 ? '#d29922' : '#f85149'
  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" mb={0.5}>
        <Typography variant="body2">{label}</Typography>
        <Typography variant="body2" color="text.secondary">{pts.toFixed(1)} / {max}</Typography>
      </Stack>
      <Box sx={{ height: 6, bgcolor: '#21262d', borderRadius: 3, overflow: 'hidden' }}>
        <Box sx={{ height: '100%', width: `${pct}%`, bgcolor: color, borderRadius: 3, transition: 'width 0.8s' }} />
      </Box>
    </Box>
  )
}

// ── Tab 0: Readiness Dashboard ────────────────────────────────────────────────
function ReadinessDashboard({ readiness }) {
  if (!readiness) return <Box sx={{ py: 6, textAlign: 'center' }}><Typography color="text.secondary">No data yet. Complete some assessments after solving problems.</Typography></Box>

  const dims = Object.values(readiness.dimensions)
  const radarData = dims.map(d => ({
    subject: d.label.replace('First-Attempt ', '').replace(' Recognition', ''),
    score: Math.round(d.pct),
  }))

  return (
    <Grid container spacing={2.5}>
      {/* Big score */}
      <Grid item xs={12} md={4}>
        <Paper sx={{ p: 3, textAlign: 'center', height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <ScoreGauge score={readiness.total_score} label="Overall" color={readiness.label_color} />
          <Chip
            label={readiness.label}
            sx={{ mt: 1.5, bgcolor: `${readiness.label_color}22`, color: readiness.label_color, fontWeight: 700, border: `1px solid ${readiness.label_color}` }}
          />
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1.5, maxWidth: 200, textAlign: 'center' }}>
            Based on your self-assessments, solve speed, and topic coverage.
          </Typography>
        </Paper>
      </Grid>

      {/* Radar */}
      <Grid item xs={12} md={4}>
        <Paper sx={{ p: 2 }}>
          <Typography variant="subtitle2" fontWeight={600} mb={1}>Skill Radar</Typography>
          <ResponsiveContainer width="100%" height={220}>
            <RadarChart data={radarData} margin={{ top: 10, right: 20, bottom: 10, left: 20 }}>
              <PolarGrid stroke="#21262d" />
              <PolarAngleAxis dataKey="subject" tick={{ fontSize: 9, fill: '#8b949e' }} />
              <Radar dataKey="score" stroke="#58a6ff" fill="#58a6ff" fillOpacity={0.22} />
              <RTooltip contentStyle={{ bgcolor: '#161b22', border: '1px solid #30363d' }}
                formatter={v => [`${v}%`]} />
            </RadarChart>
          </ResponsiveContainer>
        </Paper>
      </Grid>

      {/* Dimension breakdown */}
      <Grid item xs={12} md={4}>
        <Paper sx={{ p: 2 }}>
          <Typography variant="subtitle2" fontWeight={600} mb={2}>Dimension Breakdown</Typography>
          <Stack gap={1.5}>
            {dims.map(d => (
              <DimBar key={d.label} label={d.label} pts={d.points} max={d.max} pct={d.pct} />
            ))}
          </Stack>
        </Paper>
      </Grid>

      {/* Detail cards */}
      {dims.map(d => (
        <Grid item xs={12} sm={6} md={4} key={d.label}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
              <Typography variant="body2" fontWeight={600}>{d.label}</Typography>
              <Chip size="small" label={`${d.pct}%`} sx={{
                bgcolor: d.pct >= 70 ? '#0d2b15' : d.pct >= 40 ? '#2b1f07' : '#2b0c0c',
                color:   d.pct >= 70 ? '#3fb950' : d.pct >= 40 ? '#d29922' : '#f85149',
                fontSize: 11, fontWeight: 700,
              }} />
            </Stack>
            <Typography variant="caption" color="text.secondary" mt={0.5} display="block">
              {d.detail}
            </Typography>
          </Paper>
        </Grid>
      ))}
    </Grid>
  )
}

// ── Tab 1: Pattern Recognition ────────────────────────────────────────────────
function PatternTab({ patterns }) {
  if (!patterns.length) return <Box sx={{ py: 6, textAlign: 'center' }}><Typography color="text.secondary">No pattern data yet. Run assessments after solving.</Typography></Box>

  const chartData = patterns.map(p => ({
    name: p.pattern.replace(' / ', '/').replace(' & ', '&'),
    accuracy: p.accuracy_pct,
    time: Math.round(p.avg_time_secs / 60 * 10) / 10,
    total: p.total,
  }))

  return (
    <Grid container spacing={2}>
      <Grid item xs={12} md={7}>
        <Paper sx={{ p: 2 }}>
          <Typography variant="subtitle2" fontWeight={600} mb={2}>Recognition Accuracy by Pattern (%)</Typography>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={chartData} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
              <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11, fill: '#8b949e' }} tickFormatter={v => `${v}%`} />
              <YAxis dataKey="name" type="category" width={130} tick={{ fontSize: 10, fill: '#8b949e' }} />
              <RTooltip
                contentStyle={{ bgcolor: '#161b22', border: '1px solid #30363d' }}
                formatter={(v, name) => [name === 'accuracy' ? `${v}%` : `${v}m`, name === 'accuracy' ? 'Accuracy' : 'Avg Time']}
              />
              <Bar dataKey="accuracy" radius={[0, 4, 4, 0]} name="accuracy">
                {chartData.map((d, i) => (
                  <Cell key={i} fill={d.accuracy >= 80 ? '#3fb950' : d.accuracy >= 50 ? '#d29922' : '#f85149'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Paper>
      </Grid>
      <Grid item xs={12} md={5}>
        <Paper sx={{ p: 2, maxHeight: 380, overflow: 'auto' }}>
          <Typography variant="subtitle2" fontWeight={600} mb={1}>Avg Identification Time</Typography>
          <Stack gap={0}>
            {patterns.map(p => (
              <Box key={p.pattern} sx={{ py: 1, borderBottom: '1px solid #21262d' }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center">
                  <Typography variant="body2">{p.pattern}</Typography>
                  <Stack direction="row" gap={1} alignItems="center">
                    <Chip size="small" label={`${p.total} uses`} sx={{ fontSize: 10, bgcolor: '#21262d', color: '#8b949e' }} />
                    <Chip size="small"
                      label={p.avg_time_secs <= 120 ? `${p.avg_time_secs}s ✓` : `${Math.round(p.avg_time_secs/60)}m`}
                      sx={{
                        fontSize: 10, fontWeight: 600,
                        bgcolor: p.avg_time_secs <= 120 ? '#0d2b15' : '#2b1f07',
                        color:   p.avg_time_secs <= 120 ? '#3fb950' : '#d29922',
                      }}
                    />
                  </Stack>
                </Stack>
              </Box>
            ))}
          </Stack>
        </Paper>
      </Grid>
    </Grid>
  )
}

// ── Tab 2: Memory Retention (Spaced Repetition) ───────────────────────────────
function MemoryTab({ dueReviews, allReviews, onComplete, onRemove, navigate }) {
  const [quality, setQuality] = useState({})

  const handleComplete = (problemId) => {
    const q = quality[problemId] ?? 4
    onComplete(problemId, q)
  }

  const qualityLabels = { 0: 'Forgot', 1: 'Barely', 2: 'Hard', 3: 'Effort', 4: 'Good', 5: 'Perfect' }
  const qualityColors = { 0: '#f85149', 1: '#f85149', 2: '#d29922', 3: '#d29922', 4: '#3fb950', 5: '#3fb950' }

  return (
    <Grid container spacing={2}>
      {/* Due today */}
      <Grid item xs={12} md={6}>
        <Paper sx={{ p: 2 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="subtitle2" fontWeight={600}>
              Due for Review
              {dueReviews.length > 0 && (
                <Chip size="small" label={dueReviews.length} sx={{ ml: 1, bgcolor: '#f85149', color: '#fff', fontSize: 10 }} />
              )}
            </Typography>
          </Stack>

          {dueReviews.length === 0 ? (
            <Box sx={{ py: 4, textAlign: 'center' }}>
              <CheckCircle sx={{ color: '#3fb950', fontSize: 40, mb: 1 }} />
              <Typography color="text.secondary">All caught up! No reviews due.</Typography>
            </Box>
          ) : (
            <Stack gap={1.5}>
              {dueReviews.map(r => (
                <Box key={r.problem_id} sx={{ p: 1.5, bgcolor: '#161b22', borderRadius: 1, border: '1px solid #30363d' }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="flex-start" mb={1}>
                    <Box>
                      <Typography
                        variant="body2" fontWeight={500} sx={{ color: '#58a6ff', cursor: 'pointer', '&:hover': { textDecoration: 'underline' } }}
                        onClick={() => navigate(`/problem/${r.problem_id}`)}
                      >
                        {r.title}
                      </Typography>
                      <Stack direction="row" gap={0.5} mt={0.25}>
                        <Chip size="small" label={r.difficulty} sx={{ fontSize: 10, bgcolor: 'transparent', color: DIFF_COLORS[r.difficulty] }} />
                        <Chip size="small" label={r.category} sx={{ fontSize: 10, bgcolor: '#21262d', color: '#8b949e' }} />
                        <Chip size="small" label={`Rep ${r.rep_count}`} sx={{ fontSize: 10, bgcolor: '#21262d', color: '#8b949e' }} />
                      </Stack>
                    </Box>
                    <Tooltip title="Remove from schedule">
                      <IconButton size="small" onClick={() => onRemove(r.problem_id)} sx={{ color: '#8b949e' }}>
                        <Delete sx={{ fontSize: 15 }} />
                      </IconButton>
                    </Tooltip>
                  </Stack>

                  {/* Quality selector */}
                  <Stack direction="row" gap={0.5} flexWrap="wrap" mb={1}>
                    {[0,1,2,3,4,5].map(q => (
                      <Chip
                        key={q} size="small" label={qualityLabels[q]} clickable
                        onClick={() => setQuality(prev => ({ ...prev, [r.problem_id]: q }))}
                        sx={{
                          fontSize: 10,
                          bgcolor: (quality[r.problem_id] ?? 4) === q ? `${qualityColors[q]}22` : '#21262d',
                          color:   (quality[r.problem_id] ?? 4) === q ? qualityColors[q] : '#8b949e',
                          border:  (quality[r.problem_id] ?? 4) === q ? `1px solid ${qualityColors[q]}` : '1px solid transparent',
                        }}
                      />
                    ))}
                  </Stack>
                  <Button size="small" variant="outlined" fullWidth onClick={() => handleComplete(r.problem_id)}
                    sx={{ fontSize: 12, borderColor: '#30363d', color: '#58a6ff' }}>
                    Mark Reviewed
                  </Button>
                </Box>
              ))}
            </Stack>
          )}
        </Paper>
      </Grid>

      {/* All scheduled */}
      <Grid item xs={12} md={6}>
        <Paper sx={{ p: 2, maxHeight: 480, overflow: 'auto' }}>
          <Typography variant="subtitle2" fontWeight={600} mb={1}>
            Full Schedule ({allReviews.length} problems)
          </Typography>
          <Stack gap={0}>
            {allReviews.map(r => {
              const due = new Date(r.next_review_at)
              const now = new Date()
              const diffDays = Math.ceil((due - now) / 86400000)
              const isPast = diffDays <= 0
              return (
                <Box key={r.problem_id} sx={{ py: 1, borderBottom: '1px solid #21262d' }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Typography variant="body2" sx={{ color: '#58a6ff', cursor: 'pointer', '&:hover': { textDecoration: 'underline' } }}
                      onClick={() => navigate(`/problem/${r.problem_id}`)}>
                      {r.title}
                    </Typography>
                    <Chip size="small"
                      label={isPast ? 'Due now' : diffDays === 1 ? 'Tomorrow' : `In ${diffDays}d`}
                      sx={{
                        fontSize: 10, fontWeight: 600,
                        bgcolor: isPast ? '#2b0c0c' : '#21262d',
                        color:   isPast ? '#f85149' : '#8b949e',
                      }}
                    />
                  </Stack>
                  <Typography variant="caption" color="text.secondary">
                    Interval: {r.interval_days}d · Ease: {r.ease_factor?.toFixed(1)} · Rep #{r.rep_count}
                  </Typography>
                </Box>
              )
            })}
            {allReviews.length === 0 && (
              <Typography color="text.secondary" variant="body2" sx={{ py: 2 }}>
                No problems scheduled. Toggle "Add to Spaced Repetition" when completing your next assessment.
              </Typography>
            )}
          </Stack>
        </Paper>
      </Grid>
    </Grid>
  )
}

// ── Tab 3: Mistake Log ────────────────────────────────────────────────────────
function MistakeTab({ mistakes, summary, onAdd, navigate }) {
  const [addOpen, setAddOpen] = useState(false)
  const [newMistake, setNewMistake] = useState({ category: '', notes: '' })
  const [options, setOptions] = useState([])

  useEffect(() => {
    getInterviewOptions().then(o => setOptions(o.mistake_categories || [])).catch(() => {})
  }, [])

  const handleAdd = () => {
    if (!newMistake.category) return
    onAdd(newMistake)
    setNewMistake({ category: '', notes: '' })
    setAddOpen(false)
  }

  const barData = summary.map(s => ({ name: s.category.replace('Missed ', 'Missed\n'), count: s.count }))

  return (
    <Grid container spacing={2}>
      <Grid item xs={12} md={5}>
        <Paper sx={{ p: 2 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="subtitle2" fontWeight={600}>Mistake Distribution</Typography>
            <Button size="small" variant="outlined" startIcon={<Add />} onClick={() => setAddOpen(true)}
              sx={{ fontSize: 12, borderColor: '#30363d', color: '#58a6ff' }}>
              Log Mistake
            </Button>
          </Stack>
          {summary.length === 0 ? (
            <Typography color="text.secondary" variant="body2">No mistakes logged yet.</Typography>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={barData} layout="vertical" margin={{ left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                <XAxis type="number" tick={{ fontSize: 11, fill: '#8b949e' }} />
                <YAxis dataKey="name" type="category" width={140} tick={{ fontSize: 10, fill: '#8b949e' }} />
                <RTooltip contentStyle={{ bgcolor: '#161b22', border: '1px solid #30363d' }} />
                <Bar dataKey="count" fill="#f85149" radius={[0, 4, 4, 0]} name="Count" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Paper>
      </Grid>

      <Grid item xs={12} md={7}>
        <Paper sx={{ p: 2, maxHeight: 380, overflow: 'auto' }}>
          <Typography variant="subtitle2" fontWeight={600} mb={1}>Recent Mistakes</Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ color: '#8b949e', fontSize: 11, borderColor: '#21262d' }}>Category</TableCell>
                <TableCell sx={{ color: '#8b949e', fontSize: 11, borderColor: '#21262d' }}>Problem</TableCell>
                <TableCell sx={{ color: '#8b949e', fontSize: 11, borderColor: '#21262d' }}>Notes</TableCell>
                <TableCell sx={{ color: '#8b949e', fontSize: 11, borderColor: '#21262d' }}>Date</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {mistakes.slice(0, 50).map(m => (
                <TableRow key={m.id} sx={{ '&:last-child td': { border: 0 } }}>
                  <TableCell sx={{ borderColor: '#21262d' }}>
                    <Chip size="small" label={m.category} sx={{ fontSize: 10, bgcolor: '#2b0c0c', color: '#f85149' }} />
                  </TableCell>
                  <TableCell sx={{ borderColor: '#21262d' }}>
                    {m.problem_title ? (
                      <Typography variant="caption" sx={{ color: '#58a6ff', cursor: 'pointer' }}
                        onClick={() => navigate(`/problem/${m.problem_id}`)}>
                        {m.problem_title}
                      </Typography>
                    ) : '—'}
                  </TableCell>
                  <TableCell sx={{ borderColor: '#21262d' }}>
                    <Typography variant="caption" color="text.secondary">{m.notes || '—'}</Typography>
                  </TableCell>
                  <TableCell sx={{ borderColor: '#21262d' }}>
                    <Typography variant="caption" color="text.secondary">
                      {new Date(m.occurred_at).toLocaleDateString()}
                    </Typography>
                  </TableCell>
                </TableRow>
              ))}
              {mistakes.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} sx={{ textAlign: 'center', color: '#8b949e', py: 3, border: 0 }}>
                    No mistakes logged yet.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Paper>
      </Grid>

      {/* Add Mistake Dialog */}
      <Dialog open={addOpen} onClose={() => setAddOpen(false)} PaperProps={{ sx: { bgcolor: '#0d1117', border: '1px solid #30363d', minWidth: 380 } }}>
        <DialogTitle>Log a Mistake</DialogTitle>
        <DialogContent>
          <Stack gap={2} mt={1}>
            <FormControl size="small" fullWidth>
              <InputLabel>Category</InputLabel>
              <Select value={newMistake.category} label="Category" onChange={e => setNewMistake(p => ({ ...p, category: e.target.value }))}>
                {options.map(o => <MenuItem key={o} value={o}>{o}</MenuItem>)}
              </Select>
            </FormControl>
            <TextField
              size="small" fullWidth multiline rows={2}
              label="Notes (optional)"
              value={newMistake.notes}
              onChange={e => setNewMistake(p => ({ ...p, notes: e.target.value }))}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddOpen(false)} sx={{ color: 'text.secondary' }}>Cancel</Button>
          <Button variant="contained" onClick={handleAdd} disabled={!newMistake.category}>Log</Button>
        </DialogActions>
      </Dialog>
    </Grid>
  )
}

// ── Tab 4: Contest Log ────────────────────────────────────────────────────────
function ContestTab({ contests, onAdd, onDelete }) {
  const [addOpen, setAddOpen] = useState(false)
  const [form, setForm] = useState({
    platform: 'LeetCode', contest_name: '', contest_date: new Date().toISOString().slice(0, 10),
    rating: '', rating_change: '', global_rank: '', questions_solved: '0',
    total_questions: '4', penalty_mins: '', notes: '',
  })

  const handleAdd = () => {
    onAdd({
      ...form,
      contest_date: new Date(form.contest_date).toISOString(),
      rating: form.rating ? parseInt(form.rating) : null,
      rating_change: form.rating_change ? parseInt(form.rating_change) : null,
      global_rank: form.global_rank ? parseInt(form.global_rank) : null,
      questions_solved: parseInt(form.questions_solved) || 0,
      total_questions: parseInt(form.total_questions) || 4,
      penalty_mins: form.penalty_mins ? parseInt(form.penalty_mins) : null,
    })
    setAddOpen(false)
  }

  const ratingData = contests.slice().reverse().map(c => ({
    date: new Date(c.contest_date).toLocaleDateString(),
    rating: c.rating,
    change: c.rating_change,
  })).filter(d => d.rating)

  return (
    <Grid container spacing={2}>
      <Grid item xs={12}>
        <Stack direction="row" justifyContent="flex-end" mb={1}>
          <Button size="small" variant="outlined" startIcon={<Add />} onClick={() => setAddOpen(true)}
            sx={{ borderColor: '#30363d', color: '#58a6ff' }}>
            Log Contest
          </Button>
        </Stack>
      </Grid>

      {ratingData.length > 0 && (
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle2" fontWeight={600} mb={2}>Rating Trend</Typography>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={ratingData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#8b949e' }} />
                <YAxis tick={{ fontSize: 11, fill: '#8b949e' }} domain={['auto', 'auto']} />
                <RTooltip contentStyle={{ bgcolor: '#161b22', border: '1px solid #30363d' }} />
                <Line type="monotone" dataKey="rating" stroke="#58a6ff" dot={{ r: 4 }} strokeWidth={2} name="Rating" />
              </LineChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      )}

      <Grid item xs={12}>
        <Paper sx={{ p: 2 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                {['Date', 'Platform', 'Contest', 'Rating', 'Change', 'Rank', 'Solved', 'Notes'].map(h => (
                  <TableCell key={h} sx={{ color: '#8b949e', fontSize: 11, borderColor: '#21262d' }}>{h}</TableCell>
                ))}
                <TableCell sx={{ borderColor: '#21262d' }} />
              </TableRow>
            </TableHead>
            <TableBody>
              {contests.map(c => (
                <TableRow key={c.id} sx={{ '&:last-child td': { border: 0 } }}>
                  <TableCell sx={{ borderColor: '#21262d', fontSize: 12 }}>{new Date(c.contest_date).toLocaleDateString()}</TableCell>
                  <TableCell sx={{ borderColor: '#21262d', fontSize: 12 }}>{c.platform}</TableCell>
                  <TableCell sx={{ borderColor: '#21262d', fontSize: 12 }}>{c.contest_name || '—'}</TableCell>
                  <TableCell sx={{ borderColor: '#21262d', fontSize: 12, fontWeight: 600, color: '#58a6ff' }}>{c.rating ?? '—'}</TableCell>
                  <TableCell sx={{ borderColor: '#21262d', fontSize: 12 }}>
                    {c.rating_change != null ? (
                      <Typography variant="caption" sx={{ color: c.rating_change >= 0 ? '#3fb950' : '#f85149', fontWeight: 700 }}>
                        {c.rating_change >= 0 ? '+' : ''}{c.rating_change}
                      </Typography>
                    ) : '—'}
                  </TableCell>
                  <TableCell sx={{ borderColor: '#21262d', fontSize: 12 }}>{c.global_rank ? `#${c.global_rank.toLocaleString()}` : '—'}</TableCell>
                  <TableCell sx={{ borderColor: '#21262d', fontSize: 12 }}>
                    <Typography variant="caption" sx={{ color: c.questions_solved === c.total_questions ? '#3fb950' : 'inherit' }}>
                      {c.questions_solved}/{c.total_questions}
                    </Typography>
                  </TableCell>
                  <TableCell sx={{ borderColor: '#21262d', fontSize: 12, color: '#8b949e' }}>{c.notes || '—'}</TableCell>
                  <TableCell sx={{ borderColor: '#21262d' }}>
                    <IconButton size="small" onClick={() => onDelete(c.id)} sx={{ color: '#8b949e', '&:hover': { color: '#f85149' } }}>
                      <Delete sx={{ fontSize: 15 }} />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
              {contests.length === 0 && (
                <TableRow>
                  <TableCell colSpan={9} sx={{ textAlign: 'center', color: '#8b949e', py: 3, border: 0 }}>
                    No contests logged yet.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Paper>
      </Grid>

      <Dialog open={addOpen} onClose={() => setAddOpen(false)} maxWidth="sm" fullWidth
        PaperProps={{ sx: { bgcolor: '#0d1117', border: '1px solid #30363d' } }}>
        <DialogTitle>Log Contest Result</DialogTitle>
        <DialogContent>
          <Grid container spacing={1.5} mt={0.5}>
            {[
              { key: 'platform', label: 'Platform', opts: ['LeetCode', 'Codeforces', 'AtCoder', 'HackerRank', 'Other'] },
            ].map(({ key, label, opts }) => (
              <Grid item xs={6} key={key}>
                <FormControl size="small" fullWidth>
                  <InputLabel>{label}</InputLabel>
                  <Select value={form[key]} label={label} onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))}>
                    {opts.map(o => <MenuItem key={o} value={o}>{o}</MenuItem>)}
                  </Select>
                </FormControl>
              </Grid>
            ))}
            <Grid item xs={6}>
              <TextField size="small" fullWidth label="Date" type="date" value={form.contest_date}
                onChange={e => setForm(p => ({ ...p, contest_date: e.target.value }))}
                InputLabelProps={{ shrink: true }} />
            </Grid>
            <Grid item xs={12}>
              <TextField size="small" fullWidth label="Contest Name" value={form.contest_name}
                onChange={e => setForm(p => ({ ...p, contest_name: e.target.value }))} />
            </Grid>
            {[
              ['rating', 'Rating After', 6], ['rating_change', 'Rating Change', 6],
              ['global_rank', 'Global Rank', 6], ['questions_solved', 'Questions Solved', 3],
              ['total_questions', 'Total Questions', 3], ['penalty_mins', 'Penalty (mins)', 6],
            ].map(([key, label, xs]) => (
              <Grid item xs={xs} key={key}>
                <TextField size="small" fullWidth type="number" label={label} value={form[key]}
                  onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))} />
              </Grid>
            ))}
            <Grid item xs={12}>
              <TextField size="small" fullWidth label="Notes" value={form.notes}
                onChange={e => setForm(p => ({ ...p, notes: e.target.value }))} />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddOpen(false)} sx={{ color: 'text.secondary' }}>Cancel</Button>
          <Button variant="contained" onClick={handleAdd}>Save</Button>
        </DialogActions>
      </Dialog>
    </Grid>
  )
}

// ── Tab 5: DS Fluency ─────────────────────────────────────────────────────────
function DSFluencyTab({ fluencyMap, onUpdate }) {
  const DS_LIST = [
    'Array', 'String', 'HashMap', 'HashSet', 'Stack', 'Queue',
    'Heap', 'Linked List', 'Binary Tree', 'BST', 'Graph', 'Trie',
    'Deque', 'Union Find', 'Fenwick Tree', 'Segment Tree',
  ]
  const COLORS = ['', '#f85149', '#f85149', '#d29922', '#3fb950', '#3fb950']
  const LABELS = ['', 'Unfamiliar', 'Seen it', 'Can solve', 'Confident', 'Expert']

  return (
    <Box>
      <Alert severity="info" sx={{ mb: 2 }}>
        Rate your comfort level with each data structure. Click dots to update.
      </Alert>
      <Grid container spacing={1.5}>
        {DS_LIST.map(ds => {
          const current = fluencyMap[ds] || 0
          return (
            <Grid item xs={12} sm={6} md={4} key={ds}>
              <Paper sx={{ p: 1.5 }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1}>
                  <Typography variant="body2" fontWeight={600}>{ds}</Typography>
                  {current > 0 && (
                    <Chip size="small" label={LABELS[current]}
                      sx={{ fontSize: 10, bgcolor: `${COLORS[current]}22`, color: COLORS[current], border: `1px solid ${COLORS[current]}` }} />
                  )}
                </Stack>
                <Stack direction="row" gap={0.5}>
                  {[1,2,3,4,5].map(n => (
                    <Box
                      key={n}
                      onClick={() => onUpdate(ds, n)}
                      sx={{
                        width: 28, height: 28, borderRadius: '50%',
                        border: `2px solid ${n <= current ? COLORS[n] : '#30363d'}`,
                        bgcolor: n <= current ? `${COLORS[n]}22` : 'transparent',
                        cursor: 'pointer',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        transition: 'all 0.15s',
                        '&:hover': { borderColor: COLORS[n] },
                      }}
                    >
                      <Typography variant="caption" sx={{ color: n <= current ? COLORS[n] : '#8b949e', fontWeight: 700, fontSize: 10 }}>
                        {n}
                      </Typography>
                    </Box>
                  ))}
                </Stack>
              </Paper>
            </Grid>
          )
        })}
      </Grid>
    </Box>
  )
}

// ── Tab 6: Coding Quality ─────────────────────────────────────────────────────
function CodingQualityTab({ assessments }) {
  if (!assessments.length) return <Box sx={{ py: 6, textAlign: 'center' }}><Typography color="text.secondary">No assessments yet.</Typography></Box>

  // Aggregate bug category frequency
  const bugFreq = {}
  let totalCompile = 0, hintCount = 0, panicCount = 0, firstPassCount = 0

  assessments.forEach(a => {
    totalCompile += a.compile_attempts || 1
    if (a.hint_used) hintCount++
    if (a.did_panic) panicCount++
    if ((a.compile_attempts || 1) === 1) firstPassCount++
    ;(a.bug_categories || []).forEach(b => { bugFreq[b] = (bugFreq[b] || 0) + 1 })
  })

  const n = assessments.length
  const bugData = Object.entries(bugFreq)
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)

  const avgCompile = (totalCompile / n).toFixed(1)
  const firstPassPct = Math.round(firstPassCount / n * 100)
  const hintPct = Math.round(hintCount / n * 100)
  const panicPct = Math.round(panicCount / n * 100)

  return (
    <Grid container spacing={2}>
      {/* KPI row */}
      {[
        { label: 'Avg Compile Attempts', value: avgCompile, target: '< 1.5', good: parseFloat(avgCompile) < 1.5, color: '#58a6ff' },
        { label: 'First-Pass Success', value: `${firstPassPct}%`, target: '> 90%', good: firstPassPct >= 90, color: '#3fb950' },
        { label: 'Hint Usage Rate', value: `${hintPct}%`, target: '< 10%', good: hintPct < 10, color: '#d29922' },
        { label: 'Panic / Freeze Rate', value: `${panicPct}%`, target: '< 5%', good: panicPct < 5, color: '#f85149' },
      ].map(kpi => (
        <Grid item xs={12} sm={6} md={3} key={kpi.label}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h5" fontWeight={700} sx={{ color: kpi.good ? '#3fb950' : kpi.color }}>
              {kpi.value}
            </Typography>
            <Typography variant="body2" color="text.secondary">{kpi.label}</Typography>
            <Typography variant="caption" color={kpi.good ? '#3fb950' : '#8b949e'}>
              Target: {kpi.target}
            </Typography>
          </Paper>
        </Grid>
      ))}

      {/* Bug distribution */}
      {bugData.length > 0 && (
        <Grid item xs={12}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle2" fontWeight={600} mb={2}>Bug Categories</Typography>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={bugData} layout="vertical" margin={{ left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                <XAxis type="number" tick={{ fontSize: 11, fill: '#8b949e' }} />
                <YAxis dataKey="name" type="category" width={160} tick={{ fontSize: 10, fill: '#8b949e' }} />
                <RTooltip contentStyle={{ bgcolor: '#161b22', border: '1px solid #30363d' }} />
                <Bar dataKey="count" fill="#f85149" radius={[0, 4, 4, 0]} name="Occurrences" />
              </BarChart>
            </ResponsiveContainer>
          </Paper>
        </Grid>
      )}

      {/* Recent assessments */}
      <Grid item xs={12}>
        <Paper sx={{ p: 2, maxHeight: 350, overflow: 'auto' }}>
          <Typography variant="subtitle2" fontWeight={600} mb={1}>Recent Assessments</Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                {['Date', 'Problem', 'Pattern', 'Compile', 'Bugs', 'Communication', 'Confidence'].map(h => (
                  <TableCell key={h} sx={{ color: '#8b949e', fontSize: 11, borderColor: '#21262d' }}>{h}</TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {assessments.slice(0, 30).map(a => (
                <TableRow key={a.id} sx={{ '&:last-child td': { border: 0 } }}>
                  <TableCell sx={{ borderColor: '#21262d', fontSize: 11 }}>{new Date(a.assessed_at).toLocaleDateString()}</TableCell>
                  <TableCell sx={{ borderColor: '#21262d', fontSize: 11 }}>#{a.problem_id}</TableCell>
                  <TableCell sx={{ borderColor: '#21262d', fontSize: 11 }}>
                    {a.pattern_identified ? (
                      <Chip size="small" label={a.pattern_identified} sx={{
                        fontSize: 9,
                        bgcolor: a.pattern_was_correct ? '#0d2b15' : '#2b0c0c',
                        color:   a.pattern_was_correct ? '#3fb950' : '#f85149',
                      }} />
                    ) : '—'}
                  </TableCell>
                  <TableCell sx={{ borderColor: '#21262d', fontSize: 11 }}>
                    <Typography variant="caption" sx={{ color: (a.compile_attempts || 1) === 1 ? '#3fb950' : '#d29922', fontWeight: 600 }}>
                      {a.compile_attempts || 1}×
                    </Typography>
                  </TableCell>
                  <TableCell sx={{ borderColor: '#21262d', fontSize: 11 }}>{a.bugs_count || 0}</TableCell>
                  <TableCell sx={{ borderColor: '#21262d', fontSize: 11 }}>
                    {a.communication_score != null ? `${a.communication_score}/10` : '—'}
                  </TableCell>
                  <TableCell sx={{ borderColor: '#21262d', fontSize: 11 }}>
                    {a.confidence_after != null ? `${a.confidence_after}/5` : '—'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Paper>
      </Grid>
    </Grid>
  )
}

// ── Main InterviewPage ────────────────────────────────────────────────────────
export default function InterviewPage() {
  const { token } = useAuth()
  const navigate = useNavigate()

  const [tab, setTab] = useState(0)
  const [loading, setLoading] = useState(true)

  const [readiness, setReadiness] = useState(null)
  const [patterns, setPatterns] = useState([])
  const [dueReviews, setDueReviews] = useState([])
  const [allReviews, setAllReviews] = useState([])
  const [mistakes, setMistakes] = useState([])
  const [mistakeSummary, setMistakeSummary] = useState([])
  const [contests, setContests] = useState([])
  const [fluencyMap, setFluencyMap] = useState({})
  const [assessments, setAssessments] = useState([])

  useEffect(() => {
    if (!token) return
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
    Promise.all([
      getInterviewReadiness(),
      getPatternStats(),
      getReviewsDue(),
      getAllReviews(),
      listMistakes(),
      getMistakeSummary(),
      listContests(),
      getDSFluency(),
    ]).then(([r, p, due, all, mis, misSum, cont, flu]) => {
      setReadiness(r)
      setPatterns(p)
      setDueReviews(due)
      setAllReviews(all)
      setMistakes(mis)
      setMistakeSummary(misSum)
      setContests(cont)
      const fm = {}
      flu.forEach(f => { fm[f.ds_name] = f.rating })
      setFluencyMap(fm)
    }).catch(console.error).finally(() => setLoading(false))
  }, [token])

  // Fetch assessments lazily when Coding Quality tab is opened
  useEffect(() => {
    if (tab === 6 && assessments.length === 0) {
      import('../api/client').then(({ listAssessments }) =>
        listAssessments().then(setAssessments).catch(() => {})
      )
    }
  }, [tab])

  const handleCompleteReview = useCallback((problemId, quality) => {
    completeReview(problemId, quality).then(() => {
      setDueReviews(prev => prev.filter(r => r.problem_id !== problemId))
      return getAllReviews()
    }).then(setAllReviews).catch(() => {})
  }, [])

  const handleRemoveReview = useCallback((problemId) => {
    removeFromReview(problemId).then(() => {
      setDueReviews(prev => prev.filter(r => r.problem_id !== problemId))
      setAllReviews(prev => prev.filter(r => r.problem_id !== problemId))
    }).catch(() => {})
  }, [])

  const handleAddMistake = useCallback((m) => {
    logMistake(m).then(newMistake => {
      setMistakes(prev => [newMistake, ...prev])
      return getMistakeSummary()
    }).then(setMistakeSummary).catch(() => {})
  }, [])

  const handleAddContest = useCallback((c) => {
    logContest(c).then(newContest => {
      setContests(prev => [newContest, ...prev])
    }).catch(() => {})
  }, [])

  const handleDeleteContest = useCallback((id) => {
    deleteContest(id).then(() => {
      setContests(prev => prev.filter(c => c.id !== id))
    }).catch(() => {})
  }, [])

  const handleUpdateFluency = useCallback((dsName, rating) => {
    setFluencyMap(prev => ({ ...prev, [dsName]: rating }))
    updateDSFluency({ [dsName]: rating }).catch(() => {})
  }, [])

  const TABS = [
    { label: 'Readiness',      icon: <EmojiEvents /> },
    { label: 'Patterns',       icon: <Psychology />  },
    { label: 'Memory',         icon: <Schedule />    },
    { label: 'Mistakes',       icon: <Warning />     },
    { label: 'Contests',       icon: <Star />        },
    { label: 'DS Fluency',     icon: <School />      },
    { label: 'Coding Quality', icon: <BugReport />   },
  ]

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <Skeleton variant="text" width={240} height={44} sx={{ mb: 3 }} />
        <Grid container spacing={2} mb={3}>
          {[...Array(3)].map((_, i) => <Grid item xs={12} md={4} key={i}><Skeleton variant="rounded" height={200} /></Grid>)}
        </Grid>
      </Box>
    )
  }

  return (
    <Box sx={{ p: 3, maxWidth: 1200, mx: 'auto' }}>
      <Stack direction="row" alignItems="flex-start" justifyContent="space-between" mb={3}>
        <Box>
          <Typography variant="h4" fontWeight={700}>Interview Readiness</Typography>
          <Typography color="text.secondary" mt={0.5} variant="body2">
            Beyond problem count — measure how you actually think under pressure.
          </Typography>
        </Box>
        {readiness && (
          <Chip
            label={`${Math.round(readiness.total_score)} / 100 — ${readiness.label}`}
            sx={{
              bgcolor: `${readiness.label_color}22`, color: readiness.label_color,
              border: `1px solid ${readiness.label_color}`,
              fontWeight: 700, fontSize: 13, px: 1,
            }}
          />
        )}
      </Stack>

      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{ mb: 3, borderBottom: '1px solid', borderColor: 'divider' }}
        variant="scrollable"
        scrollButtons="auto"
      >
        {TABS.map((t, i) => (
          <Tab
            key={t.label}
            icon={t.icon}
            iconPosition="start"
            label={t.label}
            sx={{ minHeight: 48, fontSize: 13, gap: 0.5 }}
          />
        ))}
      </Tabs>

      {tab === 0 && <ReadinessDashboard readiness={readiness} />}
      {tab === 1 && <PatternTab patterns={patterns} />}
      {tab === 2 && <MemoryTab dueReviews={dueReviews} allReviews={allReviews} onComplete={handleCompleteReview} onRemove={handleRemoveReview} navigate={navigate} />}
      {tab === 3 && <MistakeTab mistakes={mistakes} summary={mistakeSummary} onAdd={handleAddMistake} navigate={navigate} />}
      {tab === 4 && <ContestTab contests={contests} onAdd={handleAddContest} onDelete={handleDeleteContest} />}
      {tab === 5 && <DSFluencyTab fluencyMap={fluencyMap} onUpdate={handleUpdateFluency} />}
      {tab === 6 && <CodingQualityTab assessments={assessments} />}
    </Box>
  )
}
