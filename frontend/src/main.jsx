import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null } }
  static getDerivedStateFromError(e) { return { error: e } }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 40, fontFamily: 'monospace', color: '#f85149', background: '#0d1117', minHeight: '100vh' }}>
          <h2 style={{ marginBottom: 16 }}>⚠️ App crashed — check browser console (F12)</h2>
          <pre style={{ whiteSpace: 'pre-wrap', color: '#e6edf3', background: '#161b22', padding: 20, borderRadius: 8 }}>
            {this.state.error.toString()}
            {'\n\n'}
            {this.state.error.stack}
          </pre>
        </div>
      )
    }
    return this.props.children
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <ErrorBoundary>
    <App />
  </ErrorBoundary>
)
