import React, {useEffect, useState} from 'react'
import { useNavigate } from 'react-router-dom'
import { activateSession, deleteSession, listRepos, listSessions } from '../lib/api'

export default function Sessions(){
  const [sessions,setSessions] = useState<any[]>([])
  const [repos,setRepos] = useState<any[]>([])
  const [busyId,setBusyId] = useState<string | null>(null)
  const navigate = useNavigate()
  useEffect(()=>{listSessions().then(setSessions).catch(()=>{})},[])
  useEffect(()=>{listRepos().then(setRepos).catch(()=>{})},[])

  async function handleResume(sessionId: string) {
    setBusyId(sessionId)
    try {
      await activateSession(sessionId)
      navigate(`/chat?sessionId=${encodeURIComponent(sessionId)}`)
    } finally {
      setBusyId(null)
    }
  }

  async function handleDelete(sessionId: string) {
    const confirmed = window.confirm('Delete this session? This cannot be undone.')
    if (!confirmed) return
    setBusyId(sessionId)
    try {
      await deleteSession(sessionId)
      setSessions(prev => prev.filter(session => session.id !== sessionId))
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="p-6 h-full overflow-auto">
      <h2 className="text-2xl font-semibold mb-4">Sessions</h2>
      <div className="mb-6 rounded-2xl border border-white/8 bg-white/3 p-4">
        <div className="text-lg font-semibold">Tracked Repositories</div>
        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
          {repos.length===0 && <div className="text-muted">No tracked repositories yet.</div>}
          {repos.map((repo:any) => (
            <div key={repo.repoUrl || repo.repoName} className="glass p-4 rounded-xl border border-white/8">
              <div className="font-semibold">{repo.repoName || repo.repoUrl}</div>
              <div className="mt-2 text-xs text-muted">{repo.sessionCount} session(s) • {repo.lastUpdatedAt}</div>
            </div>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sessions.length===0 && <div className="text-muted">No saved sessions</div>}
        {sessions.map(s=> (
          <div key={s.id} className="glass p-4 rounded-md flex justify-between items-center">
            <div>
              <div className="font-semibold">{s.repoName||s.repoUrl}</div>
              <div className="text-sm text-muted">{s.updatedAt}</div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={()=>handleResume(s.id)}
                disabled={busyId === s.id}
                className="px-3 py-1 rounded-md bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 font-semibold shadow-sm transition hover:from-amber-400 hover:to-orange-400 disabled:opacity-60"
              >
                Resume
              </button>
              <button
                onClick={()=>handleDelete(s.id)}
                disabled={busyId === s.id}
                className="px-3 py-1 rounded-md bg-red-500 text-white font-semibold shadow-sm transition hover:bg-red-400 disabled:opacity-60"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
