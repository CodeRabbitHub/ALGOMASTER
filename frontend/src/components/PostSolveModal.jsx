import React, { useState, useEffect } from 'react'
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Box, Typography, Button, Stack, Chip, TextField,
  Slider, ToggleButton, ToggleButtonGroup, Tooltip,
  LinearProgress, IconButton, FormControlLabel, Switch,
  Stepper, Step, StepLabel, Divider,
} from '@mui/material'
import {
  Close, CheckCircle, Psychology, Speed, BugReport,
  RecordVoiceOver, Warning, School, Schedule,
  NavigateNext, NavigateBefore,
} from '@mui/icons-material'
import { submitAssessment } from '../api/client'

// ── Reusable chip-select ──────────────────────────────────────────────────────
function ChipSelect({ options, selected, onChange, max }) {
  const toggle = (val) => {
    if (selected.includes(val)) {
      onChange(selected.filter(v => v !== val))
    } else if (!max || selected.length < max) {
      onChange([...selected, val])
    }
  }
  return (
    <Stack direction="row" flexWrap="wrap" gap={0.75}>
      {options.map(opt => (
        <Chip
          key={opt}
          label={opt}
          size="small"
          clickable
          onClick={() => toggle(opt)}
          sx={{
            bgcolor: selected.includes(opt) ? '#1f3550' : '#21262d',
            color:   selected.includes(opt) ? '#58a6ff' : '#8b949e',
            border:  selected.includes(opt) ? '1px solid #58a6ff' : '1px solid #30363d',
            '&:hover': { borderColor: '#58a6ff' },
            fontSize: 12,
          }}
        />
      ))}
    </Stack>
  )
}

// ── Step content components ───────────────────────────────────────────────────

function PatternStep({ data, setData, options }) {
  return (
    <Stack gap={2.5}>
      <Box>
        <Typography variant="body2" fontWeight={600} mb={1} color="text.secondary">
          Which pattern did this problem use?
        </Typography>
        <ChipSelect
          options={options.patterns || []}
          selected={data.pattern_identified ? [data.pattern_identified] : []}
          onChange={([v]) => setData(d => ({ ...d, pattern_identified: v || null }))}
          max={1}
        />
      </Box>

      <Box>
        <Typography variant="body2" fontWeight={600} mb={1} color="text.secondary">
          Time to identify the pattern
        </Typography>
        <Stack direction="row" gap={2} alignItems="center">
          {[30, 60, 120, 180, 300, 600].map(sec => (
            <Chip
              key={sec}
              label={sec < 60 ? `${sec}s` : `${sec/60}m`}
              size="small"
              clickable
              onClick={() => setData(d => ({ ...d, time_to_pattern_secs: sec }))}
              sx={{
                bgcolor: data.time_to_pattern_secs === sec ? '#1f3550' : '#21262d',
                color:   data.time_to_pattern_secs === sec ? '#58a6ff' : '#8b949e',
                border:  data.time_to_pattern_secs === sec ? '1px solid #58a6ff' : '1px solid #30363d',
              }}
            />
          ))}
        </Stack>
        <Typography variant="caption" color={
          !data.time_to_pattern_secs ? 'text.disabled'
          : data.time_to_pattern_secs <= 120 ? '#3fb950' : '#d29922'
        } sx={{ mt: 0.5, display: 'block' }}>
          {data.time_to_pattern_secs
            ? data.time_to_pattern_secs <= 120
              ? '✓ Under 2 min — excellent pattern recognition'
              : `${Math.round(data.time_to_pattern_secs / 60)}m — aim for under 2 min`
            : 'Select how long it took'}
        </Typography>
      </Box>

      <Box>
        <Typography variant="body2" fontWeight={600} mb={1} color="text.secondary">
          Was your pattern choice correct on the first try?
        </Typography>
        <ToggleButtonGroup
          value={data.pattern_was_correct === null ? null : data.pattern_was_correct ? 'yes' : 'no'}
          exclusive
          onChange={(_, v) => v !== null && setData(d => ({ ...d, pattern_was_correct: v === 'yes' }))}
          size="small"
        >
          <ToggleButton value="yes" sx={{ color: '#3fb950', borderColor: '#30363d', '&.Mui-selected': { bgcolor: '#0d2b15', borderColor: '#3fb950', color: '#3fb950' } }}>
            Yes
          </ToggleButton>
          <ToggleButton value="no" sx={{ color: '#f85149', borderColor: '#30363d', '&.Mui-selected': { bgcolor: '#2b0c0c', borderColor: '#f85149', color: '#f85149' } }}>
            No — explored a wrong approach first
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>

      <Box>
        <Typography variant="body2" fontWeight={600} mb={1} color="text.secondary">
          Wrong approaches explored
        </Typography>
        <Stack direction="row" gap={1}>
          {[0,1,2,3,'4+'].map(n => (
            <Chip
              key={n}
              label={n}
              size="small"
              clickable
              onClick={() => setData(d => ({ ...d, wrong_approaches: n === '4+' ? 4 : n }))}
              sx={{
                bgcolor: data.wrong_approaches === (n === '4+' ? 4 : n) ? '#2b1f07' : '#21262d',
                color:   data.wrong_approaches === (n === '4+' ? 4 : n) ? '#d29922' : '#8b949e',
                border:  data.wrong_approaches === (n === '4+' ? 4 : n) ? '1px solid #d29922' : '1px solid #30363d',
              }}
            />
          ))}
        </Stack>
      </Box>
    </Stack>
  )
}

