import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, sessionExpired } = useAuth()
  if (!isAuthenticated) {
    // sessionExpired is set by AuthContext when the api client's 401
    // interceptor fires (see api/client.js) — a real client-side <Navigate>
    // now, not the hard `window.location.href` reload this used to trigger.
    return <Navigate to={sessionExpired ? '/login?reason=session_expired' : '/login'} replace />
  }
  return children
}
