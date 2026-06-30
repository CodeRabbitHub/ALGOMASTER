import React, { useEffect, useState, useMemo, useCallback } from 'react'
import {
  Box, Typography, TextField, Select, MenuItem, FormControl, InputLabel,
  IconButton, Tooltip, LinearProgress, CircularProgress,
  Table, TableBody, TableCell, TableHead, TableRow,
  Stack, Collapse, Button,
} from '@mui/material'
import {
  Star, StarBorder, CheckCircle, RadioButtonUnchecked, OpenInNew,
  Search, ExpandMore, ExpandLess, UnfoldLess, UnfoldMore,
} from '@mui/icons-material'
import { useNavigate } from 'react-router-dom'
import api, { getProblems, getAllProgress, starProblem } from '../api/client'
import { useAuth } from '../contexts/AuthContext'

const DIFF_COLOR  = { Easy: '#3fb950', Medium: '#d29922', Hard: '#f85149' }
const DIFF_BG     = { Easy: '#0d2b15', Medium: '#2b1f07', Hard: '#2b0c0c' }

// ── Frequency dots ────────────────────────────────────────────────────────────
// Cosmetic only — proxy from difficulty (Easy=5, Medium=4, Hard=3)
const FREQ_MAP = { Easy: 5, Medium: 4, Hard: 3 }
function FrequencyDots({ difficulty }) {
  const val = FREQ_MAP[difficulty] ?? 3
  return (
    <Stack direction="row" gap={0.5} alignItems="center">
      {Array.from({ length: 5 }, (_, i) => (
        <Box key={i} sx={{
          width: 7, height: 7, borderRadius: '50%',
          bgcolor: i < val ? '#e8a317' : '#2d3748',
          flexShrink: 0,
        }} />
      ))}
    </Stack>
  )
}

