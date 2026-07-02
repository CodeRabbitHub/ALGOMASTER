import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import api, { getMe } from '../api/client'

const AuthContext = createContext(null)

const TOKEN_KEY = 'algomaster_token'
const USER_KEY  = 'algomaster_user'

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [user,  setUser]  = useState(() => {
    try { return JSON.parse(localStorage.getItem(USER_KEY)) } catch { return null }
  })
  // Reflects any in-flight login()/register() call. (Individual pages are
  // free to track their own local loading state too — e.g. LoginPage does,
  // for form-level disabling — but this is here so any consumer of
  // useAuth() can react to auth calls in flight without wiring its own.)
  const [loading, setLoading] = useState(false)
  // Set when the api client's 401 interceptor fires (see api/client.js),
  // so ProtectedRoute can redirect to /login?reason=session_expired
  // instead of a bare /login — distinguishing "your session expired" from
  // "you were never logged in".
  const [sessionExpired, setSessionExpired] = useState(false)

  useEffect(() => {
    const onSessionExpired = () => {
      setSessionExpired(true)
      setToken(null)
      setUser(null)
    }
    window.addEventListener('algomaster:session-expired', onSessionExpired)
    return () => window.removeEventListener('algomaster:session-expired', onSessionExpired)
  }, [])

  // Keep axios header in sync with token
  useEffect(() => {
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
    } else {
      delete api.defaults.headers.common['Authorization']
    }
  }, [token])

  // Sessions started before `is_admin` was added to the stored user object
  // (or before a role change) won't have it — refresh once from /auth/me
  // whenever we have a token so admin-only UI (e.g. the Settings page's
  // OpenAI key controls) reflects the account's real role without forcing
  // a re-login.
  useEffect(() => {
    if (!token) return
    getMe()
      .then(me => {
        setUser(prev => {
          const merged = { ...(prev || {}), id: me.id, username: me.username, email: me.email, is_admin: !!me.is_admin }
          localStorage.setItem(USER_KEY, JSON.stringify(merged))
          return merged
        })
      })
      .catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const login = useCallback(async (email, password) => {
    setLoading(true)
    try {
      const res = await api.post('/auth/login', { email, password })
      const { access_token, user_id, username, email: userEmail, is_admin } = res.data
      const userObj = { id: user_id, username, email: userEmail, is_admin: !!is_admin }
      localStorage.setItem(TOKEN_KEY, access_token)
      localStorage.setItem(USER_KEY, JSON.stringify(userObj))
      // Set header immediately so any fetch triggered by the subsequent
      // navigation fires with auth — don't wait for the useEffect cycle.
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      setToken(access_token)
      setUser(userObj)
      setSessionExpired(false)
      return userObj
    } finally {
      setLoading(false)
    }
  }, [])

  const register = useCallback(async (email, username, password) => {
    setLoading(true)
    try {
      const res = await api.post('/auth/register', { email, username, password })
      const { access_token, user_id, email: userEmail, is_admin } = res.data
      const userObj = { id: user_id, username, email: userEmail, is_admin: !!is_admin }
      localStorage.setItem(TOKEN_KEY, access_token)
      localStorage.setItem(USER_KEY, JSON.stringify(userObj))
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
      setToken(access_token)
      setUser(userObj)
      setSessionExpired(false)
      return userObj
    } finally {
      setLoading(false)
    }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setToken(null)
    setUser(null)
    setSessionExpired(false)
  }, [])

  const isAuthenticated = !!token && !!user

  return (
    <AuthContext.Provider value={{ user, token, isAuthenticated, loading, login, register, logout, sessionExpired }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
