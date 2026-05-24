import React from 'react'
import { motion } from 'framer-motion'
import { Bot, FileText, User } from 'lucide-react'

export default function ChatMessage({msg}:{msg:any}){
  const isUser = msg.role === 'user'
  const sources = Array.isArray(msg.sources) ? msg.sources.slice(0, 3) : []

  return (
    <motion.article
      initial={{opacity:0,y:8}}
      animate={{opacity:1,y:0}}
      className={`flex items-end gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      {!isUser && (
        <div className="mb-1 grid h-10 w-10 shrink-0 place-items-center rounded-2xl border border-cyan-400/20 bg-cyan-400/10 text-cyan-200 shadow-lg shadow-cyan-950/10">
          <Bot size={18} />
        </div>
      )}

      <div
        className={`max-w-[min(760px,calc(100%-4rem))] rounded-[28px] border px-4 py-4 shadow-2xl shadow-black/10 md:px-5 ${
          isUser
            ? 'border-cyan-400/20 bg-gradient-to-br from-cyan-400/15 via-sky-500/10 to-transparent text-white'
            : 'border-white/10 bg-[#0f1729]/95 text-slate-100'
        }`}
      >
        <div className={`mb-3 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.22em] ${isUser ? 'text-cyan-100/90' : 'text-slate-400'}`}>
          {isUser ? <User size={13} /> : <FileText size={13} />}
          {isUser ? 'You' : 'Assistant'}
        </div>
        <div className="whitespace-pre-wrap text-sm leading-7 text-slate-100">{msg.text}</div>

        {!isUser && sources.length > 0 && (
          <div className="mt-4 border-t border-white/8 pt-4">
            <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">Sources used</div>
            <div className="mt-3 space-y-2">
              {sources.map((source: any) => (
                <div key={source.id} className="rounded-2xl border border-white/8 bg-white/5 px-3 py-2 text-xs text-slate-300">
                  <div className="font-medium text-white">{source.path}</div>
                  <div className="mt-1 text-[11px] leading-5 text-slate-400 line-clamp-3">{source.content}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {isUser && (
        <div className="mb-1 grid h-10 w-10 shrink-0 place-items-center rounded-2xl border border-white/10 bg-white/5 text-white shadow-lg shadow-black/10">
          <User size={18} />
        </div>
      )}
    </motion.article>
  )
}