// ── Single problem row ────────────────────────────────────────────────────────
function ProblemRow({ problem, progress, onStar }) {
  const navigate = useNavigate()
  const solved   = !!progress?.solved_at
  const starred  = !!progress?.is_starred

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
      {/* Solved checkbox */}
      <TableCell width={48} sx={{ py: 0.75, pl: 2, pr: 0 }}>
        {solved
          ? <CheckCircle sx={{ fontSize: 18, color: '#3fb950' }} />
          : <Box sx={{
              width: 18, height: 18, border: '2px solid #444c56',
              borderRadius: '4px', flexShrink: 0,
            }} />
        }
      </TableCell>

      {/* Title */}
      <TableCell sx={{ py: 0.75 }}>
        <Typography
          variant="body2"
          sx={{
            color: solved ? '#3fb950' : '#58a6ff',
            fontWeight: 500,
            '&:hover': { textDecoration: 'underline' },
          }}
        >
          {problem.title}
        </Typography>
      </TableCell>

      {/* Difficulty */}
      <TableCell width={90} sx={{ py: 0.75 }}>
        <Typography
          variant="body2"
          fontWeight={600}
          sx={{ color: DIFF_COLOR[problem.difficulty] }}
        >
          {problem.difficulty}
        </Typography>
      </TableCell>

      {/* Frequency dots */}
      <TableCell width={90} sx={{ py: 0.75 }}>
        <FrequencyDots difficulty={problem.difficulty} />
      </TableCell>

      {/* LeetCode link */}
      <TableCell width={60} sx={{ py: 0.75 }} onClick={e => e.stopPropagation()}>
        {problem.leetcode_url && (
          <Tooltip title="Open on LeetCode">
            <IconButton
              size="small"
              component="a"
              href={problem.leetcode_url}
              target="_blank"
              rel="noopener"
              sx={{ color: '#e8a317', p: 0.5 }}
            >
              {/* LeetCode "L" badge */}
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

      {/* Actions: open in editor + star */}
      <TableCell width={80} sx={{ py: 0.75, pr: 1 }} onClick={e => e.stopPropagation()}>
        <Stack direction="row" gap={0} alignItems="center">
          <Tooltip title="Open problem">
            <IconButton
              size="small"
              onClick={e => { e.stopPropagation(); navigate(`/problem/${problem.id}`) }}
              sx={{ color: '#8b949e', '&:hover': { color: '#e6edf3' } }}
            >
              <OpenInNew sx={{ fontSize: 15 }} />
            </IconButton>
          </Tooltip>
          <Tooltip title={starred ? 'Unstar' : 'Bookmark'}>
            <IconButton
              size="small"
              onClick={e => { e.stopPropagation(); onStar(e, problem.id) }}
              sx={{ color: starred ? '#d29922' : '#8b949e', '&:hover': { color: '#d29922' } }}
            >
              {starred
                ? <Star sx={{ fontSize: 15 }} />
                : <StarBorder sx={{ fontSize: 15 }} />}
            </IconButton>
          </Tooltip>
        </Stack>
      </TableCell>
    </TableRow>
  )
}

// ── Category section ──────────────────────────────────────────────────────────
function CategorySection({ category, problems, progressMap, onStar, expanded, onToggle }) {
  const solved  = problems.filter(p => progressMap[p.id]?.solved_at).length
  const total   = problems.length
  const pct     = total ? (solved / total) * 100 : 0

  // LeetCode tag slug: lowercase, hyphens
  const lcTag = category.toLowerCase().replace(/[\s/]+/g, '-').replace(/[^a-z0-9-]/g, '')

  return (
    <Box sx={{ mb: '2px' }}>
      {/* ── Category header ── */}
      <Box
        onClick={onToggle}
        sx={{
          display: 'flex', alignItems: 'center', gap: 1,
          px: 2, py: 1.25,
          bgcolor: '#161b22',
          border: '1px solid #30363d',
          borderRadius: expanded ? '8px 8px 0 0' : '8px',
          cursor: 'pointer',
          userSelect: 'none',
          transition: 'background 0.15s',
          '&:hover': { bgcolor: '#1c2128' },
        }}
      >
        {expanded
          ? <ExpandLess sx={{ fontSize: 18, color: '#8b949e' }} />
          : <ExpandMore sx={{ fontSize: 18, color: '#8b949e' }} />
        }

        <Typography variant="subtitle1" fontWeight={700} sx={{ flexGrow: 1 }}>
          {category}
        </Typography>

        {/* Link to LeetCode tag */}
        <Tooltip title={`Browse ${category} on LeetCode`}>
          <IconButton
            size="small"
            component="a"
            href={`https://leetcode.com/tag/${lcTag}/`}
            target="_blank"
            rel="noopener"
            onClick={e => e.stopPropagation()}
            sx={{ color: '#8b949e', '&:hover': { color: '#58a6ff' } }}
          >
            <OpenInNew sx={{ fontSize: 14 }} />
          </IconButton>
        </Tooltip>

        {/* Progress counter */}
        <Typography variant="body2" color="text.secondary" sx={{ minWidth: 52, textAlign: 'right' }}>
          {solved} / {total}
        </Typography>

        {/* Progress bar */}
        <Box sx={{ width: 110, ml: 1.5 }}>
          <LinearProgress
            variant="determinate"
            value={pct}
            sx={{
              height: 6, borderRadius: 3,
              bgcolor: '#21262d',
              '& .MuiLinearProgress-bar': {
                bgcolor: pct === 100 ? '#3fb950' : '#238636',
              },
            }}
          />
        </Box>
      </Box>

      {/* ── Problem rows ── */}
      <Collapse in={expanded} unmountOnExit>
        <Box sx={{
          border: '1px solid #30363d',
          borderTop: 0,
          borderRadius: '0 0 8px 8px',
          overflow: 'hidden',
          bgcolor: '#0d1117',
        }}>
          <Table size="small">
            {/* Column headers (only shown once, inside first open section) */}
            <TableHead>
              <TableRow sx={{ bgcolor: '#0d1117' }}>
                <TableCell width={48} sx={{ pl: 2, pr: 0, py: 1, color: '#8b949e', fontSize: 12, fontWeight: 600, borderColor: '#21262d' }}>
                  Status
                </TableCell>
                <TableCell sx={{ py: 1, color: '#8b949e', fontSize: 12, fontWeight: 600, borderColor: '#21262d' }}>
                  Problem
                </TableCell>
                <TableCell width={90} sx={{ py: 1, color: '#8b949e', fontSize: 12, fontWeight: 600, borderColor: '#21262d' }}>
                  Difficulty
                </TableCell>
                <TableCell width={90} sx={{ py: 1, color: '#8b949e', fontSize: 12, fontWeight: 600, borderColor: '#21262d' }}>
                  Frequency
                </TableCell>
                <TableCell width={60} sx={{ py: 1, color: '#8b949e', fontSize: 12, fontWeight: 600, borderColor: '#21262d' }}>
                  LeetCode
                </TableCell>
                <TableCell width={80} sx={{ py: 1, pr: 1, color: '#8b949e', fontSize: 12, fontWeight: 600, borderColor: '#21262d' }}>
                  Actions
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {problems.map(p => (
                <ProblemRow
                  key={p.id}
                  problem={p}
                  progress={progressMap[p.id]}
                  onStar={onStar}
                />
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
  const [problems,     setProblems]     = useState([])
  const [progressMap,  setProgressMap]  = useState({})
  const [loading,      setLoading]      = useState(true)
  const [search,       setSearch]       = useState('')
  const [diffFilter,   setDiffFilter]   = useState('All')
  const [statusFilter, setStatusFilter] = useState('All')
  const [expandedCats, setExpandedCats] = useState({})  // { [category]: bool }
  const [catFilter,    setCatFilter]    = useState('All')

  useEffect(() => {
    if (!token) return
    // Belt-and-suspenders: ensure header is set before fetching,
    // regardless of when the AuthContext useEffect fires.
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
    setLoading(true)
    Promise.all([getProblems({ limit: 700 }), getAllProgress()])
      .then(([probs, prog]) => {
        setProblems(probs)
        const map = {}
        prog.forEach(p => { map[p.problem_id] = p })
        setProgressMap(map)

        // Default: expand first 5 categories, collapse rest
        const cats = [...new Set(probs.map(p => p.category))]
        const initExpanded = {}
        cats.forEach((c, i) => { initExpanded[c] = i < 5 })
        setExpandedCats(initExpanded)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [token])

  const handleStar = useCallback(async (e, id) => {
    e.stopPropagation()
    try {
      await starProblem(id)
      setProgressMap(prev => ({
        ...prev,
        [id]: { ...(prev[id] || { problem_id: id }), is_starred: !prev[id]?.is_starred },
      }))
    } catch {}
  }, [])

  const toggleCategory = useCallback((cat) => {
    setExpandedCats(prev => ({ ...prev, [cat]: !prev[cat] }))
  }, [])

  const expandAll  = () => setExpandedCats(prev => Object.fromEntries(Object.keys(prev).map(k => [k, true])))
  const collapseAll = () => setExpandedCats(prev => Object.fromEntries(Object.keys(prev).map(k => [k, false])))

  // Group + filter problems
  const grouped = useMemo(() => {
    const filtered = problems.filter(p => {
      const prog = progressMap[p.id]
      if (search) {
        const q = search.toLowerCase()
        if (!p.title.toLowerCase().includes(q) && !p.category.toLowerCase().includes(q)) return false
      }
      if (diffFilter   !== 'All' && p.difficulty !== diffFilter)  return false
      if (catFilter    !== 'All' && p.category   !== catFilter)   return false
      if (statusFilter === 'Solved'   && !prog?.solved_at)        return false
      if (statusFilter === 'Unsolved' &&  prog?.solved_at)        return false
      if (statusFilter === 'Starred'  && !prog?.is_starred)       return false
      return true
    })

    // Preserve category order from API (insertion order of first occurrence)
    const order = []
    const map   = {}
    filtered.forEach(p => {
      if (!map[p.category]) { map[p.category] = []; order.push(p.category) }
      map[p.category].push(p)
    })
    return order.map(cat => ({ category: cat, problems: map[cat] }))
  }, [problems, progressMap, search, diffFilter, catFilter, statusFilter])

  // All unique categories for the dropdown
  const allCategories = useMemo(() => [...new Set(problems.map(p => p.category))].sort(), [problems])

  // Overall stats
  const totalSolved   = Object.values(progressMap).filter(p => p.solved_at).length
  const totalProblems = problems.length
  const overallPct    = totalProblems ? ((totalSolved / totalProblems) * 100).toFixed(1) : 0
  const totalFiltered = grouped.reduce((acc, g) => acc + g.problems.length, 0)

  if (loading) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <CircularProgress />
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
          <LinearProgress
            variant="determinate"
            value={parseFloat(overallPct)}
            sx={{
              height: 8, borderRadius: 4, bgcolor: '#21262d',
              '& .MuiLinearProgress-bar': { bgcolor: '#238636' },
            }}
          />
        </Box>
      </Stack>

      {/* ── Filters ── */}
      <Stack direction="row" gap={1.5} mb={2.5} flexWrap="wrap" alignItems="center">
        <TextField
          size="small"
          placeholder="Search problems…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          InputProps={{ startAdornment: <Search sx={{ mr: 1, color: 'text.secondary', fontSize: 18 }} /> }}
          sx={{ minWidth: 220, bgcolor: '#0d1117' }}
        />
        <FormControl size="small" sx={{ minWidth: 110 }}>
          <InputLabel>Difficulty</InputLabel>
          <Select value={diffFilter} label="Difficulty" onChange={e => setDiffFilter(e.target.value)}
            sx={{ bgcolor: '#0d1117' }}>
            {['All', 'Easy', 'Medium', 'Hard'].map(d => (
              <MenuItem key={d} value={d}>{d}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 110 }}>
          <InputLabel>Status</InputLabel>
          <Select value={statusFilter} label="Status" onChange={e => setStatusFilter(e.target.value)}
            sx={{ bgcolor: '#0d1117' }}>
            {['All', 'Solved', 'Unsolved', 'Starred'].map(s => (
              <MenuItem key={s} value={s}>{s}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 170 }}>
          <InputLabel>Topic</InputLabel>
          <Select value={catFilter} label="Topic" onChange={e => setCatFilter(e.target.value)}
            sx={{ bgcolor: '#0d1117' }}>
            <MenuItem value="All">All Topics</MenuItem>
            {allCategories.map(c => (
              <MenuItem key={c} value={c}>{c}</MenuItem>
            ))}
          </Select>
        </FormControl>

        <Typography variant="body2" color="text.secondary">
          {totalFiltered} problems · {grouped.length} topics
        </Typography>

        <Box sx={{ ml: 'auto' }}>
          <Button size="small" startIcon={<UnfoldMore />} onClick={expandAll}
            sx={{ color: 'text.secondary', mr: 0.5 }}>
            Expand all
          </Button>
          <Button size="small" startIcon={<UnfoldLess />} onClick={collapseAll}
            sx={{ color: 'text.secondary' }}>
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
    </Box>
  )
}
