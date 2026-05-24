import React, {useEffect, useMemo, useRef, useState} from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { AlertTriangle, ArrowRight, Bot, Loader2, Send, Sparkles } from 'lucide-react'
import { loadSession, me, sendChat } from '../lib/api'
import ChatMessage from '../components/ChatMessage'
import Toast from '../components/Toast'

export default function Chat(){
  const [messages,setMessages] = useState<any[]>([])
  const [input,setInput] = useState('')
  const [toast,setToast] = useState<string|null>(null)
  const [loading,setLoading] = useState(false)
  const [sessionId,setSessionId] = useState<string | null>(null)
  const [sessionMeta,setSessionMeta] = useState<{repoName?: string | null; repoUrl?: string | null} | null>(null)
  const containerRef = useRef<HTMLDivElement|null>(null)
  const inputRef = useRef<HTMLInputElement|null>(null)
  const [searchParams] = useSearchParams()
  const location = useLocation()
  const navigate = useNavigate()

  useEffect(()=>{
    if(toast){
      const t = setTimeout(()=>setToast(null), 3000)
      return ()=>clearTimeout(t)
    }
  },[toast])

  useEffect(()=>{containerRef.current?.scrollTo({top: containerRef.current.scrollHeight, behavior:'smooth'})},[messages])

  useEffect(() => {
    let cancelled = false

    async function hydrateSession() {
      try {
        const currentUser = await me()
        if (cancelled) return
        const resolvedSessionId = searchParams.get('sessionId') || currentUser.currentSessionId || null
        setSessionId(resolvedSessionId)

        if (resolvedSessionId) {
          try {
            const session = await loadSession(resolvedSessionId)
            if (cancelled) return
            setSessionMeta({
              repoName: session.repo_name || session.repoName || null,
              repoUrl: session.repo_url || session.repoUrl || null,
            })

            // Restore prior conversation from the session file so switching
            // sessions does not lose the chat history.
            const storedMessages = Array.isArray(session.messages) ? session.messages : []
            const restored = storedMessages
              .map((m: any, idx: number) => {
                const role = m?.role === 'assistant' || m?.role === 'ai' ? 'assistant'
                  : m?.role === 'user' || m?.role === 'human' ? 'user'
                  : null
                if (!role) return null
                const text = (typeof m?.text === 'string' ? m.text : m?.content) || ''
                if (!text) return null
                return {
                  id: m?.id || `restored-${idx}`,
                  role,
                  text,
                  createdAt: m?.createdAt || m?.created_at || null,
                  sources: Array.isArray(m?.sources) ? m.sources : undefined,
                }
              })
              .filter(Boolean) as any[]
            setMessages(restored)
          } catch {
            if (!cancelled) {
              setSessionMeta(null)
              setMessages([])
            }
          }
        } else if (!cancelled) {
          setSessionMeta(null)
          setMessages([])
          setToast('Ingest a repository first, then ask a grounded question here.')
        }
      } catch {
        if (cancelled) return
        const fallbackSessionId = searchParams.get('sessionId') || null
        setSessionId(fallbackSessionId)
        setSessionMeta(null)
      }
    }

    hydrateSession()
    return () => {
      cancelled = true
    }
  }, [searchParams])

  useEffect(() => {
    if (location.state && (location.state as any).justIngested) {
      setToast('Repository indexed. Try a summary question or ask about a file, function, or data flow.')
      inputRef.current?.focus()
      navigate(location.pathname + location.search, { replace: true, state: null })
    }
  }, [location, navigate])

  const quickPrompts = useMemo(() => ([
    'Summarize the architecture of this repository.',
    'What are the main files I should read first?',
    'Explain the auth flow and where it is implemented.',
    'Show me the most important entry points and data flow.',
  ]), [])

  async function onSend(promptText?: string){
    const prompt = (promptText ?? input).trim()
    if(!prompt || loading) return
    if(!sessionId){
      setToast('No active repository yet. Process a repo first, then return here.')
      navigate('/repo')
      return
    }

    const m = {id:Date.now().toString(), role:'user', text:prompt, createdAt: new Date().toISOString()}
    const priorHistory = messages
      .filter((msg: any) => (msg.role === 'user' || msg.role === 'assistant') && typeof msg.text === 'string' && msg.text.trim())
      .map((msg: any) => ({ role: msg.role as 'user'|'assistant', text: msg.text }))
    setMessages(prev=>[...prev,m])
    setInput('')
    setLoading(true)
    try{
      const res = await sendChat(sessionId, prompt, priorHistory)
      setMessages(prev=>[...prev,{...res, createdAt: res.createdAt || new Date().toISOString()}])
    }catch(err:any){
      setToast(err?.response?.data?.detail || err?.message || 'Failed to send message')
    }finally{
      setLoading(false)
    }
  }

  return (
    <div className="flex h-full min-w-0">
      <div className="relative flex min-w-0 flex-1 flex-col overflow-hidden">
        <div ref={containerRef} className="flex-1 overflow-y-auto px-6 py-6 pb-40">
          <div className="mx-auto flex max-w-6xl flex-col gap-6">
            <div className="rounded-[28px] border border-white/10 bg-[#0d1424]/90 p-6 shadow-2xl shadow-black/20 backdrop-blur-xl md:p-7">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                <div className="min-w-0">
                  <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.24em] text-cyan-200">
                    <Sparkles size={14} />
                    Grounded repo chat
                  </div>
                  <h3 className="mt-4 text-3xl font-semibold tracking-tight text-white">Chat with the active repository.</h3>
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
                    Answers are pulled from indexed repository chunks and presented with source context. Ask about architecture, files, functions, security, or data flow.
                  </p>
                </div>
                <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-300">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">Active session</div>
                  <div className="mt-1 font-medium text-white">{sessionMeta?.repoName || sessionId || 'No session selected'}</div>
                  <div className="mt-1 text-xs text-slate-400">{sessionMeta?.repoUrl || 'Open Ingest to process a repository.'}</div>
                </div>
              </div>
            </div>

            {!messages.length && (
              <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
                <div className="rounded-[28px] border border-white/10 bg-white/5 p-6 shadow-2xl shadow-black/10">
                  <div className="flex items-center gap-2 text-sm font-semibold text-white">
                    <Bot size={18} className="text-cyan-300" />
                    What to do next
                  </div>
                  <div className="mt-4 space-y-4 text-sm leading-6 text-slate-300">
                    <p>1. If you just ingested a repository, wait for the app to open this screen automatically.</p>
                    <p>2. Start with a specific question like architecture, auth, entry points, or a file name.</p>
                    <p>3. Use the source blocks underneath answers to jump back to the most relevant code.</p>
                  </div>
                </div>

                <div className="rounded-[28px] border border-cyan-400/15 bg-cyan-400/10 p-6 shadow-2xl shadow-cyan-950/10">
                  <div className="flex items-center gap-2 text-sm font-semibold text-cyan-50">
                    <AlertTriangle size={18} />
                    Best results
                  </div>
                  <div className="mt-4 space-y-3 text-sm leading-6 text-cyan-50/90">
                    <p>Ask one precise question at a time for the best grounded answer.</p>
                    <p>If the answer looks off, ask for file names or function names and the chat will keep the same session context.</p>
                  </div>
                </div>
              </div>
            )}

            <div className="space-y-4">
              {messages.length > 0 && messages.map(m=> (
                <ChatMessage key={m.id} msg={m} />
              ))}

              {loading && (
                <div className="flex items-center gap-3 rounded-[28px] border border-white/10 bg-white/5 px-5 py-4 text-sm text-slate-300">
                  <Loader2 size={18} className="animate-spin text-cyan-300" />
                  Searching the repository context and composing a grounded reply...
                </div>
              )}
            </div>

            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {quickPrompts.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => onSend(prompt)}
                  className="group rounded-2xl border border-white/10 bg-white/5 p-4 text-left text-sm leading-6 text-slate-200 transition hover:-translate-y-0.5 hover:border-cyan-400/30 hover:bg-white/8"
                >
                  <div className="flex items-start justify-between gap-3">
                    <span>{prompt}</span>
                    <ArrowRight size={16} className="mt-0.5 shrink-0 text-cyan-300 opacity-70 transition group-hover:translate-x-0.5 group-hover:opacity-100" />
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-[#0b1020] via-[#0b1020]/95 to-transparent px-6 pb-6 pt-16">
          <div className="pointer-events-auto mx-auto max-w-6xl">
            <form
              onSubmit={(event) => {
                event.preventDefault()
                onSend()
              }}
              className="rounded-[28px] border border-white/10 bg-[#0d1424]/95 p-4 shadow-2xl shadow-black/30 backdrop-blur-xl"
            >
              <div className="flex flex-col gap-3 md:flex-row md:items-end">
                <div className="flex-1">
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">Ask a question</label>
                  <input
                    ref={inputRef}
                    value={input}
                    onChange={e=>setInput(e.target.value)}
                    className="min-h-[56px] w-full rounded-2xl border border-white/10 bg-[#0b1220] px-4 text-sm text-white placeholder:text-slate-500 caret-cyan-300 outline-none focus:border-cyan-400/50 focus:ring-2 focus:ring-cyan-400/10"
                    placeholder={sessionId ? 'Ask about architecture, files, functions, or data flow...' : 'Process a repo first to enable chat'}
                    disabled={!sessionId || loading}
                  />
                </div>
                <button
                  type="submit"
                  disabled={!sessionId || loading || !input.trim()}
                  className="inline-flex min-h-[56px] items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-cyan-400 to-sky-500 px-6 text-sm font-semibold text-slate-950 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {loading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
                  {loading ? 'Thinking...' : 'Send'}
                </button>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">Grounded to the active session</span>
                <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1">Source snippets included when available</span>
              </div>
            </form>
          </div>
        </div>
      </div>

      {toast && <Toast>{toast}</Toast>}
    </div>
  )
}
