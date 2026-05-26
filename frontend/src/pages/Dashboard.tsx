import React, { useEffect, useMemo, useState } from 'react'
import MetricCard from '../components/MetricCard'
import ContributorChart from '../components/ContributorChart'
import ReactMarkdown from 'react-markdown'
import { 
  evaluateRepository,
  exportStats,
  getRepoStats,
  getReportArtifacts,
  importCoverageReport,
} from '../lib/api'
import { Cell, Legend, Pie, PieChart, ResponsiveContainer } from 'recharts'
import { ArrowDownToLine, BarChart3, FileText, UploadCloud } from 'lucide-react'

function humanBytes(bytes: number) {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let value = bytes
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024
    i += 1
  }
  return `${value.toFixed(i ? 1 : 0)} ${units[i]}`
}

const palette = ['#7c5cff', '#00d4ff', '#ff7ab6', '#ffd36b', '#6ee7b7', '#9f7aea']

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null)
  const [reports, setReports] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)
  const [coverageStatus, setCoverageStatus] = useState<string | null>(null)
  const [evalStatus, setEvalStatus] = useState<string | null>(null)
  const [evalCasesText, setEvalCasesText] = useState('')

  useEffect(() => {
    let active = true
    setLoading(true)
    Promise.all([getRepoStats('active'), getReportArtifacts('active')])
      .then(([nextStats, nextReports]) => {
        if (active) {
          setStats(nextStats)
          setReports(nextReports)
        }
      })
      .catch(() => {
        if (active) {
          setStats(null)
          setReports(null)
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [])

  async function refreshStats() {
    const [nextStats, nextReports] = await Promise.all([getRepoStats('active'), getReportArtifacts('active')])
    setStats(nextStats)
    setReports(nextReports)
  }

  async function onExport(format: 'csv' | 'json') {
    setExporting(true)
    try {
      const result = await exportStats('active', format)
      const blob = new Blob(
        [typeof result === 'string' ? result : JSON.stringify(result, null, 2)],
        { type: format === 'csv' ? 'text/csv' : 'application/json' }
      )
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `codeminer_stats.${format}`
      anchor.click()
      URL.revokeObjectURL(url)
    } catch {
      // keep the page responsive even if export is unavailable
    } finally {
      setExporting(false)
    }
  }

  async function onCoverageUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    setBusy('coverage')
    setCoverageStatus(`Importing ${file.name}...`)
    try {
      const content = await file.text()
      await importCoverageReport('active', file.name, content)
      await refreshStats()
      setCoverageStatus(`Imported coverage from ${file.name}`)
    } catch (error: any) {
      setCoverageStatus(error?.response?.data?.detail || error?.message || 'Coverage import failed')
    } finally {
      setBusy(null)
      event.target.value = ''
    }
  }

  async function onRunEval() {
    if (!evalCasesText.trim()) {
      setEvalStatus('Paste or upload a JSON evaluation dataset first.')
      return
    }
    setBusy('eval')
    setEvalStatus('Running retrieval evaluation...')
    try {
      const parsed = JSON.parse(evalCasesText)
      const cases = Array.isArray(parsed) ? parsed : parsed.cases
      const result = await evaluateRepository('active', cases || [], 6)
      setEvalStatus(
        `Hit@6 ${result.summary?.hit_at_k ?? 'N/A'}, MRR ${result.summary?.mrr ?? 'N/A'}, avg latency ${result.summary?.avg_retrieval_ms ?? 'N/A'} ms`
      )
      await refreshStats()
    } catch (error: any) {
      setEvalStatus(error?.message || 'Evaluation failed')
    } finally {
      setBusy(null)
    }
  }

  function downloadText(name: string, content: string, mime = 'text/plain') {
    const blob = new Blob([content], { type: mime })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = name
    anchor.click()
    URL.revokeObjectURL(url)
  }

  function downloadPdfBase64(name: string, base64?: string | null) {
    if (!base64) return
    const bytes = Uint8Array.from(atob(base64), (char) => char.charCodeAt(0))
    const blob = new Blob([bytes], { type: 'application/pdf' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = name
    anchor.click()
    URL.revokeObjectURL(url)
  }

  const languageData = stats?.languages
    ? Object.entries(stats.languages).map(([name, value]) => ({ name, value: Number(value) }))
    : []

  const topExtensions = stats
    ? Object.entries(stats.extension_breakdown || stats.extensions || {})
        .sort((a: any, b: any) => Number(b[1]) - Number(a[1]))
        .slice(0, 8)
        .map(([name, value]) => `${name} (${value})`)
    : []

  const complexitySummary = stats?.complexity_summary || {}
  const languageSummary = stats?.language_insights_summary || {}
  const coverageSummary = stats?.coverage_import?.summary || {}
  const evalSummary = stats?.rag_eval_summary || {}
  const hotspotTimeline = stats?.hotspots_over_time?.timeline || {}
  const summaryMarkdown = reports?.summaryMarkdown || ''
  const onboardingMarkdown = reports?.onboardingMarkdown || ''
  const diagram = reports?.architectureMermaid || stats?.architecture_mermaid || ''
  const pdfBase64 = reports?.summaryPdfBase64
  const languageBreakdown = useMemo(
    () => (stats?.language_insights?.language_counts ? stats.language_insights.language_counts : stats?.languages || {}),
    [stats]
  )

  return (
    <div className="p-6 h-full overflow-auto">
      <div className="flex items-center justify-between mb-4 gap-4">
        <div>
          <h2 className="text-2xl font-semibold">Repository Analytics</h2>
          <div className="text-sm text-muted">High-fidelity metrics, findings, and exports.</div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => downloadText('repo_summary.md', summaryMarkdown || '# RepoMiner Summary\n\nNo summary available yet.')}
            disabled={exporting || loading}
            className="px-3 py-2 bg-white/3 rounded-md disabled:opacity-60"
          >
            Summary MD
          </button>
          <button
            onClick={() => downloadPdfBase64('repo_summary.pdf', pdfBase64)}
            disabled={exporting || loading || !pdfBase64}
            className="px-3 py-2 bg-white/3 rounded-md disabled:opacity-60"
          >
            Summary PDF
          </button>
          <button
            onClick={() => onExport('csv')}
            disabled={exporting}
            className="px-3 py-2 bg-white/3 rounded-md disabled:opacity-60"
          >
            Export CSV
          </button>
          <button
            onClick={() => onExport('json')}
            disabled={exporting}
            className="px-3 py-2 bg-white/3 rounded-md disabled:opacity-60"
          >
            Export JSON
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard title="Files" value={loading ? '…' : stats?.total_files || 0} sub={loading ? 'Loading…' : 'Parsed files'} />
        <MetricCard title="Chunks" value={loading ? '…' : stats?.total_chunks || 0} sub={loading ? 'Loading…' : 'Text/code chunks'} />
        <MetricCard title="Images" value={loading ? '…' : stats?.images_processed || 0} sub={loading ? 'Loading…' : 'Images scanned'} />
      </div>

      <div className="mt-6 grid grid-cols-1 md:grid-cols-4 gap-4">
        <MetricCard title="Complex files" value={loading ? '…' : complexitySummary.files || 0} sub={loading ? 'Loading…' : 'Computed complexity rows'} />
        <MetricCard title="Avg CC" value={loading ? '…' : complexitySummary.cc_avg ?? 'N/A'} sub="Cyclomatic complexity" />
        <MetricCard title="Coverage" value={loading ? '…' : `${coverageSummary.coverage_pct ?? 0}%`} sub="Imported coverage" />
        <MetricCard title="Eval MRR" value={loading ? '…' : evalSummary.mrr ?? 'N/A'} sub="Retrieval quality" />
      </div>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass p-4 rounded-md">
          <h4 className="font-semibold">Language Breakdown</h4>
          <div style={{ height: 260 }} className="mt-4">
            {loading ? (
              <div className="text-muted">Loading chart…</div>
            ) : Object.keys(languageBreakdown).length ? (
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    dataKey="value"
                    data={Object.entries(languageBreakdown).map(([name, value]) => ({ name, value: Number(value) }))}
                    outerRadius={90}
                    innerRadius={36}
                  >
                    {Object.entries(languageBreakdown).map(([name], index) => (
                      <Cell key={name} fill={palette[index % palette.length]} />
                    ))}
                  </Pie>
                  <Legend verticalAlign="bottom" height={36} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-muted">No language data</div>
            )}
          </div>
        </div>

        <div className="glass p-4 rounded-md">
          <h4 className="font-semibold">Top Extensions</h4>
          <div className="mt-4 text-sm text-muted">
            {loading ? 'Loading…' : topExtensions.length ? topExtensions.join(', ') : '—'}
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass p-4 rounded-md">
          <h4 className="font-semibold">Hotspots over time</h4>
          <div className="text-xs text-muted mt-1">Churn by month or week, computed from git history.</div>
          <div className="mt-3">
            {loading ? (
              <div className="text-muted">Loading hotspots…</div>
            ) : Object.keys(hotspotTimeline).length ? (
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie data={Object.entries(hotspotTimeline).map(([name, value]) => ({ name, value }))} dataKey="value" outerRadius={80} label>
                    {Object.entries(hotspotTimeline).map(([name], index) => (
                      <Cell key={name} fill={palette[index % palette.length]} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            ) : stats?.hotspots?.length ? (
              <table className="w-full text-sm">
                <thead className="text-left text-muted">
                  <tr>
                    <th>Path</th>
                    <th>Commits</th>
                    <th>Lines</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.hotspots.map((hotspot: any) => (
                    <tr key={hotspot.path} className="border-t border-white/6 hover:bg-white/2">
                      <td className="py-2">{hotspot.path}</td>
                      <td>{hotspot.complexity}</td>
                      <td>{hotspot.lines}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="text-muted">No hotspot data</div>
            )}
          </div>
        </div>

        <div className="glass p-4 rounded-md">
          <h4 className="font-semibold">Coverage import</h4>
          <div className="text-xs text-muted mt-1">Upload coverage.xml or lcov.info to merge test coverage into the session.</div>
          <div className="mt-3 space-y-3 text-sm">
            <label className="block rounded-md border border-white/10 bg-white/5 p-3 cursor-pointer">
              <div className="flex items-center gap-2 text-white">
                <UploadCloud size={16} />
                <span>{busy === 'coverage' ? 'Importing...' : 'Choose coverage file'}</span>
              </div>
              <input type="file" accept=".xml,.info" className="hidden" onChange={onCoverageUpload} disabled={busy === 'coverage'} />
            </label>
            {coverageStatus && <div className="text-muted">{coverageStatus}</div>}
            {coverageSummary.coverage_pct != null && (
              <div className="rounded-md border border-white/10 bg-white/5 p-3">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Imported summary</div>
                <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                  <div>Files: {coverageSummary.files ?? 0}</div>
                  <div>Covered files: {coverageSummary.covered_files ?? 0}</div>
                  <div>Lines covered: {coverageSummary.lines_covered ?? 0}</div>
                  <div>Coverage: {coverageSummary.coverage_pct ?? 0}%</div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="glass p-4 rounded-md lg:col-span-2">
          <h4 className="font-semibold">Hotspots</h4>
          <div className="text-xs text-muted mt-1">Files touched by the most commits in this repo's history.</div>
          <div className="mt-3">
            {loading ? (
              <div className="text-muted">Loading hotspots…</div>
            ) : stats?.hotspots?.length ? (
              <table className="w-full text-sm">
                <thead className="text-left text-muted">
                  <tr>
                    <th>Path</th>
                    <th>Commits</th>
                    <th>Lines</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.hotspots.map((hotspot: any) => (
                    <tr
                      key={hotspot.path}
                      className="border-t border-white/6 hover:bg-white/2"
                    >
                      <td className="py-2">{hotspot.path}</td>
                      <td>{hotspot.complexity}</td>
                      <td>{hotspot.lines}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="text-muted">No hotspot data</div>
            )}
          </div>
        </div>

        <div className="glass p-4 rounded-md">
          <h4 className="font-semibold">Contributors</h4>
          <div className="text-xs text-muted mt-1">Commits per author from the full git history.</div>
          <div className="mt-3 text-sm">
            {loading ? (
              <div className="text-muted">Loading contributors…</div>
            ) : stats?.contributors?.length ? (
              <ContributorChart data={stats.contributors} />
            ) : (
              <div className="text-muted">No contributor data</div>
            )}
          </div>
        </div>
      </div>

      <div className="mt-6">
        <div className="glass p-4 rounded-md">
          <h4 className="font-semibold">Dependencies</h4>
          <div className="text-xs text-muted mt-1">Declared in package.json and requirements.txt.</div>
          <div className="mt-3 text-sm">
            {loading ? (
              <div className="text-muted">Loading dependencies…</div>
            ) : stats?.dependencies?.length ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {stats.dependencies.map((dependency: any, i: number) => (
                  <div key={`${dependency.source || ''}-${dependency.name}-${i}`} className="flex items-center justify-between gap-4 py-1">
                    <div className="min-w-0">
                      <div className="font-medium truncate">
                        {dependency.name}
                        {dependency.version ? `@${dependency.version}` : ''}
                      </div>
                    </div>
                    <div className="text-xs text-muted shrink-0">{dependency.source || ''}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-muted">No dependency data</div>
            )}
          </div>
        </div>
      </div>

      <div className="mt-6">
        <h4 className="font-semibold">Top Files (by size)</h4>
        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
          {loading ? (
            <div className="text-muted">Loading top files…</div>
          ) : stats?.top_files?.length ? (
            stats.top_files.map((file: any) => (
              <div key={file.path} className="glass p-3 rounded-md flex items-center justify-between">
                <div>
                  <div className="font-medium">{file.path}</div>
                  <div className="text-xs text-muted">{humanBytes(file.size)}</div>
                </div>
                <div className="flex gap-2">
                  <a href="#" className="px-2 py-1 bg-white/3 rounded-md text-sm">
                    Open
                  </a>
                  <a href="#" className="px-2 py-1 bg-white/3 rounded-md text-sm">
                    Download
                  </a>
                </div>
              </div>
            ))
          ) : (
            <div className="text-muted">No top file data</div>
          )}
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass p-4 rounded-md">
          <h4 className="font-semibold">Retrieval evaluation</h4>
          <div className="text-xs text-muted mt-1">Paste a JSON array of benchmark cases or upload from your test harness.</div>
          <textarea
            value={evalCasesText}
            onChange={(event) => setEvalCasesText(event.target.value)}
            placeholder='[{"id":"case-1","question":"How does auth work?","expected_sources":["backend_api.py"],"expected_keywords":["cookie"]}]'
            className="mt-3 min-h-[180px] w-full rounded-md border border-white/10 bg-[#0b1220] p-3 text-sm text-white outline-none placeholder:text-slate-500"
          />
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              onClick={onRunEval}
              disabled={busy === 'eval'}
              className="inline-flex items-center gap-2 rounded-md bg-white/10 px-3 py-2 text-sm font-medium disabled:opacity-60"
            >
              <BarChart3 size={16} />
              {busy === 'eval' ? 'Running...' : 'Run evaluation'}
            </button>
            <button
              onClick={() => downloadText('repo_onboarding.md', onboardingMarkdown || '# Repository Onboarding\n\nNo onboarding doc available yet.', 'text/markdown')}
              className="inline-flex items-center gap-2 rounded-md bg-white/10 px-3 py-2 text-sm font-medium"
            >
              <FileText size={16} />
              Download onboarding
            </button>
          </div>
          {evalStatus && <div className="mt-3 text-sm text-muted">{evalStatus}</div>}
          {evalSummary && (
            <div className="mt-4 rounded-md border border-white/10 bg-white/5 p-3 text-sm">
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Latest evaluation</div>
              <div className="mt-2 grid grid-cols-2 gap-2">
                <div>Hit@k: {evalSummary.hit_at_k ?? 'N/A'}</div>
                <div>Precision@k: {evalSummary.precision_at_k ?? 'N/A'}</div>
                <div>Recall@k: {evalSummary.recall_at_k ?? 'N/A'}</div>
                <div>Latency: {evalSummary.avg_retrieval_ms ?? 'N/A'} ms</div>
              </div>
            </div>
          )}
        </div>

        <div className="glass p-4 rounded-md">
          <h4 className="font-semibold">Architecture report</h4>
          <div className="text-xs text-muted mt-1">Generated Markdown and Mermaid outputs from the repository graph.</div>
          <div className="mt-3 space-y-3 text-sm">
            <div className="rounded-md border border-white/10 bg-white/5 p-3">
              <div className="text-xs uppercase tracking-[0.18em] text-muted">Architecture diagram source</div>
              <pre className="mt-2 max-h-44 overflow-auto whitespace-pre-wrap text-xs text-slate-200">{diagram || 'No diagram available'}</pre>
            </div>
            <button
              onClick={() => downloadText('repo_summary.md', summaryMarkdown || '# RepoMiner Summary\n\nNo summary available yet.', 'text/markdown')}
              className="inline-flex items-center gap-2 rounded-md bg-white/10 px-3 py-2 text-sm font-medium"
            >
              <ArrowDownToLine size={16} />
              Download summary Markdown
            </button>
            <button
              onClick={() => downloadPdfBase64('repo_summary.pdf', pdfBase64)}
              disabled={!pdfBase64}
              className="inline-flex items-center gap-2 rounded-md bg-white/10 px-3 py-2 text-sm font-medium disabled:opacity-60"
            >
              <ArrowDownToLine size={16} />
              Download summary PDF
            </button>
            {summaryMarkdown && (
              <div className="rounded-md border border-white/10 bg-white/5 p-3">
                <div className="text-xs uppercase tracking-[0.18em] text-muted">Summary preview</div>
                <div className="mt-2 max-h-64 overflow-auto text-sm leading-6 text-slate-200">
                  <ReactMarkdown>{summaryMarkdown}</ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
