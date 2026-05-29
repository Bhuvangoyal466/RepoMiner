import React from 'react'
import { NavLink } from 'react-router-dom'
import { Home, Terminal, MessagesSquare, BarChart2, ClockIcon } from 'lucide-react'
import { AuthUser } from '../lib/api'

const NavButton = ({to,label,children}:{to:string,label:string,children:React.ReactNode})=> (
  <NavLink
    to={to}
    className={({isActive})=>[
      'group w-full rounded-xl border px-3 py-3 flex items-center gap-3 transition-all duration-200',
      isActive
        ? 'border-accent/40 bg-gradient-to-r from-accent/20 to-accent2/10 text-white shadow-soft-lg'
        : 'border-white/8 bg-white/4 text-gray-300 hover:border-white/14 hover:bg-white/7 hover:text-white hover:-translate-y-0.5',
    ].join(' ')}
  >
    {({isActive}) => (
      <>
        <span className={`grid h-9 w-9 place-items-center rounded-lg border transition-colors ${isActive ? 'border-accent/50 bg-white/10' : 'border-white/10 bg-white/5 group-hover:border-white/20 group-hover:bg-white/10'}`}>
          {children}
        </span>
        <span className="text-sm font-semibold tracking-wide">{label}</span>
      </>
    )}
  </NavLink>
)

type NavRailProps = {
  user: AuthUser | null
  onLogout: () => void
  onLogin: () => void
}

export default function NavRail({ user, onLogout, onLogin }: NavRailProps){
  return (
    <aside className="w-64 min-w-[64px] p-4 bg-transparent border-r border-white/6 flex flex-col gap-5">
      <div className="rounded-2xl border border-white/8 bg-white/4 p-4 shadow-soft-lg">
        <div className="text-lg font-semibold text-white">RepoMiner</div>
        <div className="mt-1 text-xs text-muted">Code intelligence workspace</div>
        <div className="mt-3 inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-2.5 py-1 text-[11px] font-medium text-accent-2">
          <span className="h-1.5 w-1.5 rounded-full bg-accent-2" />
          {user ? 'Personal workspace' : 'Sign in required'}
        </div>
      </div>
      <div className="text-[11px] uppercase tracking-[0.2em] text-muted px-1">Navigation</div>
      <nav className="flex-1 flex flex-col gap-2">
        <NavButton to="/" label="Home"><Home size={18} /></NavButton>
        <NavButton to="/repo" label="Ingest"><Terminal size={18} /></NavButton>
        <NavButton to="/chat" label="Chat"><MessagesSquare size={18} /></NavButton>
        <NavButton to="/stats" label="Analytics"><BarChart2 size={18} /></NavButton>
        <NavButton to="/sessions" label="Sessions"><ClockIcon size={18} /></NavButton>
      </nav>
      <div className="rounded-xl border border-white/8 bg-white/4 p-3 text-xs text-muted">
        <div className="text-white font-medium">Signed in as</div>
        <div className="mt-1 text-sm text-white">{user ? (user.name || user.email) : 'Signed out'}</div>
        <div className="mt-1 leading-relaxed">{user ? 'Email/password account' : 'Sign in to process repositories and manage sessions.'}</div>
        {user ? (
          <button onClick={onLogout} className="mt-3 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-white hover:bg-white/10">Logout</button>
        ) : (
          <button onClick={onLogin} className="mt-3 w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-white hover:bg-white/10">Sign in</button>
        )}
      </div>
      <div className="text-xs text-muted px-2">v0.1 • Local</div>
    </aside>
  )
}
