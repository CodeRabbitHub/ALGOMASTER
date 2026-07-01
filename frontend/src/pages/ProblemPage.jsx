import React, { useEffect, useState, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Box, Typography, Stack, Chip, Button, IconButton, Tooltip,
  Paper, CircularProgress, Tabs, Tab, TextField,
  Alert, LinearProgress, Collapse,
} from '@mui/material'
import {
  ArrowBack, Star, StarBorder, PlayArrow, CheckCircle,
  RadioButtonUnchecked, OpenInNew, History, ExpandMore, ExpandLess,
  LightbulbOutlined, Send, AutoAwesome, BugReport, RateReview,
} from '@mui/icons-material'
import Editor from '@monaco-editor/react'
import {
  getProblem, getProgress, updateProgress, starProblem,
  runCode, getAttemptHistory, getAIInsight,
} from '../api/client'

const DIFF_COLOR = { Easy: '#3fb950', Medium: '#d29922', Hard: '#f85149' }

function formatTime(secs) {
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  if (h > 0) return `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
  return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
}

const DEFAULT_CODE = `def solve(nums):
    """
    Write your solution here.
    Time complexity:  O(?)
    Space complexity: O(?)
    """
    pass
`

// ── Inline markdown renderer — handles **bold**, *italic*, and `code` ────────
function InlineText({ text }) {
  // Order matters: **bold** before *italic* to avoid partial matches
  const tokens = text.split(/(\*\*[^*]+\*\*|\*[^*\s][^*]*\*|\*[^*\s]\*|`[^`]+`)/g)
  return (
    <>
      {tokens.map((tok, i) => {
        if (tok.startsWith('**') && tok.endsWith('**')) {
          return <Box key={i} component="strong" sx={{ fontWeight: 700, color: '#e6edf3' }}>{tok.slice(2, -2)}</Box>
        }
        if (tok.startsWith('*') && tok.endsWith('*') && !tok.startsWith('**')) {
          return <Box key={i} component="em" sx={{ fontStyle: 'italic', color: '#e6edf3' }}>{tok.slice(1, -1)}</Box>
        }
        if (tok.startsWith('`') && tok.endsWith('`')) {
          return (
            <Box key={i} component="code" sx={{
              bgcolor: '#21262d', px: 0.6, py: 0.2, borderRadius: 0.5,
              fontFamily: 'JetBrains Mono, monospace', fontSize: 12,
            }}>{tok.slice(1, -1)}</Box>
          )
        }
        return tok
      })}
    </>
  )
}

