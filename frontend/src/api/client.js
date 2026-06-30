import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Bootstrap token from localStorage on cold load
const _saved = localStorage.getItem('algomaster_token')
if (_saved) api.defaults.headers.common['Authorization'] = `Bearer ${_saved}`

// Redirect to /login on 401
api.interceptors.response.use(
  res => res,
  err => {
    if (err?.response?.status === 401 && window.location.pathname !== '/login') {
      localStorage.removeItem('algomaster_token')
      localStorage.removeItem('algomaster_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ── Problems ─────────────────────────────────────────────────────────────
export const getProblems = (params = {}) =>
  api.get('/problems', { params }).then(r => r.data)

export const getProblem = (id) =>
  api.get(`/problems/${id}`).then(r => r.data)

export const getProgress = (id) =>
  api.get(`/problems/${id}/progress`).then(r => r.data)

export const updateProgress = (id, data) =>
  api.patch(`/problems/${id}/progress`, data).then(r => r.data)

export const starProblem = (id) =>
  api.post(`/problems/${id}/star`).then(r => r.data)

export const getAllProgress = () =>
  api.get('/problems/progress/all').then(r => r.data)

// ── Code Execution ───────────────────────────────────────────────────────
export const runCode = (problemId, code, language = 'python', timeSpentSecs = 0, mode = 'run') =>
  api.post('/attempts/run', { problem_id: problemId, code, language, time_spent_secs: timeSpentSecs, mode }).then(r => r.data)

export const getAttemptHistory = (problemId) =>
  api.get(`/attempts/problem/${problemId}`).then(r => r.data)

// ── Analytics ────────────────────────────────────────────────────────────
export const getOverviewStats = () =>
  api.get('/analytics/overview').then(r => r.data)

export const getDailyStats = (days = 90) =>
  api.get('/analytics/daily', { params: { days } }).then(r => r.data)

export const getTopicMastery = () =>
  api.get('/analytics/topic-mastery').then(r => r.data)

export const getErrorPatterns = () =>
  api.get('/analytics/error-patterns').then(r => r.data)

export const getMilestones = () =>
  api.get('/analytics/milestones').then(r => r.data)

// ── AI ───────────────────────────────────────────────────────────────────
export const getAIInsight = (insightType, opts = {}) =>
  api.post('/ai/insight', { insight_type: insightType, ...opts }).then(r => r.data)

export const getAIHistory = (limit = 20) =>
  api.get('/ai/history', { params: { limit } }).then(r => r.data)

// ── Settings ─────────────────────────────────────────────────────────────
export const getOpenAIKeyStatus = () =>
  api.get('/settings/openai-key').then(r => r.data)

export const setOpenAIKey = (api_key) =>
  api.post('/settings/openai-key', { api_key }).then(r => r.data)

export const deleteOpenAIKey = () =>
  api.delete('/settings/openai-key').then(r => r.data)

export default api
