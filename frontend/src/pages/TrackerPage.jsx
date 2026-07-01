import React, { useEffect, useState, useMemo, useCallback } from 'react'
import {
  Box, Typography, TextField, Select, MenuItem, FormControl, InputLabel,
  IconButton, Tooltip, LinearProgress, CircularProgress,
  Table, TableBody, TableCell, TableHead, TableRow,
  Stack, Collapse, Button, Snackbar, Alert, Skeleton,
} from '@mui/material'
import {
  Star, StarBorder, CheckCircle, OpenInNew,
  Search, ExpandMore, ExpandLess, UnfoldLess, UnfoldMore,
  Casino, PlayArrow,
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import api, { getProblems, getAllProgress, starProblem } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

const DIFF_COLOR = { Easy: '#3fb950', Medium: '#d29922', Hard: '#f85149' }

const LS_KEY = 'algomaster_expanded_cats'

// ── Confidence dots (1-5) ─────────────────────────────────────────────────────
function ConfidenceDots({ value }) {
  if (!value) return <Typography variant="caption" color="text.disabled">—</Typography>
  const colors = ['#f85149', '#d29922', '#d29922', '#3fb950', '#3fb950']
  return (
    <Stack direction="row" gap={0.4} alignItems="center">
      {Array.from({ length: 5 }, (_, i) => (
        <Box key={i} sx={{
          width: 7, height: 7, borderRadius: '50%',
          bgcolor: i < value ? colors[value - 1] : '#2d3748',
        }} />
      ))}
    </Stack>
  )
}

// ── Single problem row ────────────────────────────────────────────────────────
function ProblemRow({ problem, progress, onStar }) {
  const navigate = useNavigate()
  const solved  = !!progress?.solved_at
  const starred = !!progress?.is_starred

  return (
    <TableRow
      hover
      onClick={() => navigate(`/problem/${problem.id}`)}
      sx={{
        cursor: 'pointer',
        '&:hover': { bgcolor: 'rgba(88,166,255,0.04)' },
        '&:last-child td': { borderBottom: 0 },
      }}
    >
      {/* Solved indicator */}
      <TableCell width={44} sx={{ py: 0.75, pl: 2, pr: 0 }}>
        {solved
          ? <CheckCircle sx={{ fontSize: 17, color: '#3fb950' }} />
          : <Box sx={{ width: 17, height: 17, border: '2px solid #444c56', borderRadius: '4px' }} />}
      </TableCell>

      {/* Title */}
      <TableCell sx={{ py: 0.75 }}>
        <Typography variant="body2" sx={{
          color: solved ? '#3fb950' : '#58a6ff', fontWeight: 500,
          '&:hover': { textDecoration: 'underline' },
        }}>
          {problem.title}
        </Typography>
      </TableCell>

      {/* Difficulty */}
      <TableCell width={90} sx={{ py: 0.75 }}>
        <Typography variant="body2" fontWeight={600} sx={{ color: DIFF_COLOR[problem.difficulty] }}>
          {problem.difficulty}
        </Typography>
      </TableCell>

      {/* Confidence */}
      <TableCell width={90} sx={{ py: 0.75 }}>
        <ConfidenceDots value={progress?.confidence || 0} />
      </TableCell>

      {/* LeetCode link */}
      <TableCell width={56} sx={{ py: 0.75 }} onClick={e => e.stopPropagation()}>
        {problem.leetcode_url && (
          <Tooltip title="Open on LeetCode">
            <IconButton
              size="small" component="a" href={problem.leetcode_url}
              target="_blank" rel="noopener"
              sx={{ color: '#e8a317', p: 0.5 }}
            >
              <Box sx={{
                width: 20, height: 20, borderRadius: '50%',
                border: '1.5px solid #e8a317',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 10, fontWeight: 700, color: '#e8a317', lineHeight: 1,
              }}>L</Box>
            </IconButton>
          </Tooltip>
        )}
      </TableCell>

      {/* Actions */}
      <TableCell width={72} sx={{ py: 0.75, pr: 1 }} onClick={e => e.stopPropagation()}>
        <Stack direction="row" gap={0} alignItems="center">
          <Tooltip title="Open problem">
            <IconButton size="small"
              onClick={e => { e.stopPropagation(); navigate(`/problem/${problem.id}`) }}
              sx={{ color: '#8b949e', '&:hover': { color: '#e6edf3' } }}>
              <OpenInNew sx={{ fontSize: 15 }} />
            </IconButton>
          </Tooltip>
          <Tooltip title={starred ? 'Unstar' : 'Bookmark'}>
            <IconButton size="small"
              onClick={e => { e.stopPropagation(); onStar(e, problem.id, starred) }}
              sx={{ color: starred ? '#d29922' : '#8b949e', '&:hover': { color: '#d29922' } }}>
              {starred ? <Star sx={{ fontSize: 15 }} /> : <StarBorder sx={{ fontSize: 15 }} />}
            </IconButton>
          </Tooltip>
        </Stack>
      </TableCell>
    </TableRow>
  )
}

// ── Category section ──────────────────────────────────────────────────────────
function CategorySection({ category, problems, progressMap, onStar, expanded, onToggle }) {
  const solved = problems.filter(p => progressMap[p.id]?.solved_at).length
  const total  = problems.length
  const pct    = total ? (solved / total) * 100 : 0
  const lcTag  = category.toLowerCase().replace(/[\s/]+/g, '-').replace(/[^a-z0-9-]/g, '')

  return (
    <Box sx={{ mb: '2px' }}>
      <Box
        onClick={onToggle}
        sx={{
          display: 'flex', alignItems: 'center', gap: 1,
          px: 2, py: 1.25,
          bgcolor: '#161b22', border: '1px solid #30363d',
          borderRadius: expanded ? '8px 8px 0 0' : '8px',
          cursor: 'pointer', userSelect: 'none',
          transition: 'background 0.15s',
          '&:hover': { bgcolor: '#1c2128' },
        }}
      >
        {expanded
          ? <ExpandLess sx={{ fontSize: 18, color: '#8b949e' }} />
          : <ExpandMore sx={{ fontSize: 18, color: '#8b949e' }} />}
        <Typography variant="subtitle1" fontWeight={700} sx={{ flexGrow: 1 }}>{category}</Typography>
        <Tooltip title={`Browse ${category} on LeetCode`}>
          <IconButton size="small" component="a"
            href={`https://leetcode.com/tag/${lcTag}/`}
            target="_blank" rel="noopener"
            onClick={e => e.stopPropagation()}
            sx={{ color: '#8b949e', '&:hover': { color: '#58a6ff' } }}>
            <OpenInNew sx={{ fontSize: 14 }} />
          </IconButton>
        </Tooltip>
        <Typography variant="body2" color="text.secondary" sx={{ minWidth: 52, textAlign: 'right' }}>
          {solved} / {total}
        </Typography>
        <Box sx={{ width: 110, ml: 1.5 }}>
          <LinearProgress variant="determinate" value={pct} sx={{
            height: 6, borderRadius: 3, bgcolor: '#21262d',
            '& .MuiLinearProgress-bar': { bgcolor: pct === 100 ? '#3fb950' : '#238636' },
          }} />
        </Box>
      </Box>

      <Collapse in={expanded} unmountOnExit>
        <Box sx={{ border: '1px solid #30363d', borderTop: 0, borderRadius: '0 0 8px 8px', overflow: 'hidden', bgcolor: '#0d1117' }}>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: '#0d1117' }}>
                <TableCell width={44} sx={{ pl: 2, pr: 0, py: 1, color: '#8b949e', fontSize: 12, fontWeight: 600, borderColor: '#21262d' }}>✓</TableCell>
                <TableCell sx={{ py: 1, color: '#8b949e', fontSize: 12, fontWeight: 600, borderColor: '#21262d' }}>Problem</TableCell>
                <TableCell width={90} sx={{ py: 1, color: '#8b949e', fontSize: 12, fontWeight: 600, borderColor: '#21262d' }}>Difficulty</TableCell>
                <TableCell width={90} sx={{ py: 1, color: '#8b949e', fontSize: 12, fontWeight: 600, borderColor: '#21262d' }}>Confidence</TableCell>
                <TableCell width={56} sx={{ py: 1, color: '#8b949e', fontSize: 12, fontWeight: 600, borderColor: '#21262d' }}>LC</TableCell>
                <TableCell width={72} sx={{ py: 1, pr: 1, color: '#8b949e', fontSize: 12, fontWeight: 600, borderColor: '#21262d' }}>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {problems.map(p => (
                <ProblemRow key={p.id} problem={p} progress={progressMap[p.id]} onStar={onStar} />
              ))}
            </TableBody>
          </Table>
        </Box>
      </Collapse>
    </Box>
  )
}

