import React, { useMemo } from 'react'
import { Box, Tooltip, Typography, Stack } from '@mui/material'

const CELL = 13
const GAP = 2
const WEEKS = 52

function getColor(count) {
  if (!count || count === 0) return '#161b22'
  if (count === 1) return '#0e4429'
  if (count <= 3) return '#006d32'
  if (count <= 6) return '#26a641'
  return '#39d353'
}

export default function GitHubHeatmap({ data }) {
  // Build map: date string → solved count
  const dayMap = useMemo(() => {
    const map = {}
    data.forEach(d => {
      if (d.day) map[d.day.slice(0, 10)] = d.solved || 0
    })
    return map
  }, [data])

  // Build grid: 52 weeks × 7 days
  const grid = useMemo(() => {
    const today = new Date()
    const start = new Date(today)
    start.setDate(start.getDate() - WEEKS * 7)
    // Align to Sunday
    start.setDate(start.getDate() - start.getDay())

    const weeks = []
    let current = new Date(start)
    for (let w = 0; w < WEEKS; w++) {
      const week = []
      for (let d = 0; d < 7; d++) {
        const iso = current.toISOString().slice(0, 10)
        week.push({ date: iso, count: dayMap[iso] || 0 })
        current.setDate(current.getDate() + 1)
      }
      weeks.push(week)
    }
    return weeks
  }, [dayMap])

  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  const DAYS = ['', 'Mon', '', 'Wed', '', 'Fri', '']

  return (
    <Box>
      <Box sx={{ overflowX: 'auto' }}>
        <Box sx={{ display: 'flex', gap: '2px' }}>
          {/* Day labels */}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: `${GAP}px`, mr: 0.5 }}>
            {DAYS.map((d, i) => (
              <Box key={i} sx={{ height: CELL, display: 'flex', alignItems: 'center' }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: 9, width: 24 }}>{d}</Typography>
              </Box>
            ))}
          </Box>

          {/* Week columns */}
          {grid.map((week, wi) => (
            <Box key={wi} sx={{ display: 'flex', flexDirection: 'column', gap: `${GAP}px` }}>
              {week.map((cell, di) => (
                <Tooltip
                  key={di}
                  title={`${cell.date}: ${cell.count} solved`}
                  placement="top"
                  arrow
                >
                  <Box
                    sx={{
                      width: CELL, height: CELL,
                      bgcolor: getColor(cell.count),
                      borderRadius: '2px',
                      cursor: 'default',
                      transition: 'transform 0.1s',
                      '&:hover': { transform: 'scale(1.3)' },
                    }}
                  />
                </Tooltip>
              ))}
            </Box>
          ))}
        </Box>
      </Box>

      {/* Legend */}
      <Stack direction="row" gap={0.5} alignItems="center" mt={2}>
        <Typography variant="caption" color="text.secondary" mr={1}>Less</Typography>
        {[0, 1, 3, 6, 9].map(v => (
          <Box key={v} sx={{ width: CELL, height: CELL, bgcolor: getColor(v), borderRadius: '2px' }} />
        ))}
        <Typography variant="caption" color="text.secondary" ml={1}>More</Typography>
      </Stack>
    </Box>
  )
}
