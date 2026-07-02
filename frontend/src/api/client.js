import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Bootstrap token from localStorage on cold load
const _saved = localStorage.getItem('algomaster_token')
if (_saved) api.defaults.headers.common['Authorization'] = `Bearer ${_saved}`

// On 401, clear the stored session and notify the app so it can redirect
// via React Router. This file lives outside the React tree, so it can't
// call useNavigate() directly — it previously used a hard
// `window.location.href` redirect instead, which threw away all client
// state and forced a full page (re-)download just to show the login form.
// Dispatching an event lets AuthProvider (which *is* inside the Router)
// react with a normal client-side navigation instead.
api.interceptors.response.use(
  res => res,
  err => {
    if (err?.response?.status === 401 && window.location.pathname !== '/login') {
      localStorage.removeItem('algomaster_token')
      localStorage.removeItem('algomaster_user')
      window.dispatchEvent(new CustomEvent('algomaster:session-expired'))
    }
    return Promise.reject(err)
  }
)

// ── Auth ─────────────────────────────────────────────────────────────────
export const getMe = () =>
  api.get('/auth/me').then(r => r.data)

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

// ── Interview / Readiness ─────────────────────────────────────────────────
export const submitAssessment = (data) =>
  api.post('/interview/assessment', data).then(r => r.data)

export const listAssessments = (limit = 50) =>
  api.get('/interview/assessments', { params: { limit } }).then(r => r.data)

export const getAssessmentForProblem = (id) =>
  api.get(`/interview/assessment/${id}`).then(r => r.data)

export const getInterviewOptions = () =>
  api.get('/interview/options').then(r => r.data)

export const getInterviewReadiness = () =>
  api.get('/interview/readiness').then(r => r.data)

export const getPatternStats = () =>
  api.get('/interview/pattern-stats').then(r => r.data)

export const getReviewsDue = () =>
  api.get('/interview/reviews/due').then(r => r.data)

export const getAllReviews = () =>
  api.get('/interview/reviews/all').then(r => r.data)

export const addToReview = (problemId) =>
  api.post('/interview/reviews/add', { problem_id: problemId }).then(r => r.data)

export const completeReview = (problemId, quality) =>
  api.post('/interview/reviews/complete', { problem_id: problemId, quality }).then(r => r.data)

export const removeFromReview = (problemId) =>
  api.delete(`/interview/reviews/${problemId}`).then(r => r.data)

export const listMistakes = (limit = 200) =>
  api.get('/interview/mistakes', { params: { limit } }).then(r => r.data)

export const getMistakeSummary = () =>
  api.get('/interview/mistakes/summary').then(r => r.data)

export const logMistake = (data) =>
  api.post('/interview/mistake', data).then(r => r.data)

export const listContests = () =>
  api.get('/interview/contests').then(r => r.data)

export const logContest = (data) =>
  api.post('/interview/contest', data).then(r => r.data)

export const deleteContest = (id) =>
  api.delete(`/interview/contest/${id}`).then(r => r.data)

export const getDSFluency = () =>
  api.get('/interview/ds-fluency').then(r => r.data)

export const updateDSFluency = (ratings) =>
  api.post('/interview/ds-fluency', { ratings }).then(r => r.data)

// ── Settings ─────────────────────────────────────────────────────────────
export const getOpenAIKeyStatus = () =>
  api.get('/settings/openai-key').then(r => r.data)

export const setOpenAIKey = (api_key) =>
  api.post('/settings/openai-key', { api_key }).then(r => r.data)

export const deleteOpenAIKey = () =>
  api.delete('/settings/openai-key').then(r => r.data)

export default api