// ── Description renderer ─────────────────────────────────────────────────────
function DescriptionBlock({ text }) {
  if (!text) return null
  const lines = text.split('\n')
  const result = []
  let inCode = false
  let codeLines = []
  let codeLang = ''

  lines.forEach((line, i) => {
    // Code fence open/close
    if (line.startsWith('```')) {
      if (!inCode) {
        inCode = true
        codeLang = line.slice(3).trim()
        codeLines = []
      } else {
        result.push(
          <Box key={i} component="pre" sx={{
            my: 1.5, p: 1.5, bgcolor: '#0d1117', borderRadius: 1,
            border: '1px solid #21262d', overflowX: 'auto',
            fontFamily: 'JetBrains Mono, monospace', fontSize: 12.5,
            color: '#e6edf3', lineHeight: 1.7, whiteSpace: 'pre',
          }}>
            {codeLines.join('\n')}
          </Box>
        )
        inCode = false
        codeLines = []
      }
      return
    }
    if (inCode) { codeLines.push(line); return }

    // Blank line
    if (!line.trim()) { result.push(<Box key={i} sx={{ height: 8 }} />); return }

    // Headings  ##### / #### / ### / ## / #
    const headingMatch = line.match(/^(#{1,6})\s+(.*)/)
    if (headingMatch) {
      const level = headingMatch[1].length
      const sizes = { 1: 18, 2: 16, 3: 15, 4: 14, 5: 13, 6: 12.5 }
      result.push(
        <Typography key={i} component="p" sx={{
          fontSize: sizes[level] || 13, fontWeight: 700,
          color: '#e6edf3', mt: level <= 3 ? 2 : 1, mb: 0.5,
        }}>
          <InlineText text={headingMatch[2]} />
        </Typography>
      )
      return
    }

    // List item  - text  or  * text
    const listMatch = line.match(/^(\s*)([-*])\s+(.*)/)
    if (listMatch) {
      const indent = listMatch[1].length
      result.push(
        <Stack key={i} direction="row" sx={{ pl: indent / 2 + 1.5, mb: 0.4 }}>
          <Box component="span" sx={{ color: '#58a6ff', mr: 1, mt: '2px', flexShrink: 0 }}>•</Box>
          <Typography variant="body2" sx={{ color: '#c9d1d9', lineHeight: 1.7 }}>
            <InlineText text={listMatch[3]} />
          </Typography>
        </Stack>
      )
      return
    }

    // Numbered list  1. text
    const numListMatch = line.match(/^(\s*)(\d+)\.\s+(.*)/)
    if (numListMatch) {
      const indent = numListMatch[1].length
      result.push(
        <Stack key={i} direction="row" sx={{ pl: indent / 2 + 1.5, mb: 0.4 }}>
          <Box component="span" sx={{ color: '#58a6ff', mr: 1, flexShrink: 0, minWidth: 20 }}>
            {numListMatch[2]}.
          </Box>
          <Typography variant="body2" sx={{ color: '#c9d1d9', lineHeight: 1.7 }}>
            <InlineText text={numListMatch[3]} />
          </Typography>
        </Stack>
      )
      return
    }

    // Normal paragraph
    result.push(
      <Typography key={i} variant="body2" component="p" sx={{ mb: 0.5, color: '#c9d1d9', lineHeight: 1.8 }}>
        <InlineText text={line} />
      </Typography>
    )
  })

  return <Box sx={{ lineHeight: 1.8 }}>{result}</Box>
}

// ── Example box ──────────────────────────────────────────────────────────────
function ExampleBox({ example, index }) {
  return (
    <Paper sx={{ p: 2, mb: 1.5, bgcolor: '#0d1117', border: '1px solid #21262d' }}>
      <Typography variant="caption" color="primary.main" fontWeight={600} sx={{ mb: 1, display: 'block' }}>
        Example {index + 1}
      </Typography>
      <Stack gap={1}>
        <Box>
          <Typography variant="caption" color="text.secondary" fontWeight={600}>Input</Typography>
          <Box sx={{
            mt: 0.5, p: 1.5, bgcolor: '#161b22', borderRadius: 1,
            fontFamily: 'JetBrains Mono, monospace', fontSize: 13, color: '#e6edf3',
            borderLeft: '3px solid #30363d', whiteSpace: 'pre-wrap',
          }}>
            {example.input}
          </Box>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary" fontWeight={600}>Output</Typography>
          <Box sx={{
            mt: 0.5, p: 1.5, bgcolor: '#161b22', borderRadius: 1,
            fontFamily: 'JetBrains Mono, monospace', fontSize: 13, color: '#3fb950',
            borderLeft: '3px solid #3fb950', whiteSpace: 'pre-wrap',
          }}>
            {example.expected_output || '—'}
          </Box>
        </Box>
        {example.explanation && (
          <Box>
            <Typography variant="caption" color="text.secondary" fontWeight={600}>Explanation</Typography>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5, lineHeight: 1.6 }}>
              {example.explanation}
            </Typography>
          </Box>
        )}
      </Stack>
    </Paper>
  )
}

// ── Hints section ─────────────────────────────────────────────────────────────
function HintsSection({ hints }) {
  const [open, setOpen] = useState(false)
  const [revealed, setRevealed] = useState(0)
  if (!hints?.length) return null
  return (
    <Box mt={2}>
      <Button
        size="small"
        startIcon={<LightbulbOutlined />}
        onClick={() => setOpen(o => !o)}
        endIcon={open ? <ExpandLess /> : <ExpandMore />}
        sx={{ color: '#d29922', mb: 1 }}
      >
        Hints ({hints.length})
      </Button>
      <Collapse in={open}>
        <Stack gap={1}>
          {hints.slice(0, revealed + 1).map((h, i) => (
            <Alert key={i} severity="warning" sx={{ py: 0.5, '& .MuiAlert-message': { fontSize: 13 } }}>
              <strong>Hint {i + 1}:</strong> {h}
            </Alert>
          ))}
          {revealed < hints.length - 1 && (
            <Button size="small" onClick={() => setRevealed(r => r + 1)} sx={{ alignSelf: 'flex-start' }}>
              Show next hint
            </Button>
          )}
        </Stack>
      </Collapse>
    </Box>
  )
}

