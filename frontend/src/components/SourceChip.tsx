import React from 'react'

export default function SourceChip({path,score, onOpen}:{path:string, score?:number, onOpen?:()=>void}){
  return (
    <div className="flex items-center gap-2 bg-white/3 p-2 rounded-md">
      <div className="text-xs font-mono text-accent">{path}</div>
      {typeof score==='number' && <div className="text-xs text-muted">{Math.round(score*100)}%</div>}
      {onOpen && <button onClick={onOpen} className="ml-auto text-sm text-accent">Open</button>}
    </div>
  )
}