// ── Main TrackerPage ──────────────────────────────────────────────────────────
export default function TrackerPage() {
  const { token } = useAuth()
  const navigate  = useNavigate()

  const [problems,     setProblems]     = useState([])
  const [progressMap,  setProgressMap]  = useState({})
  const [loading,      setLoading]      = useState(true)
  const [search,       setSearch]       = useState('')
  const [diffFilter,   setDiffFilter]   = useState('All')
  const [statusFilter, setStatusFilter] = useState('All')
  const [catFilter,    setCatFilter]    = useState('All')
  const [expandedCats, setExpandedCats] = useState(() => {
    try { return JSON.parse(localStorage.getItem(LS_KEY) || 'null') || {} }
    catch { return {} }
  })
  // Toast for star/unstar
  const [toast, setToast] = useState({ open: false, msg: '' })

  useEffect(() => {
    if (!token) return
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
    setLoading(true)
    Promise.all([getProblems({ limit: 700 }), getAllProgress()])
      .then(([probs, prog]) => {
        setProblems(probs)
        const map = {}
        prog.forEach(p => { map[p.problem_id] = p })
        setProgressMap(map)

        // Only initialise expanded state when nothing is persisted yet
        const persisted = localStorage.getItem(LS_KEY)
        if (!persisted) {
          const cats = [...new Set(probs.map(p => p.category))]
          const initExpanded = {}
          cats.forEach((c, i) => { initExpanded[c] = i < 5 })
          setExpandedCats(initExpanded)
          localStorage.setItem(LS_KEY, JSON.stringify(initExpanded))
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [token])

  const handleStar = useCallback(async (e, id, wasStarred) => {
    e.stopPropagation()
    try {
      await starProblem(id)
      setProgressMap(prev => ({
        ...prev,
        [id]: { ...(prev[id] || { problem_id: id }), is_starred: !wasStarred },
      }))
      setToast({ open: true, msg: wasStarred ? 'Bookmark removed' : 'Bookmarked' })
    } catch {}
  }, [])

  const toggleCategory = useCallback((cat) => {
    setExpandedCats(prev => {
      const next = { ...prev, [cat]: !prev[cat] }
      localStorage.setItem(LS_KEY, JSON.stringify(next))
      return next
    })
  }, [])

  const expandAll = () => setExpandedCats(prev => {
    const next = Object.fromEntries(Object.keys(prev).map(k => [k, true]))
    localStorage.setItem(LS_KEY, JSON.stringify(next))
    return next
  })
  const collapseAll = () => setExpandedCats(prev => {
    const next = Object.fromEntries(Object.keys(prev).map(k => [k, false]))
    localStorage.setItem(LS_KEY, JSON.stringify(next))
    return next
  })

  // Random unsolved problem (weighted toward Medium)
  const handleRandom = useCallback(() => {
    const unsolved = problems.filter(p => !progressMap[p.id]?.solved_at)
    if (!unsolved.length) return
    // Weight: Medium × 3, Hard × 2, Easy × 1
    const weighted = unsolved.flatMap(p =>
      p.difficulty === 'Medium' ? [p, p, p]
      : p.difficulty === 'Hard' ? [p, p]
      : [p]
    )
    const pick = weighted[Math.floor(Math.random() * weighted.length)]
    navigate(`/problem/${pick.id}`)
  }, [problems, progressMap, navigate])

  // Continue = last attempted problem
  const handleContinue = useCallback(() => {
    const withAttempts = Object.values(progressMap)
      .filter(p => p.last_attempted_at)
      .sort((a, b) => new Date(b.last_attempted_at) - new Date(a.last_attempted_at))
    if (withAttempts.length) navigate(`/problem/${withAttempts[0].problem_id}`)
  }, [progressMap, navigate])

  // Group + filter
  const grouped = useMemo(() => {
    const filtered = problems.filter(p => {
      const prog = progressMap[p.id]
      if (search) {
        const q = search.toLowerCase()
        if (!p.title.toLowerCase().includes(q) && !p.category.toLowerCase().includes(q)) return false
      }
      if (diffFilter   !== 'All' && p.difficulty !== diffFilter) return false
      if (catFilter    !== 'All' && p.category   !== catFilter)  return false
      if (statusFilter === 'Solved'   && !prog?.solved_at)       return false
      if (statusFilter === 'Unsolved' &&  prog?.solved_at)       return false
      if (statusFilter === 'Starred'  && !prog?.is_starred)      return false
      return true
    })
    const order = [], map = {}
    filtered.forEach(p => {
      if (!map[p.category]) { map[p.category] = []; order.push(p.category) }
      map[p.category].push(p)
    })
    return order.map(cat => ({ category: cat, problems: map[cat] }))
  }, [problems, progressMap, search, diffFilter, catFilter, statusFilter])

  const allCategories = useMemo(() => [...new Set(problems.map(p => p.category))].sort(), [problems])
  const totalSolved   = Object.values(progressMap).filter(p => p.solved_at).length
  const totalProblems = problems.length
  const overallPct    = totalProblems ? ((totalSolved / totalProblems) * 100).toFixed(1) : 0
  const totalFiltered = grouped.reduce((acc, g) => acc + g.problems.length, 0)
  const hasLastAttempt = Object.values(progressMap).some(p => p.last_attempted_at)

  if (loading) {
    return (
      <Box sx={{ p: 3, maxWidth: 1100, mx: 'auto' }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" mb={3}>
          <Box>
            <Skeleton variant="text" width={200} height={44} />
            <Skeleton variant="text" width={160} height={20} sx={{ mt: 0.5 }} />
          </Box>
          <Skeleton variant="rounded" width={200} height={8} />
        </Stack>
        <Stack direction="row" gap={1.5} mb={2.5}>
          {[220, 110, 110, 170].map((w, i) => (
            <Skeleton key={i} variant="rounded" width={w} height={40} />
          ))}
        </Stack>
        <Stack gap="2px">
          {[...Array(8)].map((_, i) => (
            <Skeleton key={i} variant="rounded" height={52} sx={{ borderRadius: '8px' }} />
          ))}
        </Stack>
      </Box>
    )
  }

  return (
    <Box sx={{ p: 3, maxWidth: 1100, mx: 'auto' }}>
      {/* ── Header ── */}
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" mb={3}>
        <Box>
          <Typography variant="h4" fontWeight={700}>Problem Tracker</Typography>
          <Typography color="text.secondary" mt={0.5} variant="body2">
            {totalSolved} / {totalProblems} solved · {overallPct}% complete
          </Typography>
        </Box>
        <Box sx={{ width: 200, textAlign: 'right' }}>
          <LinearProgress variant="determinate" value={parseFloat(overallPct)} sx={{
            height: 8, borderRadius: 4, bgcolor: '#21262d',
            '& .MuiLinearProgress-bar': { bgcolor: '#238636' },
          }} />
        </Box>
      </Stack>

      {/* ── Filters + actions ── */}
      <Stack direction="row" gap={1.5} mb={2.5} flexWrap="wrap" alignItems="center">
        <TextField
          size="small" placeholder="Search problems…" value={search}
          onChange={e => setSearch(e.target.value)}
          InputProps={{ startAdornment: <Search sx={{ mr: 1, color: 'text.secondary', fontSize: 18 }} /> }}
          sx={{ minWidth: 220, bgcolor: '#0d1117' }}
        />
        <FormControl size="small" sx={{ minWidth: 110 }}>
          <InputLabel>Difficulty</InputLabel>
          <Select value={diffFilter} label="Difficulty" onChange={e => setDiffFilter(e.target.value)} sx={{ bgcolor: '#0d1117' }}>
            {['All', 'Easy', 'Medium', 'Hard'].map(d => <MenuItem key={d} value={d}>{d}</MenuItem>)}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 110 }}>
          <InputLabel>Status</InputLabel>
          <Select value={statusFilter} label="Status" onChange={e => setStatusFilter(e.target.value)} sx={{ bgcolor: '#0d1117' }}>
            {['All', 'Solved', 'Unsolved', 'Starred'].map(s => <MenuItem key={s} value={s}>{s}</MenuItem>)}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 170 }}>
          <InputLabel>Topic</InputLabel>
          <Select value={catFilter} label="Topic" onChange={e => setCatFilter(e.target.value)} sx={{ bgcolor: '#0d1117' }}>
            <MenuItem value="All">All Topics</MenuItem>
            {allCategories.map(c => <MenuItem key={c} value={c}>{c}</MenuItem>)}
          </Select>
        </FormControl>

        <Typography variant="body2" color="text.secondary">
          {totalFiltered} problems · {grouped.length} topics
        </Typography>

        <Box sx={{ ml: 'auto', display: 'flex', gap: 0.75, alignItems: 'center' }}>
          {hasLastAttempt && (
            <Tooltip title="Continue where you left off">
              <Button size="small" variant="outlined" startIcon={<PlayArrow />} onClick={handleContinue}
                sx={{ color: '#58a6ff', borderColor: '#1f3550', '&:hover': { borderColor: '#58a6ff' } }}>
                Continue
              </Button>
            </Tooltip>
          )}
          <Tooltip title="Open a random unsolved problem (weighted toward Medium)">
            <Button size="small" variant="outlined" startIcon={<Casino />} onClick={handleRandom}
              sx={{ color: '#d29922', borderColor: '#2b1f07', '&:hover': { borderColor: '#d29922' } }}>
              Random
            </Button>
          </Tooltip>
          <Button size="small" startIcon={<UnfoldMore />} onClick={expandAll} sx={{ color: 'text.secondary' }}>
            Expand all
          </Button>
          <Button size="small" startIcon={<UnfoldLess />} onClick={collapseAll} sx={{ color: 'text.secondary' }}>
            Collapse all
          </Button>
        </Box>
      </Stack>

      {/* ── Category groups ── */}
      <Stack gap="2px">
        {grouped.length === 0 ? (
          <Box sx={{ py: 6, textAlign: 'center' }}>
            <Typography color="text.secondary">No problems match your filters.</Typography>
          </Box>
        ) : (
          grouped.map(({ category, problems: catProblems }) => (
            <CategorySection
              key={category}
              category={category}
              problems={catProblems}
              progressMap={progressMap}
              onStar={handleStar}
              expanded={!!expandedCats[category]}
              onToggle={() => toggleCategory(category)}
            />
          ))
        )}
      </Stack>

      {/* ── Toast ── */}
      <Snackbar
        open={toast.open}
        autoHideDuration={2000}
        onClose={() => setToast(t => ({ ...t, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert severity="success" variant="filled" sx={{ fontSize: 13 }}>{toast.msg}</Alert>
      </Snackbar>
    </Box>
  )
}