// ── Test Case Panel ───────────────────────────────────────────────────────────
function TestCasePanel({ testCases, result, running }) {
  const [activeCase, setActiveCase] = useState(0)
  // Only show test cases that have an expected output
  const cases = (testCases || []).filter(tc => tc.expected_output?.trim()).slice(0, 10)
  if (!cases.length) return null

  // Build a map: test_case index (1-based) → result
  const resultMap = {}
  if (result?.test_results) {
    result.test_results.forEach(tr => { resultMap[tr.test_case - 1] = tr })
  }

  const tc = cases[activeCase]
  const tr = resultMap[activeCase]
  const hasRun = !!result

  return (
    <Box sx={{ borderTop: '1px solid', borderColor: 'divider', bgcolor: '#0a0e14', flexShrink: 0 }}>
      {/* Header row */}
      <Stack direction="row" alignItems="center" px={1.5} pt={1} pb={0} gap={1}>
        <Typography variant="caption" color="text.secondary" fontWeight={600} sx={{ mr: 1 }}>
          TEST CASES
        </Typography>

        {/* Case tabs */}
        <Stack direction="row" gap={0.5} flexWrap="wrap" sx={{ flexGrow: 1 }}>
          {cases.map((_, i) => {
            const r = resultMap[i]
            const bg = !hasRun ? '#21262d'
              : r?.passed ? '#1a3a1a' : '#3a1a1a'
            const border = !hasRun ? '#30363d'
              : r?.passed ? '#3fb950' : '#f85149'
            const dot = !hasRun ? null
              : r?.passed ? '✓' : '✗'

            return (
              <Box
                key={i}
                onClick={() => setActiveCase(i)}
                sx={{
                  px: 1.25, py: 0.3, borderRadius: 1, cursor: 'pointer',
                  border: `1px solid ${activeCase === i ? '#58a6ff' : border}`,
                  bgcolor: activeCase === i ? '#0d1f3a' : bg,
                  fontSize: 12, color: activeCase === i ? '#58a6ff' : '#e6edf3',
                  fontWeight: activeCase === i ? 700 : 400,
                  userSelect: 'none', display: 'flex', alignItems: 'center', gap: 0.5,
                  transition: 'all 0.15s',
                }}
              >
                {dot && (
                  <Box component="span" sx={{ color: resultMap[i]?.passed ? '#3fb950' : '#f85149', fontSize: 11 }}>
                    {dot}
                  </Box>
                )}
                Case {i + 1}
              </Box>
            )
          })}
        </Stack>

        {/* stdout / error summary pill */}
        {hasRun && (
          <Chip
            size="small"
            label={result.is_correct ? '✓ All Passed' : result.error_type || 'Some Failed'}
            color={result.is_correct ? 'success' : 'error'}
            sx={{ fontSize: 11, height: 22 }}
          />
        )}
        {hasRun && result.exec_time_ms !== undefined && (
          <Typography variant="caption" color="text.secondary">{result.exec_time_ms}ms</Typography>
        )}
      </Stack>

      {/* Case detail */}
      <Box sx={{ p: 1.5, pt: 1 }}>
        <Stack direction="row" gap={1.5}>
          {/* Input */}
          <Box sx={{ flex: 1 }}>
            <Typography variant="caption" color="text.secondary" fontWeight={600}>INPUT</Typography>
            <Box sx={{
              mt: 0.5, p: 1.25, bgcolor: '#161b22', borderRadius: 1,
              fontFamily: 'JetBrains Mono, monospace', fontSize: 12.5, color: '#e6edf3',
              borderLeft: '3px solid #30363d', whiteSpace: 'pre-wrap', minHeight: 44,
            }}>
              {tc?.input || '—'}
            </Box>
          </Box>

          {/* Expected */}
          <Box sx={{ flex: 1 }}>
            <Typography variant="caption" color="text.secondary" fontWeight={600}>EXPECTED OUTPUT</Typography>
            <Box sx={{
              mt: 0.5, p: 1.25, bgcolor: '#161b22', borderRadius: 1,
              fontFamily: 'JetBrains Mono, monospace', fontSize: 12.5, color: '#3fb950',
              borderLeft: '3px solid #3fb950', whiteSpace: 'pre-wrap', minHeight: 44,
            }}>
              {tc?.expected_output || '—'}
            </Box>
          </Box>

          {/* Actual (only after run) */}
          {hasRun && (
            <Box sx={{ flex: 1 }}>
              <Typography variant="caption" color="text.secondary" fontWeight={600}>ACTUAL OUTPUT</Typography>
              <Box sx={{
                mt: 0.5, p: 1.25, bgcolor: '#161b22', borderRadius: 1,
                fontFamily: 'JetBrains Mono, monospace', fontSize: 12.5,
                color: tr?.passed ? '#3fb950' : '#f85149',
                borderLeft: `3px solid ${tr?.passed ? '#3fb950' : '#f85149'}`,
                whiteSpace: 'pre-wrap', minHeight: 44,
              }}>
                {tr ? (tr.actual ?? '—') : '—'}
              </Box>
            </Box>
          )}
        </Stack>

        {/* Error / stdout row */}
        {hasRun && result.error_message && (
          <Box mt={1}>
            <Typography variant="caption" color="error.main" fontWeight={600}>ERROR</Typography>
            <Box component="pre" sx={{
              mt: 0.5, fontFamily: 'JetBrains Mono', fontSize: 12,
              color: '#f85149', whiteSpace: 'pre-wrap',
            }}>
              {result.error_message}
            </Box>
          </Box>
        )}
        {hasRun && result.stdout && (
          <Box mt={1}>
            <Typography variant="caption" color="text.secondary" fontWeight={600}>STDOUT</Typography>
            <Box component="pre" sx={{
              mt: 0.5, fontFamily: 'JetBrains Mono', fontSize: 12,
              color: '#8b949e', whiteSpace: 'pre-wrap',
            }}>
              {result.stdout}
            </Box>
          </Box>
        )}
      </Box>
    </Box>
  )
}