function ComplexityStep({ data, setData }) {
  return (
    <Stack gap={2.5}>
      <Box>
        <Typography variant="body2" fontWeight={600} mb={1.5} color="text.secondary">
          Complexity journey
        </Typography>
        <Stack gap={1.5}>
          <Stack direction="row" gap={2} alignItems="center">
            <Typography variant="caption" color="text.secondary" sx={{ minWidth: 120 }}>Initial (brute force)</Typography>
            <TextField
              size="small" placeholder="e.g. O(n²)"
              value={data.complexity_initial_time || ''}
              onChange={e => setData(d => ({ ...d, complexity_initial_time: e.target.value }))}
              sx={{ maxWidth: 140, input: { fontFamily: 'monospace', fontSize: 13 } }}
            />
          </Stack>
          <Box sx={{ pl: 15, color: '#8b949e', fontSize: 18 }}>↓</Box>
          <Stack direction="row" gap={2} alignItems="center">
            <Typography variant="caption" color="text.secondary" sx={{ minWidth: 120 }}>Final Time</Typography>
            <TextField
              size="small" placeholder="e.g. O(n)"
              value={data.complexity_final_time || ''}
              onChange={e => setData(d => ({ ...d, complexity_final_time: e.target.value }))}
              sx={{ maxWidth: 140, input: { fontFamily: 'monospace', fontSize: 13, color: '#3fb950' } }}
            />
          </Stack>
          <Stack direction="row" gap={2} alignItems="center">
            <Typography variant="caption" color="text.secondary" sx={{ minWidth: 120 }}>Final Space</Typography>
            <TextField
              size="small" placeholder="e.g. O(1)"
              value={data.complexity_final_space || ''}
              onChange={e => setData(d => ({ ...d, complexity_final_space: e.target.value }))}
              sx={{ maxWidth: 140, input: { fontFamily: 'monospace', fontSize: 13, color: '#3fb950' } }}
            />
          </Stack>
        </Stack>
      </Box>

      <Box>
        <Typography variant="body2" fontWeight={600} mb={1} color="text.secondary">
          Could you explain your solution and its trade-offs clearly?
        </Typography>
        <Typography variant="caption" color="text.secondary" mb={0.75} display="block">
          Communication score (1 = couldn't explain, 10 = crystal clear)
        </Typography>
        <Stack direction="row" gap={1} alignItems="center">
          <Typography variant="caption" color="text.secondary">1</Typography>
          <Slider
            value={data.communication_score || 5}
            onChange={(_, v) => setData(d => ({ ...d, communication_score: v }))}
            min={1} max={10} step={1} marks
            sx={{
              '& .MuiSlider-thumb': { bgcolor: '#58a6ff' },
              '& .MuiSlider-track': { bgcolor: '#58a6ff' },
            }}
          />
          <Typography variant="caption" color="text.secondary">10</Typography>
          <Chip
            label={data.communication_score || 5}
            size="small"
            sx={{ bgcolor: '#1f3550', color: '#58a6ff', minWidth: 32 }}
          />
        </Stack>
      </Box>
    </Stack>
  )
}

function CodingQualityStep({ data, setData, options }) {
  return (
    <Stack gap={2.5}>
      <Box>
        <Typography variant="body2" fontWeight={600} mb={1} color="text.secondary">
          How many runs/submissions until correct?
        </Typography>
        <Stack direction="row" gap={1}>
          {[1,2,3,4,5,6].map(n => (
            <Chip
              key={n}
              label={n === 6 ? '6+' : n}
              size="small"
              clickable
              onClick={() => setData(d => ({ ...d, compile_attempts: n }))}
              sx={{
                bgcolor: data.compile_attempts === n ? (n === 1 ? '#0d2b15' : n <= 3 ? '#2b1f07' : '#2b0c0c') : '#21262d',
                color:   data.compile_attempts === n ? (n === 1 ? '#3fb950' : n <= 3 ? '#d29922' : '#f85149') : '#8b949e',
                border:  data.compile_attempts === n ? `1px solid ${n === 1 ? '#3fb950' : n <= 3 ? '#d29922' : '#f85149'}` : '1px solid #30363d',
              }}
            />
          ))}
        </Stack>
      </Box>

      <Box>
        <Typography variant="body2" fontWeight={600} mb={1} color="text.secondary">
          Bug categories encountered (select all that apply)
        </Typography>
        <ChipSelect
          options={options.bug_categories || []}
          selected={data.bug_categories || []}
          onChange={v => setData(d => ({ ...d, bug_categories: v, bugs_count: v.length }))}
        />
      </Box>

      <Stack direction="row" gap={3}>
        <Box>
          <Typography variant="body2" fontWeight={600} mb={1} color="text.secondary">
            Did you panic or freeze?
          </Typography>
          <ToggleButtonGroup
            value={data.did_panic === null ? null : data.did_panic ? 'yes' : 'no'}
            exclusive
            onChange={(_, v) => v !== null && setData(d => ({ ...d, did_panic: v === 'yes' }))}
            size="small"
          >
            <ToggleButton value="yes" sx={{ color: '#f85149', borderColor: '#30363d', '&.Mui-selected': { bgcolor: '#2b0c0c', borderColor: '#f85149', color: '#f85149' } }}>
              Yes
            </ToggleButton>
            <ToggleButton value="no" sx={{ color: '#3fb950', borderColor: '#30363d', '&.Mui-selected': { bgcolor: '#0d2b15', borderColor: '#3fb950', color: '#3fb950' } }}>
              No
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>

        <Box>
          <Typography variant="body2" fontWeight={600} mb={1} color="text.secondary">
            Used a hint?
          </Typography>
          <ToggleButtonGroup
            value={data.hint_used === null ? null : data.hint_used ? 'yes' : 'no'}
            exclusive
            onChange={(_, v) => v !== null && setData(d => ({ ...d, hint_used: v === 'yes' }))}
            size="small"
          >
            <ToggleButton value="yes" sx={{ borderColor: '#30363d', '&.Mui-selected': { bgcolor: '#2b1f07', borderColor: '#d29922', color: '#d29922' } }}>
              Yes
            </ToggleButton>
            <ToggleButton value="no" sx={{ borderColor: '#30363d', '&.Mui-selected': { bgcolor: '#0d2b15', borderColor: '#3fb950', color: '#3fb950' } }}>
              No
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>
      </Stack>
    </Stack>
  )
}

function EdgeLearningStep({ data, setData, options }) {
  return (
    <Stack gap={2.5}>
      <Box>
        <Typography variant="body2" fontWeight={600} mb={0.5} color="text.secondary">
          Edge cases you identified
        </Typography>
        <FormControlLabel
          control={
            <Switch
              size="small"
              checked={!!data.edge_cases_before_coding}
              onChange={e => setData(d => ({ ...d, edge_cases_before_coding: e.target.checked }))}
              sx={{ '& .MuiSwitch-thumb': { bgcolor: '#58a6ff' } }}
            />
          }
          label={<Typography variant="caption" color="text.secondary">Identified before coding</Typography>}
          sx={{ mb: 1 }}
        />
        <ChipSelect
          options={options.edge_cases || []}
          selected={data.edge_cases_checked || []}
          onChange={v => setData(d => ({ ...d, edge_cases_checked: v }))}
        />
      </Box>

      <Box>
        <Typography variant="body2" fontWeight={600} mb={1} color="text.secondary">
          What did you learn? (new trick, observation, algorithm detail)
        </Typography>
        <TextField
          multiline rows={3} fullWidth
          placeholder="e.g. Learned that you can use a deque for monotonic window problems instead of rebuilding each step..."
          value={data.new_learning || ''}
          onChange={e => setData(d => ({ ...d, new_learning: e.target.value }))}
          sx={{ '& .MuiOutlinedInput-root': { fontSize: 13 } }}
        />
      </Box>

      <Box>
        <Typography variant="body2" fontWeight={600} mb={1} color="text.secondary">
          Confidence after solving (1 = shaky, 5 = could teach it)
        </Typography>
        <Stack direction="row" gap={0.75}>
          {[1,2,3,4,5].map(n => {
            const colors = ['#f85149','#f85149','#d29922','#3fb950','#3fb950']
            const sel = data.confidence_after === n
            return (
              <Box
                key={n}
                onClick={() => setData(d => ({ ...d, confidence_after: n }))}
                sx={{
                  width: 36, height: 36, borderRadius: '50%', cursor: 'pointer',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  border: `2px solid ${sel ? colors[n-1] : '#30363d'}`,
                  bgcolor: sel ? `${colors[n-1]}22` : 'transparent',
                  color: sel ? colors[n-1] : '#8b949e',
                  fontWeight: 700, fontSize: 15,
                  transition: 'all 0.15s',
                  '&:hover': { borderColor: colors[n-1] },
                }}
              >
                {n}
              </Box>
            )
          })}
        </Stack>
      </Box>

      <Box>
        <FormControlLabel
          control={
            <Switch
              checked={!!data.add_to_review}
              onChange={e => setData(d => ({ ...d, add_to_review: e.target.checked }))}
              sx={{ '& .MuiSwitch-thumb': { bgcolor: '#58a6ff' } }}
            />
          }
          label={
            <Stack>
              <Typography variant="body2" fontWeight={600}>Add to Spaced Repetition</Typography>
              <Typography variant="caption" color="text.secondary">
                Schedule this problem for review in 1 day, 6 days, 2+ weeks…
              </Typography>
            </Stack>
          }
        />
      </Box>
    </Stack>
  )
}

// ── Main Modal ────────────────────────────────────────────────────────────────

const STEPS = [
  { label: 'Pattern',    icon: <Psychology /> },
  { label: 'Complexity', icon: <Speed />      },
  { label: 'Coding',     icon: <BugReport />  },
  { label: 'Reflect',    icon: <School />     },
]

const DEFAULT_DATA = {
  pattern_identified: null,
  time_to_pattern_secs: null,
  pattern_was_correct: null,
  wrong_approaches: 0,
  hint_used: false,
  did_panic: false,
  complexity_initial_time: '',
  complexity_final_time: '',
  complexity_final_space: '',
  communication_score: 7,
  compile_attempts: 1,
  bugs_count: 0,
  bug_categories: [],
  edge_cases_checked: [],
  edge_cases_before_coding: true,
  new_learning: '',
  confidence_after: null,
  add_to_review: false,
}

export default function PostSolveModal({ open, onClose, problemId, solveTimeSecs, options }) {
  const [step, setStep] = useState(0)
  const [data, setData] = useState(DEFAULT_DATA)
  const [saving, setSaving] = useState(false)

  // Reset when opened for a new problem
  useEffect(() => {
    if (open) {
      setStep(0)
      setData({ ...DEFAULT_DATA, total_solve_time_secs: solveTimeSecs || null })
    }
  }, [open, problemId])

  const handleSave = async () => {
    setSaving(true)
    try {
      await submitAssessment({ ...data, problem_id: problemId })
    } catch (e) {
      console.error('Assessment save failed:', e)
    } finally {
      setSaving(false)
      onClose()
    }
  }

  const isLast = step === STEPS.length - 1

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          bgcolor: '#0d1117',
          border: '1px solid #30363d',
          borderRadius: 2,
          backgroundImage: 'none',
        },
      }}
    >
      <DialogTitle sx={{ pb: 1.5, pr: 6 }}>
        <Stack direction="row" alignItems="center" gap={1.5}>
          <CheckCircle sx={{ color: '#3fb950', fontSize: 22 }} />
          <Typography fontWeight={700}>Performance Assessment</Typography>
        </Stack>
        <Typography variant="caption" color="text.secondary" mt={0.25} display="block">
          Tracking these metrics builds better interview intuition over time.
        </Typography>
        <IconButton onClick={onClose} size="small" sx={{ position: 'absolute', top: 12, right: 12, color: 'text.secondary' }}>
          <Close fontSize="small" />
        </IconButton>
      </DialogTitle>

      {/* Stepper */}
      <Box sx={{ px: 3, pb: 2 }}>
        <Stepper activeStep={step} alternativeLabel>
          {STEPS.map((s, i) => (
            <Step key={s.label} completed={i < step}>
              <StepLabel
                onClick={() => i < step && setStep(i)}
                sx={{ cursor: i < step ? 'pointer' : 'default' }}
                StepIconProps={{
                  sx: {
                    '&.Mui-completed': { color: '#3fb950' },
                    '&.Mui-active': { color: '#58a6ff' },
                    color: '#30363d',
                  },
                }}
              >
                <Typography variant="caption" sx={{ color: i === step ? '#58a6ff' : i < step ? '#3fb950' : '#8b949e' }}>
                  {s.label}
                </Typography>
              </StepLabel>
            </Step>
          ))}
        </Stepper>
      </Box>

      <Divider sx={{ borderColor: '#21262d' }} />

      <DialogContent sx={{ pt: 2.5, pb: 2 }}>
        {step === 0 && <PatternStep data={data} setData={setData} options={options || {}} />}
        {step === 1 && <ComplexityStep data={data} setData={setData} />}
        {step === 2 && <CodingQualityStep data={data} setData={setData} options={options || {}} />}
        {step === 3 && <EdgeLearningStep data={data} setData={setData} options={options || {}} />}
      </DialogContent>

      <Divider sx={{ borderColor: '#21262d' }} />

      <DialogActions sx={{ px: 3, py: 1.5, gap: 1 }}>
        <Button
          size="small" color="inherit"
          onClick={() => setStep(s => s - 1)}
          disabled={step === 0}
          startIcon={<NavigateBefore />}
          sx={{ color: 'text.secondary' }}
        >
          Back
        </Button>
        <Box sx={{ flexGrow: 1 }} />
        <Button
          size="small"
          onClick={onClose}
          sx={{ color: 'text.secondary' }}
        >
          Skip
        </Button>
        {isLast ? (
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={saving}
            startIcon={<CheckCircle />}
          >
            {saving ? 'Saving…' : 'Save Assessment'}
          </Button>
        ) : (
          <Button
            variant="contained"
            onClick={() => setStep(s => s + 1)}
            endIcon={<NavigateNext />}
          >
            Next
          </Button>
        )}
      </DialogActions>
    </Dialog>
  )
}
