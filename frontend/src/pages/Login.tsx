import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { ShieldCheck, Sparkles } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'

type LoginProps = {
  onLogin: (email: string, password: string, returnTo?: string) => Promise<void>
}

export default function Login({ onLogin }: LoginProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [searchParams] = useSearchParams()
  const returnTo = searchParams.get('returnTo') || '/'

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setLoading(true)
    setMessage(null)
    try {
      await onLogin(email, password, returnTo)
    } catch (error: any) {
      setMessage(error?.response?.data?.detail || 'Login failed. Check your email and password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen w-screen app-root overflow-auto text-gray-100">
      <div className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6 py-10 lg:px-10">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass rounded-[2rem] border border-white/8 p-8 shadow-soft-lg"
        >
          <div className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent/10 px-3 py-1 text-xs font-medium text-accent-2">
            <Sparkles size={14} />
            Email and password sign-in
          </div>
          <h1 className="mt-6 text-4xl font-bold text-white">Sign in to RepoMiner</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">
            Sign in to process repositories and manage sessions. Use the same account to keep your analysis history organized.
          </p>

          <div className="mt-8 grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-white/8 bg-white/5 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-white">
                <ShieldCheck size={16} className="text-accent-2" />
                Scoped sessions
              </div>
              <p className="mt-2 text-sm text-muted">Your sessions and tracked repositories are filtered to the account you sign in with.</p>
            </div>
            <div className="rounded-2xl border border-white/8 bg-white/5 p-4">
              <div className="flex items-center gap-2 text-sm font-semibold text-white">
                <ShieldCheck size={16} className="text-accent-2" />
                Fast access
              </div>
              <p className="mt-2 text-sm text-muted">Enter your email and password to continue directly to the repository analysis workspace.</p>
            </div>
          </div>

          {message && (
            <div className="mt-6 rounded-2xl border border-yellow-400/30 bg-yellow-400/10 px-4 py-3 text-sm text-yellow-100">
              {message}
            </div>
          )}

          <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
            <label className="block">
              <span className="mb-2 block text-sm text-muted">Email</span>
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none placeholder:text-muted focus:border-accent/40"
                placeholder="you@example.com"
                required
              />
            </label>

            <label className="block">
              <span className="mb-2 block text-sm text-muted">Password</span>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="w-full rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-white outline-none placeholder:text-muted focus:border-accent/40"
                placeholder="••••••••"
                required
              />
            </label>

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-2xl border border-white/10 bg-gradient-to-r from-accent to-accent-2 px-4 py-3 text-sm font-semibold text-white shadow-soft-lg transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <p className="mt-4 text-xs leading-5 text-muted">
            Email/password is the only sign-in method in this build.
          </p>
        </motion.div>
      </div>
    </div>
  )
}