// ── Verdict Screen (shown after Submit) ───────────────────────────────────────
function VerdictScreen({ verdict, problem, elapsedSecs, onClose, onExplainMistake, onCodeReview, aiLoading, aiResult }) {
  const passed = verdict.test_results?.filter(r => r.passed).length ?? 0
  const total  = verdict.test_results?.length ?? 0
  const allOk  = verdict.is_correct

  return (
    <Box sx={{
      position: 'absolute', inset: 0, zIndex: 10,
      bgcolor: 'rgba(0,0,0,0.85)', display: 'flex',
      alignItems: 'center', justifyContent: 'center',
    }}>
      <Paper sx={{
        p: 4, minWidth: 420, maxWidth: 600, maxHeight: '90vh', overflow: 'auto',
        bgcolor: '#0d1117',
        border: `2px solid ${allOk ? '#3fb950' : '#f85149'}`,
        borderRadius: 2, textAlign: 'center',
      }}>
        {/* Icon */}
        <Typography sx={{ fontSize: 56, lineHeight: 1, mb: 1 }}>
          {allOk ? '🎉' : '❌'}
        </Typography>

        {/* Verdict */}
        <Typography variant="h5" fontWeight={700}
          sx={{ color: allOk ? '#3fb950' : '#f85149', mb: 0.5 }}>
          {allOk ? 'Accepted' : 'Wrong Answer'}
        </Typography>
        <Typography variant="body2" color="text.secondary" mb={3}>
          {problem?.title}
        </Typography>

        {/* Stats */}
        <Stack direction="row" justifyContent="center" gap={4} mb={3}>
          <Box>
            <Typography variant="h4" fontWeight={700}
              sx={{ color: allOk ? '#3fb950' : '#f85149' }}>
              {passed}/{total}
            </Typography>
            <Typography variant="caption" color="text.secondary">Test Cases</Typography>
          </Box>
          <Box>
            <Typography variant="h4" fontWeight={700} color="text.primary">
              {formatTime(elapsedSecs)}
            </Typography>
            <Typography variant="caption" color="text.secondary">Time Spent</Typography>
          </Box>
          {verdict.execution_time_ms > 0 && (
            <Box>
              <Typography variant="h4" fontWeight={700} color="text.primary">
                {verdict.execution_time_ms}ms
              </Typography>
              <Typography variant="caption" color="text.secondary">Runtime</Typography>
            </Box>
          )}
        </Stack>

        {/* Failed cases list */}
        {!allOk && verdict.test_results?.filter(r => !r.passed).slice(0, 3).map((r, i) => (
          <Paper key={i} sx={{ p: 1.5, mb: 1, bgcolor: '#1a0a0a', border: '1px solid #3a1a1a', textAlign: 'left' }}>
            <Typography variant="caption" color="error.main" fontWeight={600}>
              Case {r.test_case} Failed
            </Typography>
            <Stack direction="row" gap={2} mt={0.5}>
              <Box flex={1}>
                <Typography variant="caption" color="text.secondary">Expected</Typography>
                <Box sx={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#3fb950' }}>{r.expected}</Box>
              </Box>
              <Box flex={1}>
                <Typography variant="caption" color="text.secondary">Got</Typography>
                <Box sx={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#f85149' }}>{r.actual || '(no output)'}</Box>
              </Box>
            </Stack>
          </Paper>
        ))}

        {/* Error */}
        {verdict.error_message && (
          <Box sx={{ p: 1.5, mb: 2, bgcolor: '#1a0a0a', borderRadius: 1, textAlign: 'left' }}>
            <Typography variant="caption" color="error.main" fontWeight={600}>Error</Typography>
            <Box component="pre" sx={{ fontSize: 11, color: '#f85149', whiteSpace: 'pre-wrap', mt: 0.5, maxHeight: 120, overflow: 'auto' }}>
              {verdict.error_message}
            </Box>
          </Box>
        )}

        {/* AI buttons */}
        <Stack direction="row" gap={1} justifyContent="center" mb={aiResult ? 2 : 0} mt={2}>
          {!allOk && (
            <Button
              variant="outlined" size="small"
              startIcon={aiLoading ? <CircularProgress size={14} color="inherit" /> : <BugReport />}
              onClick={onExplainMistake}
              disabled={aiLoading}
              sx={{ borderColor: '#f85149', color: '#f85149', '&:hover': { borderColor: '#f85149', bgcolor: '#3a0a0a' } }}
            >
              Why did I fail?
            </Button>
          )}
          {allOk && (
            <Button
              variant="outlined" size="small"
              startIcon={aiLoading ? <CircularProgress size={14} color="inherit" /> : <RateReview />}
              onClick={onCodeReview}
              disabled={aiLoading}
              sx={{ borderColor: '#58a6ff', color: '#58a6ff', '&:hover': { borderColor: '#58a6ff', bgcolor: '#0d1f3a' } }}
            >
              Review my code
            </Button>
          )}
        </Stack>

        {/* AI result */}
        {aiResult && (
          <Paper sx={{ p: 2, mt: 1, mb: 2, bgcolor: '#0a0e14', border: '1px solid #21262d', textAlign: 'left' }}>
            <Stack direction="row" gap={1} alignItems="center" mb={1}>
              <AutoAwesome sx={{ fontSize: 14, color: '#d29922' }} />
              <Typography variant="caption" fontWeight={600} color="text.secondary">AI Coach</Typography>
            </Stack>
            <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.7, color: '#c9d1d9' }}>
              {aiResult}
            </Typography>
          </Paper>
        )}

        <Button variant="outlined" onClick={onClose} sx={{ mt: 1 }}>
          Back to Editor
        </Button>
      </Paper>
    </Box>
  )
}

