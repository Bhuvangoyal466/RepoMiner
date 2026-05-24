import React, {useState} from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, Bot, FileText, GitBranch, Loader2, Sparkles } from 'lucide-react'
import { startProcessing } from '../lib/api'

export default function RepoWorkspace(){
  const [url,setUrl] = useState('')
  const [loading,setLoading] = useState(false)
  const [message,setMessage] = useState<string|undefined>()
  const navigate = useNavigate()

  async function onSubmit(e:any){
    e?.preventDefault()
    const trimmedUrl = url.trim()
    if (!trimmedUrl) {
      setMessage('Paste a GitHub repository URL to continue.')
      return
    }
    setLoading(true)
    setMessage('Processing repository. This can take a minute; keep this tab open while the code is indexed.')
    try{
      const res = await startProcessing(trimmedUrl)
      setMessage('Ingestion complete. Opening chat with the active repository...')
      navigate(`/chat?sessionId=${encodeURIComponent(res.sessionId)}`, {
        state: {
          justIngested: true,
          repoUrl: trimmedUrl,
          repoName: res?.stats?.repo_name || res?.stats?.repoName || undefined,
        },
        replace: true,
      })
    }catch(err:any){
      setMessage(err?.message || 'Failed to start')
    }finally{setLoading(false)}
  }

  return (
    <div className="h-full overflow-auto px-6 py-6">
      <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[1.3fr_0.7fr]">
        <div className="rounded-[28px] border border-white/10 bg-[#0d1424]/90 p-6 shadow-2xl shadow-cyan-950/20 backdrop-blur-xl lg:p-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-cyan-200">
            <Sparkles size={14} />
            Repository ingest
          </div>
          <h2 className="mt-4 text-3xl font-semibold tracking-tight text-white">Process a repo, then jump straight into chat.</h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
            Paste a GitHub URL, wait for indexing to finish, and the app will open the chat workspace automatically with the newly processed repository active.
          </p>

          <form onSubmit={onSubmit} className="mt-6 space-y-3">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-3 shadow-inner shadow-black/20">
              <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Repository URL</label>
              <div className="flex flex-col gap-3 md:flex-row">
                <input
                  value={url}
                  onChange={e=>setUrl(e.target.value)}
                  placeholder="https://github.com/owner/repo"
                  className="min-h-[52px] flex-1 rounded-xl border border-white/10 bg-[#0b1220] px-4 text-sm text-white outline-none placeholder:text-slate-500 focus:border-cyan-400/50 focus:ring-2 focus:ring-cyan-400/10"
                />
                <button
                  type="submit"
                  className="inline-flex min-h-[52px] items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-400 to-sky-500 px-5 text-sm font-semibold text-slate-950 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={loading}
                >
                  {loading ? <Loader2 size={18} className="animate-spin" /> : <ArrowRight size={18} />}
                  {loading ? 'Processing...' : 'Start ingestion'}
                </button>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <GitBranch size={18} className="text-cyan-300" />
                <div className="mt-3 text-sm font-semibold text-white">Step 1</div>
                <div className="mt-1 text-sm leading-6 text-slate-300">Paste the GitHub repository URL and submit it.</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <FileText size={18} className="text-cyan-300" />
                <div className="mt-3 text-sm font-semibold text-white">Step 2</div>
                <div className="mt-1 text-sm leading-6 text-slate-300">Wait while files are cloned, chunked, and indexed.</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <Bot size={18} className="text-cyan-300" />
                <div className="mt-3 text-sm font-semibold text-white">Step 3</div>
                <div className="mt-1 text-sm leading-6 text-slate-300">Chat opens automatically once the repository is ready.</div>
              </div>
            </div>

            {message && (
              <div className="rounded-2xl border border-cyan-400/20 bg-cyan-400/10 px-4 py-3 text-sm leading-6 text-cyan-50">
                {message}
              </div>
            )}
          </form>
        </div>

        <aside className="rounded-[28px] border border-white/10 bg-white/5 p-6 shadow-2xl shadow-black/20 backdrop-blur-xl">
          <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">What happens next</div>
          <div className="mt-4 space-y-4 text-sm leading-6 text-slate-300">
            <p>After the ingest finishes, the app will route you to Chat with the repository session already selected.</p>
            <p>Ask for architecture summaries, specific files, implementation details, or "show me the source" style questions.</p>
            <p>If processing takes time, keep this page open. The status text will update while the repository is being prepared.</p>
          </div>
          <div className="mt-6 rounded-2xl border border-white/10 bg-[#0b1220] p-4">
            <div className="text-sm font-semibold text-white">Example prompts</div>
            <ul className="mt-3 space-y-2 text-sm text-slate-300">
              <li>• Summarize the architecture of this repository.</li>
              <li>• What are the main entry points and data flows?</li>
              <li>• Which files should I read first to understand auth?</li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  )
}
