import React, { useEffect, useRef, useState } from 'react'
import { Search } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'
import { AuthUser } from '../lib/api'

type TopBarProps = {
  user: AuthUser | null
  onLogout: () => void
  onLogin: () => void
}

export default function TopBar({ user, onLogout, onLogin }: TopBarProps){
  const [menuOpen, setMenuOpen] = useState(false)
  const [query, setQuery] = useState('')
  const menuRef = useRef<HTMLDivElement | null>(null)
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    const nextQuery = new URLSearchParams(location.search).get('q') || ''
    setQuery(nextQuery)
  }, [location.pathname, location.search])

  function applySearch(pathname: string, value: string) {
    const params = new URLSearchParams(location.search)
    if (value) {
      params.set('q', value)
    } else {
      params.delete('q')
    }
    const nextQuery = params.toString()
    navigate(nextQuery ? `${pathname}?${nextQuery}` : pathname)
  }

  function handleSearchSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const value = query.trim()
    if (!value) {
      applySearch(location.pathname, '')
      return
    }

    const normalized = value.toLowerCase()
    if (normalized === 'home') {
      navigate('/')
      return
    }
    if (normalized.includes('session')) {
      applySearch('/sessions', value)
      return
    }
    if (normalized.includes('analytics') || normalized.includes('stat') || normalized.includes('dashboard')) {
      applySearch('/stats', value)
      return
    }
    if (normalized.includes('chat')) {
      applySearch('/chat', value)
      return
    }
    if (normalized.includes('repo') || normalized.includes('ingest')) {
      navigate('/repo')
      return
    }

    if (location.pathname === '/stats' || location.pathname === '/sessions' || location.pathname === '/chat') {
      applySearch(location.pathname, value)
      return
    }

    applySearch('/stats', value)
  }

  useEffect(() => {
    function handleDocumentClick(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false)
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', handleDocumentClick)
    document.addEventListener('keydown', handleEscape)
    return () => {
      document.removeEventListener('mousedown', handleDocumentClick)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [])

  const displayName = (() => {
    const source = user?.email || user?.name || 'Signed out'
    if (!source.includes('@')) return source
    return source.split('@')[0].replace(/[._-]+/g, ' ')
  })()
  const avatarLabel = (displayName || 'U').slice(0, 1).toUpperCase()

  return (
    <header className="relative z-20 h-16 flex items-center gap-4 px-6 border-b border-white/6 bg-[#0b1020]/85 backdrop-blur-md shrink-0">
      <div className="flex items-center gap-3 w-full min-w-0">
        <form
          onSubmit={handleSearchSubmit}
          className="flex items-center gap-3 w-full max-w-2xl rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 shadow-soft-lg backdrop-blur-sm focus-within:border-accent/40 focus-within:bg-white/7"
        >
          <Search size={17} className="shrink-0 text-gray-300" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search sessions, files, commands..."
            className="w-full bg-transparent outline-none placeholder:text-muted text-sm text-white"
          />
        </form>
      </div>
      <div ref={menuRef} className="relative shrink-0">
        <button
          type="button"
          onClick={() => setMenuOpen((next) => !next)}
          className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-3 py-2 max-w-[240px] text-left transition hover:bg-white/10"
        >
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-white/10 bg-white/10 text-xs font-semibold uppercase text-white">
            {avatarLabel}
          </div>
          <div className="hidden md:block min-w-0">
            <div className="text-sm font-medium text-white truncate">{displayName}</div>
            <div className="text-xs text-muted truncate">{user ? 'Signed in' : 'Sign in to analyze repositories'}</div>
          </div>
          <div className="text-white/60">▾</div>
        </button>

        {menuOpen && (
          <div className="absolute right-0 mt-2 w-56 overflow-hidden rounded-2xl border border-white/10 bg-[#10182a] shadow-soft-lg">
            <div className="border-b border-white/8 px-3 py-3">
              <div className="text-sm font-medium text-white truncate">{displayName}</div>
              <div className="text-xs text-muted truncate">{user?.email || 'Signed out'}</div>
            </div>
            <div className="p-2">
              <button onClick={() => { setMenuOpen(false); window.location.assign('/'); }} className="w-full rounded-xl px-3 py-2 text-left text-sm text-white transition hover:bg-white/8">Home</button>
              <button onClick={() => { setMenuOpen(false); window.location.assign('/sessions'); }} className="w-full rounded-xl px-3 py-2 text-left text-sm text-white transition hover:bg-white/8">My sessions</button>
              {!user && (
                <button onClick={() => { setMenuOpen(false); onLogin(); }} className="w-full rounded-xl px-3 py-2 text-left text-sm text-white transition hover:bg-white/8">Sign in</button>
              )}
              {user && (
                <button onClick={() => { setMenuOpen(false); onLogout(); }} className="mt-2 w-full rounded-xl px-3 py-2 text-left text-sm text-red-200 transition hover:bg-red-500/10">Logout</button>
              )}
            </div>
          </div>
        )}
      </div>
    </header>
  )
}
