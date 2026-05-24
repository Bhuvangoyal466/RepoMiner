import React, { useEffect, useState } from 'react'
import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom'
import Home from './pages/Home'
import RepoWorkspace from './pages/RepoWorkspace'
import Chat from './pages/Chat'
import Dashboard from './pages/Dashboard'
import Sessions from './pages/Sessions'
import NavRail from './components/NavRail'
import TopBar from './components/TopBar'
import Login from './pages/Login'
import { AuthUser, loginWithEmailPassword, logout, me } from './lib/api'

export default function App() {
  const [user, setUser] = useState<AuthUser | null>(null)
  const location = useLocation()
  const navigate = useNavigate()
  const loginReturnTo = new URLSearchParams(location.search).get('returnTo') || '/'

  useEffect(() => {
    me()
      .then((currentUser) => setUser(currentUser))
      .catch(() => setUser(null))
  }, [])

  async function handleLogin(email: string, password: string, returnTo = '/') {
    const currentUser = await loginWithEmailPassword(email, password)
    setUser(currentUser)
    navigate(returnTo, { replace: true })
  }

  async function handleLogout() {
    await logout()
    setUser(null)
    navigate('/', { replace: true })
  }

  function handleOpenLogin() {
    navigate(`/login?returnTo=${encodeURIComponent(location.pathname)}`)
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to={loginReturnTo} replace /> : <Login onLogin={handleLogin} />}
      />
      <Route
        path="*"
        element={
          <div className="app-root h-screen w-screen flex bg-gray-900 text-gray-100">
            <NavRail user={user} onLogout={handleLogout} onLogin={handleOpenLogin} />
            <div className="flex-1 flex flex-col min-w-0">
              <TopBar user={user} onLogout={handleLogout} onLogin={handleOpenLogin} />
              <main className="flex-1 overflow-hidden min-w-0">
                <Routes>
                  <Route path="/" element={<Home />} />
                  <Route path="/repo" element={user ? <RepoWorkspace /> : <Navigate to={`/login?returnTo=${encodeURIComponent(location.pathname)}`} replace />} />
                  <Route path="/chat" element={user ? <Chat /> : <Navigate to={`/login?returnTo=${encodeURIComponent(location.pathname)}`} replace />} />
                  <Route path="/stats" element={user ? <Dashboard /> : <Navigate to={`/login?returnTo=${encodeURIComponent(location.pathname)}`} replace />} />
                  <Route path="/sessions" element={user ? <Sessions /> : <Navigate to={`/login?returnTo=${encodeURIComponent(location.pathname)}`} replace />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </main>
            </div>
          </div>
        }
      />
    </Routes>
  )
}