// ── Main component ────────────────────────────────────────────────────────────
export default function ProblemPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [problem, setProblem] = useState(null)
  const [progress, setProgress] = useState(null)
  const [code, setCode] = useState(DEFAULT_CODE)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState(null)
  const [tab, setTab] = useState(0)
  const [attempts, setAttempts] = useState([])
  const [notes, setNotes] = useState('')
  const [elapsedSecs, setElapsedSecs] = useState(0)
  const [timerActive, setTimerActive] = useState(false)
  const timerRef = React.useRef(null)
  const [verdict, setVerdict] = useState(null)
  const [expandedAttempt, setExpandedAttempt] = useState(null)
  const notesSaveRef = useRef(null)
  // AI Coach state
  const [aiLoading, setAiLoading] = useState(false)
  const [aiHintResult, setAiHintResult] = useState(null)
  const [aiHintOpen, setAiHintOpen] = useState(false)
  const [verdictAiResult, setVerdictAiResult] = useState(null)

  // Clear notes autosave timer on unmount to prevent state updates on dead component
  useEffect(() => {
    return () => clearTimeout(notesSaveRef.current)
  }, [])

  // Timer + AI — reset when switching problems
  useEffect(() => {
    setElapsedSecs(0)
    setTimerActive(false)
    setAiHintResult(null)
    setAiHintOpen(false)
    setVerdictAiResult(null)
  }, [id])

  useEffect(() => {
    if (timerActive) {
      timerRef.current = setInterval(() => setElapsedSecs(s => s + 1), 1000)
    } else {
      clearInterval(timerRef.current)
    }
    return () => clearInterval(timerRef.current)
  }, [timerActive, id])

  useEffect(() => {
    Promise.all([getProblem(id), getProgress(id)])
      .then(([prob, prog]) => {
        setProblem(prob)
        setProgress(prog)
        setNotes(prog?.notes || '')
        if (prog?.best_solution) setCode(prog.best_solution)
        else if (prob.starter_code) setCode(prob.starter_code)
      })
      .catch(console.error)
  }, [id])

  const handleGetHint = async () => {
    setAiLoading(true)
    setAiHintOpen(true)
    setAiHintResult(null)
    try {
      const data = await getAIInsight('hint', { problem_id: parseInt(id) })
      setAiHintResult(data.content)
    } catch {
      setAiHintResult('Could not connect to AI service.')
    } finally {
      setAiLoading(false)
    }
  }

  const handleExplainMistake = async () => {
    if (!verdict) return
    setAiLoading(true)
    setVerdictAiResult(null)
    try {
      const failedCases = verdict.test_results?.filter(r => !r.passed) || []
      const data = await getAIInsight('mistake_explain', {
        problem_id: parseInt(id),
        code,
        failed_cases: failedCases,
      })
      setVerdictAiResult(data.content)
    } catch {
      setVerdictAiResult('Could not connect to AI service.')
    } finally {
      setAiLoading(false)
    }
  }

  const handleCodeReview = async () => {
    setAiLoading(true)
    setVerdictAiResult(null)
    try {
      const data = await getAIInsight('code_review', { problem_id: parseInt(id), code })
      setVerdictAiResult(data.content)
    } catch {
      setVerdictAiResult('Could not connect to AI service.')
    } finally {
      setAiLoading(false)
    }
  }

  const handleRun = useCallback(async () => {
    setRunning(true)
    setResult(null)
    setVerdict(null)
    try {
      const res = await runCode(id, code, 'python', elapsedSecs, 'run')
      setResult(res)
      const prog = await getProgress(id)
      setProgress(prog)
    } catch {
      setResult({ error_message: 'Failed to connect to code runner.', is_correct: false })
    } finally {
      setRunning(false)
    }
  }, [id, code, elapsedSecs])

  const handleSubmit = useCallback(async () => {
    setRunning(true)
    setResult(null)
    setVerdict(null)
    try {
      const res = await runCode(id, code, 'python', elapsedSecs, 'submit')
      setVerdict(res)                      // show verdict screen
      const prog = await getProgress(id)
      setProgress(prog)
    } catch {
      setVerdict({ error_message: 'Failed to connect to code runner.', is_correct: false })
    } finally {
      setRunning(false)
    }
  }, [id, code, elapsedSecs])

  // Keyboard shortcuts: Ctrl+Enter → Run, Ctrl+Shift+Enter → Submit
  // Must be defined AFTER handleRun and handleSubmit (useCallback is not hoisted)
  useEffect(() => {
    const handler = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault()
        if (e.shiftKey) handleSubmit()
        else handleRun()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [handleRun, handleSubmit])

  const handleStar = async () => {
    await starProblem(id)
    setProgress(p => ({ ...p, is_starred: !p?.is_starred }))
  }

  const handleSaveNotes = useCallback(async (val) => {
    await updateProgress(id, { notes: val ?? notes })
  }, [id, notes])

  // Auto-save notes 1.5s after user stops typing
  const handleNotesChange = (val) => {
    setNotes(val)
    clearTimeout(notesSaveRef.current)
    notesSaveRef.current = setTimeout(() => handleSaveNotes(val), 1500)
  }

  const handleConfidence = async (val) => {
    await updateProgress(id, { confidence: val })
    setProgress(p => ({ ...p, confidence: val }))
  }

  const loadHistory = async () => {
    const hist = await getAttemptHistory(id)
    setAttempts(hist)
  }

  if (!problem) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    )
  }

  const solved = !!progress?.solved_at
  const starred = !!progress?.is_starred
  const examples = problem.test_cases || []
  const description = problem.description || ''

  // Split description — stop before any markdown Example or Constraints heading
  const descMain = description.split(/\n#{1,6}\s*\**\s*(?:Example\s+\d+|Constraints?)\b/i)[0]

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top bar */}
      <Stack
        direction="row" alignItems="center" gap={1} px={2} py={1}
        sx={{ bgcolor: 'background.paper', borderBottom: '1px solid', borderColor: 'divider', flexShrink: 0 }}
      >
        <IconButton size="small" onClick={() => navigate('/tracker')}>
          <ArrowBack fontSize="small" />
        </IconButton>
        <Typography variant="subtitle1" fontWeight={600} sx={{ flexGrow: 1 }} noWrap>
          {problem.title}
        </Typography>
        <Chip label={problem.difficulty} size="small"
          sx={{ color: DIFF_COLOR[problem.difficulty], bgcolor: `${DIFF_COLOR[problem.difficulty]}18`, fontWeight: 600 }} />
        <Chip label={problem.category} size="small" variant="outlined" sx={{ maxWidth: 140 }} />
        {solved
          ? <CheckCircle sx={{ color: 'success.main', fontSize: 20 }} />
          : <RadioButtonUnchecked sx={{ color: 'text.secondary', fontSize: 20 }} />}
        <Tooltip title={starred ? 'Unstar' : 'Star'}>
          <IconButton size="small" onClick={handleStar}>
            {starred ? <Star sx={{ color: '#d29922' }} /> : <StarBorder />}
          </IconButton>
        </Tooltip>
        {problem.leetcode_url && (
          <Tooltip title="Open on LeetCode">
            <IconButton size="small" component="a" href={problem.leetcode_url} target="_blank" rel="noopener">
              <OpenInNew fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
      </Stack>


      {/* Split pane */}
      <Box sx={{ display: 'flex', flexGrow: 1, overflow: 'hidden' }}>

        {/* ── Left: Description ── */}
        <Box sx={{ width: '42%', borderRight: '1px solid', borderColor: 'divider', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <Tabs value={tab} onChange={(_, v) => { setTab(v); if (v === 1) loadHistory() }}
            sx={{ borderBottom: '1px solid', borderColor: 'divider', flexShrink: 0 }}>
            <Tab label="Description" />
            <Tab label="History" icon={<History fontSize="small" />} iconPosition="start" />
            <Tab label="Notes" />
          </Tabs>

          {/* Description tab */}
          {tab === 0 && (
            <Box sx={{ p: 2, overflow: 'auto', flexGrow: 1 }}>

              {/* Tags (topic chips) */}
              {problem.tags?.length > 0 && (
                <Stack direction="row" gap={0.75} flexWrap="wrap" mb={2}>
                  {problem.tags.map(tag => (
                    <Chip key={tag} label={tag} size="small" variant="outlined"
                      sx={{ fontSize: 11, color: '#58a6ff', borderColor: '#1f3550', bgcolor: '#0d1f2d' }} />
                  ))}
                </Stack>
              )}

              {/* Main description */}
              <DescriptionBlock text={descMain} />

              {/* Examples — only show ones with an expected output */}
              {examples.filter(ex => ex.expected_output?.trim()).length > 0 && (
                <Box mt={2.5}>
                  <Typography variant="subtitle2" fontWeight={600} mb={1.5} color="text.secondary">
                    EXAMPLES
                  </Typography>
                  {examples.filter(ex => ex.expected_output?.trim()).map((ex, i) => (
                    <ExampleBox key={i} example={ex} index={i} />
                  ))}
                </Box>
              )}

              {/* Constraints */}
              {problem.constraints && (
                <Box mt={2.5}>
                  <Typography variant="subtitle2" fontWeight={600} mb={1} color="text.secondary">
                    CONSTRAINTS
                  </Typography>
                  <Paper sx={{ p: 1.5, bgcolor: '#0d1117', border: '1px solid #21262d' }}>
                    {problem.constraints.split('\n').map((line, i) => (
                      <Typography key={i} variant="body2" sx={{
                        fontFamily: 'JetBrains Mono, monospace', fontSize: 12.5,
                        color: '#e6edf3', lineHeight: 1.9,
                      }}>
                        • {line}
                      </Typography>
                    ))}
                  </Paper>
                </Box>
              )}

              {/* Hints */}
              <HintsSection hints={problem.hints} />

              {/* AI Coach */}
              <Box mt={2}>
                <Button
                  size="small"
                  startIcon={aiLoading && aiHintOpen ? <CircularProgress size={14} color="inherit" /> : <AutoAwesome sx={{ color: '#d29922' }} />}
                  onClick={aiHintOpen ? () => setAiHintOpen(false) : handleGetHint}
                  endIcon={aiHintOpen ? <ExpandLess /> : <ExpandMore />}
                  disabled={aiLoading && !aiHintOpen}
                  sx={{ color: '#d29922', mb: 1 }}
                >
                  AI Hints
                </Button>
                <Collapse in={aiHintOpen}>
                  {aiHintResult ? (
                    <Paper sx={{ p: 2, bgcolor: '#0d1117', border: '1px solid #2b2000' }}>
                      <Stack direction="row" gap={1} alignItems="center" mb={1}>
                        <AutoAwesome sx={{ fontSize: 14, color: '#d29922' }} />
                        <Typography variant="caption" fontWeight={600} color="text.secondary">AI Coach</Typography>
                      </Stack>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.8, color: '#c9d1d9' }}>
                        {aiHintResult}
                      </Typography>
                    </Paper>
                  ) : aiLoading ? (
                    <Box sx={{ p: 2, display: 'flex', gap: 1, alignItems: 'center' }}>
                      <CircularProgress size={16} />
                      <Typography variant="caption" color="text.secondary">Generating hints…</Typography>
                    </Box>
                  ) : null}
                </Collapse>
              </Box>

              {/* Progress summary */}
              {progress && (
                <Box mt={3} pt={2} sx={{ borderTop: '1px solid #21262d' }}>
                  <Typography variant="caption" color="text.secondary" display="block" mb={1}>YOUR PROGRESS</Typography>
                  <Stack direction="row" gap={1} flexWrap="wrap">
                    <Chip size="small" label={`${progress.total_attempts || 0} attempts`} />
                    {solved && <Chip size="small" label="Solved ✓" color="success" />}
                    {progress.confidence > 0 && (
                      <Chip size="small" label={`Confidence ${progress.confidence}/5`} />
                    )}
                  </Stack>
                </Box>
              )}
            </Box>
          )}

          {/* History tab */}
          {tab === 1 && (
            <Box sx={{ p: 2, overflow: 'auto', flexGrow: 1 }}>
              {attempts.length === 0 ? (
                <Typography color="text.secondary">No attempts yet.</Typography>
              ) : attempts.map((a) => (
                <Paper key={a.id} sx={{ p: 1.5, mb: 1, bgcolor: '#0d1117', border: '1px solid #21262d' }}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Stack direction="row" gap={1} alignItems="center">
                      <Typography variant="caption" color="text.secondary">
                        #{a.attempt_number} · {new Date(a.submitted_at).toLocaleString()}
                      </Typography>
                      {a.time_spent_secs > 0 && (
                        <Typography variant="caption" color="text.secondary">
                          · {formatTime(a.time_spent_secs)}
                        </Typography>
                      )}
                    </Stack>
                    <Stack direction="row" gap={1} alignItems="center">
                      <Chip size="small" label={a.is_correct ? 'Passed' : 'Failed'}
                        color={a.is_correct ? 'success' : 'error'} />
                      <IconButton size="small" onClick={() => setExpandedAttempt(expandedAttempt === a.id ? null : a.id)}>
                        {expandedAttempt === a.id ? <ExpandLess fontSize="small" /> : <ExpandMore fontSize="small" />}
                      </IconButton>
                    </Stack>
                  </Stack>
                  {a.error_type && expandedAttempt !== a.id && (
                    <Typography variant="caption" color="error.main" display="block" mt={0.5}>
                      {a.error_type}
                    </Typography>
                  )}
                  <Collapse in={expandedAttempt === a.id}>
                    {a.code && (
                      <Box component="pre" sx={{
                        mt: 1, p: 1.5, bgcolor: '#161b22', borderRadius: 1,
                        fontFamily: 'JetBrains Mono, monospace', fontSize: 11.5,
                        color: '#e6edf3', whiteSpace: 'pre-wrap', overflowX: 'auto',
                        border: '1px solid #30363d', maxHeight: 300, overflow: 'auto',
                      }}>
                        {a.code}
                      </Box>
                    )}
                    {a.error_type && (
                      <Typography variant="caption" color="error.main" display="block" mt={0.5}>
                        {a.error_type}: {a.error_message?.slice(0, 200)}
                      </Typography>
                    )}
                  </Collapse>
                </Paper>
              ))}
            </Box>
          )}

          {/* Notes tab */}
          {tab === 2 && (
            <Box sx={{ p: 2, flexGrow: 1, display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              {/* Confidence rating */}
              <Box>
                <Typography variant="caption" color="text.secondary" fontWeight={600} display="block" mb={0.75}>
                  CONFIDENCE
                </Typography>
                <Stack direction="row" gap={0.5}>
                  {[1,2,3,4,5].map(n => (
                    <Box
                      key={n}
                      onClick={() => handleConfidence(n)}
                      sx={{
                        px: 1.5, py: 0.4, borderRadius: 1, cursor: 'pointer',
                        border: `1px solid ${(progress?.confidence || 0) >= n ? '#d29922' : '#30363d'}`,
                        bgcolor: (progress?.confidence || 0) >= n ? '#2b1f07' : 'transparent',
                        fontSize: 12, fontWeight: 600,
                        color: (progress?.confidence || 0) >= n ? '#d29922' : '#8b949e',
                        transition: 'all 0.15s',
                        '&:hover': { borderColor: '#d29922', color: '#d29922' },
                      }}
                    >
                      {n}
                    </Box>
                  ))}
                  <Typography variant="caption" color="text.secondary" sx={{ ml: 1, alignSelf: 'center' }}>
                    {['', 'Barely', 'Shaky', 'Ok', 'Good', 'Solid'][progress?.confidence || 0]}
                  </Typography>
                </Stack>
              </Box>
              <TextField multiline fullWidth rows={12} value={notes}
                onChange={e => handleNotesChange(e.target.value)}
                placeholder="Your notes, approach, patterns, edge cases…"
                variant="outlined"
                sx={{ '& .MuiOutlinedInput-root': { fontFamily: 'JetBrains Mono, monospace', fontSize: 13 } }}
              />
              <Typography variant="caption" color="text.secondary">Auto-saved</Typography>
            </Box>
          )}
        </Box>

        {/* ── Right: Editor + Test Cases ── */}
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}>
          {/* Verdict overlay */}
          {verdict && (
            <VerdictScreen
              verdict={verdict}
              problem={problem}
              elapsedSecs={elapsedSecs}
              onClose={() => { setVerdict(null); setVerdictAiResult(null) }}
              onExplainMistake={handleExplainMistake}
              onCodeReview={handleCodeReview}
              aiLoading={aiLoading}
              aiResult={verdictAiResult}
            />
          )}
          {/* Toolbar */}
          <Stack direction="row" alignItems="center" gap={1} px={2} py={1}
            sx={{ borderBottom: '1px solid', borderColor: 'divider', bgcolor: '#0d1117', flexShrink: 0 }}>
            <Chip label="Python 3" size="small" variant="outlined" />
            <Box sx={{ flexGrow: 1 }} />
            {/* Solve timer */}
            <Chip
              label={formatTime(elapsedSecs)}
              size="small"
              onClick={() => setTimerActive(a => !a)}
              sx={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 12, fontWeight: 600,
                color: timerActive ? '#e6edf3' : '#8b949e',
                bgcolor: timerActive ? '#1a2a1a' : '#1a1a1a',
                border: `1px solid ${timerActive ? '#3fb950' : '#30363d'}`,
                cursor: 'pointer',
              }}
            />
            <Button
              variant="outlined" size="small"
              startIcon={running ? <CircularProgress size={14} color="inherit" /> : <PlayArrow />}
              onClick={handleRun} disabled={running}
              sx={{ borderColor: '#3fb950', color: '#3fb950', '&:hover': { borderColor: '#3fb950', bgcolor: '#1a3a1a' } }}
            >
              {running ? 'Running…' : 'Run'}
            </Button>
            <Button
              variant="contained" size="small"
              startIcon={running ? <CircularProgress size={14} color="inherit" /> : <Send sx={{ fontSize: 14 }} />}
              onClick={handleSubmit} disabled={running}
              sx={{ bgcolor: '#238636', '&:hover': { bgcolor: '#2ea043' } }}
            >
              Submit
            </Button>
          </Stack>

          {running && <LinearProgress color="success" sx={{ height: 2, flexShrink: 0 }} />}

          {/* Monaco Editor — shrinks to make room for test panel */}
          <Box sx={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>
            <Editor
              height="100%"
              language="python"
              value={code}
              onChange={v => setCode(v || '')}
              theme="vs-dark"
              options={{
                fontSize: 14,
                fontFamily: "'JetBrains Mono', monospace",
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                lineNumbers: 'on',
                tabSize: 4,
                insertSpaces: true,
                wordWrap: 'on',
                padding: { top: 12 },
              }}
            />
          </Box>

          {/* Test Case Panel — always visible */}
          <TestCasePanel
            testCases={problem?.test_cases}
            result={result}
            running={running}
          />
        </Box>
      </Box>
    </Box>
  )
}
