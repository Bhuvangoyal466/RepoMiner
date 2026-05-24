import React, {useEffect, useRef} from 'react'

type Props = {
  code: string
  lang?: string
  startLine?: number
}

export default function CodeViewer({code, lang, startLine}:Props){
  const containerRef = useRef<HTMLDivElement|null>(null)

  useEffect(()=>{
    if(!containerRef.current || !startLine) return
    const el = containerRef.current.querySelector(`[data-line="${startLine}"]`) as HTMLElement | null
    if(el){
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      el.classList.add('bg-white/6')
      setTimeout(()=>el.classList.remove('bg-white/6'), 2000)
    }
  },[startLine, code])

  const lines = code.split('\n')

  return (
    <div className="rounded-md overflow-auto bg-black/60 p-2 max-h-[60vh] font-mono text-sm" ref={containerRef}>
      <div className="w-full">
        {lines.map((ln, idx)=> (
          <div key={idx} data-line={idx+1} className="grid grid-cols-[56px_1fr] gap-4 py-0.5">
            <div className="text-muted text-right pr-3 select-none text-xs">{idx+1}</div>
            <div className="whitespace-pre-wrap">{ln || '\u00A0'}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
