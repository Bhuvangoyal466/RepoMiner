import React, {useEffect, useState} from 'react'
import { motion } from 'framer-motion'
import MetricCard from '../components/MetricCard'
import { listRepos, listSessions } from '../lib/api'

export default function Home(){
  const [sessions,setSessions] = useState<any[]>([])
  const [repos,setRepos] = useState<any[]>([])

  useEffect(()=>{
    listSessions().then(setSessions).catch(()=>{})
    listRepos().then(setRepos).catch(()=>{})
  },[])

  return (
    <div className="p-6 h-full overflow-auto">
      <div className="grid grid-cols-2 gap-6">
        <section className="col-span-2 md:col-span-1">
          <motion.div initial={{opacity:0, y:8}} animate={{opacity:1,y:0}} className="glass p-6 rounded-2xl border border-white/8">
            <div className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-xs font-medium text-accent-2">
              <span className="h-1.5 w-1.5 rounded-full bg-accent-2" />
              Live workspace
            </div>
            <h1 className="mt-4 text-3xl font-bold">RepoMiner</h1>
            <p className="text-muted mt-2 max-w-xl">Instant codebase intelligence for repositories, sessions, and follow-up analysis. Paste a GitHub URL to get started.</p>
            <div className="mt-5 flex flex-wrap gap-2">
              <a href="/repo" className="px-4 py-2 rounded-lg border border-accent/35 bg-gradient-to-r from-accent to-accent-2 text-white shadow-soft-lg">Process a repository</a>
              <span className="px-3 py-2 rounded-lg border border-white/10 bg-white/5 text-sm text-muted">Recent syncs and reports appear below</span>
            </div>
          </motion.div>
        </section>
        <section>
          <div className="grid grid-cols-1 gap-4">
            <MetricCard title="Sessions" value={sessions.length} sub="Recent processed repositories" />
            <MetricCard title="Tracked repos" value={repos.length} sub="Repos linked to your account" />
          </div>
        </section>
      </div>

      <div className="mt-6 rounded-2xl border border-white/8 bg-white/3 p-4">
        <div className="flex items-center justify-between gap-4 mb-3">
          <div>
            <h3 className="text-xl font-semibold">Tracked Repositories</h3>
            <p className="text-sm text-muted mt-1">Repositories processed under your account.</p>
          </div>
          <div className="hidden md:flex items-center gap-2 text-xs text-muted">
            <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">User-scoped</span>
            <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">Always current</span>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {repos.length===0 && <div className="text-muted">No tracked repositories yet. Process a GitHub repo to populate this area.</div>}
          {repos.map((repo:any) => (
            <div key={repo.repoUrl || repo.repoName} className="glass p-4 rounded-xl border border-white/8">
              <div className="font-semibold leading-snug">{repo.repoName || repo.repoUrl}</div>
              <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted">
                <span className="rounded-full border border-accent/25 bg-accent/10 px-2.5 py-1 text-accent-2">{repo.sessionCount} session(s)</span>
                <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">Updated {repo.lastUpdatedAt}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-6 rounded-2xl border border-white/8 bg-white/3 p-4">
        <div className="flex items-center justify-between gap-4 mb-3">
          <div>
            <h3 className="text-xl font-semibold">Recent Sessions</h3>
            <p className="text-sm text-muted mt-1">A quick snapshot of the latest repositories and activity.</p>
          </div>
          <div className="hidden md:flex items-center gap-2 text-xs text-muted">
            <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">Fresh data</span>
            <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">Readable cards</span>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sessions.length===0 && <div className="text-muted">No sessions yet. Process a repository to populate this area.</div>}
          {sessions.map(s=> (
            <div key={s.id} className="glass p-4 rounded-xl border border-white/8">
              <div className="flex justify-between items-start">
                <div>
                  <div className="font-semibold leading-snug">{s.repoName || s.repoUrl}</div>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs">
                    <span className="rounded-full border border-accent/25 bg-accent/10 px-2.5 py-1 text-accent-2">Indexed</span>
                    <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-muted">Updated {s.updatedAt}</span>
                  </div>
                </div>
                <div className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs text-muted">{s.messageCount || 0} msgs</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
