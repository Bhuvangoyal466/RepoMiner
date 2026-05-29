import React, { useEffect, useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import MetricCard from '../components/MetricCard'
import ContributorChart from '../components/ContributorChart'
import {
  exportStats,
  getRepoStats,
  getReportArtifacts,
  importCoverageReport,
} from '../lib/api'
import { Cell, Legend, Pie, PieChart, ResponsiveContainer } from 'recharts'
import { ArrowDownToLine, FileText, UploadCloud } from 'lucide-react'

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
  const location = useLocation()

  const searchQuery = useMemo(() => {
    const value = new URLSearchParams(location.search).get('q') || ''
    return value.trim().toLowerCase()
  }, [location.search])

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
      anchor.download = `repominer_stats.${format}`
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

  const complexitySummary = stats?.complexity_summary || {}
  const coverageSummary = stats?.coverage_import?.summary || {}
  const summaryMarkdown = reports?.summaryMarkdown || ''
  const onboardingMarkdown = reports?.onboardingMarkdown || ''
  const diagram = reports?.architectureMermaid || stats?.architecture_mermaid || ''
  const pdfBase64 = reports?.summaryPdfBase64

  const languageEntries = useMemo(() => {
    const languageCounts = stats?.language_insights?.language_counts || stats?.languages || {}
    const entries = Object.entries(languageCounts).map(([name, value]) => ({ name, value: Number(value) }))
    if (!searchQuery) return entries
    return entries.filter((item) => item.name.toLowerCase().includes(searchQuery))
  }, [searchQuery, stats])

  const extensionEntries = useMemo(() => {
    const entries = Object.entries(stats?.extension_breakdown || stats?.extensions || {})
      .map(([name, value]) => ({ name, value: Number(value) }))
      .sort((a, b) => b.value - a.value)
    const filtered = searchQuery
      ? entries.filter((item) => item.name.toLowerCase().includes(searchQuery))
      : entries
    return filtered.slice(0, 10)
  }, [searchQuery, stats])

  const filteredHotspots = useMemo(() => {
    const rows = stats?.hotspots || []
    if (!searchQuery) return rows
    return rows.filter((row: any) => String(row.path || '').toLowerCase().includes(searchQuery))
  }, [searchQuery, stats])

  const filteredDependencies = useMemo(() => {
    const rows = stats?.dependencies || []
    if (!searchQuery) return rows
    return rows.filter((row: any) => {
      const name = String(row.name || '').toLowerCase()
      const version = String(row.version || '').toLowerCase()
      const source = String(row.source || '').toLowerCase()
      return name.includes(searchQuery) || version.includes(searchQuery) || source.includes(searchQuery)
    })
  }, [searchQuery, stats])

  const filteredTopFiles = useMemo(() => {
    const rows = stats?.top_files || []
    if (!searchQuery) return rows
    return rows.filter((row: any) => String(row.path || '').toLowerCase().includes(searchQuery))
  }, [searchQuery, stats])

  const filteredContributors = useMemo(() => {
    const rows = stats?.contributors || []
    if (!searchQuery) return rows
    return rows.filter((row: any) => String(row.name || '').toLowerCase().includes(searchQuery))
  }, [searchQuery, stats])

  const hasLanguageData = languageEntries.length > 0
  const hasExtensionData = extensionEntries.length > 0
  const hasContributorData = filteredContributors.length > 0
  const hasHotspotData = filteredHotspots.length > 0
  const hasDependencyData = filteredDependencies.length > 0
  const hasTopFiles = filteredTopFiles.length > 0
  const hasReportArtifacts = Boolean(summaryMarkdown || onboardingMarkdown || diagram || pdfBase64)

  return (
    <div className="p-6 h-full overflow-auto">
      <div className="flex items-center justify-between mb-4 gap-4">
        <div>
          <h2 className="text-2xl font-semibold">Repository Analytics</h2>
          <div className="text-sm text-muted">Core repository signals only, filtered to what has data.</div>
          {searchQuery && <div className="text-xs text-muted mt-1">Filtering results for: {searchQuery}</div>}
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

      {(complexitySummary.files || coverageSummary.coverage_pct != null) && (
        <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          <MetricCard title="Complex files" value={loading ? '…' : complexitySummary.files || 0} sub={loading ? 'Loading…' : 'Computed complexity rows'} />
          <MetricCard title="Avg CC" value={loading ? '…' : complexitySummary.cc_avg ?? 'N/A'} sub="Cyclomatic complexity" />
          <MetricCard title="Coverage" value={loading ? '…' : `${coverageSummary.coverage_pct ?? 0}%`} sub="Imported coverage" />
        </div>
      )}

      {(hasLanguageData || hasExtensionData) && (
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
          {hasLanguageData && (
            <div className="glass p-4 rounded-md">
              <h4 className="font-semibold">Language Breakdown</h4>
              <div style={{ height: 260 }} className="mt-4">
                {loading ? (
                  <div className="text-muted">Loading chart…</div>
                ) : (
                  <ResponsiveContainer>
                    <PieChart>
                      <Pie dataKey="value" data={languageEntries} outerRadius={90} innerRadius={36}>
                        {languageEntries.map((entry, index) => (
                          <Cell key={entry.name} fill={palette[index % palette.length]} />
                        ))}
                      </Pie>
                      <Legend verticalAlign="bottom" height={36} />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
          )}

          {hasExtensionData && (
            <div className="glass p-4 rounded-md">
              <h4 className="font-semibold">Top Extensions</h4>
              <div className="mt-3 space-y-2 text-sm text-slate-200">
                {extensionEntries.map((entry) => (
                  <div key={entry.name} className="flex items-center justify-between gap-3 border-b border-white/5 pb-2 last:border-0 last:pb-0">
                    <span className="truncate">{entry.name}</span>
                    <span className="text-muted shrink-0">{entry.value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {(hasHotspotData || loading) && (
          <div className="glass p-4 rounded-md">
            <h4 className="font-semibold">Hotspots</h4>
            <div className="text-xs text-muted mt-1">Files touched by the most commits in this repo's history.</div>
            <div className="mt-3">
              {loading ? (
                <div className="text-muted">Loading hotspots…</div>
              ) : (
                <table className="w-full text-sm">
                  <thead className="text-left text-muted">
                    <tr>
                      <th>Path</th>
                      <th>Commits</th>
                      <th>Lines</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredHotspots.map((hotspot: any) => (
                      <tr key={hotspot.path} className="border-t border-white/6 hover:bg-white/2">
                        <td className="py-2">{hotspot.path}</td>
                        <td>{hotspot.complexity}</td>
                        <td>{hotspot.lines}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        )}

        <div className="glass p-4 rounded-md">
          <h4 className="font-semibold">Coverage import</h4>
          <div className="text-xs text-muted mt-1">Upload coverage.xml or lcov.info to merge test coverage into this session.</div>
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

      {hasContributorData && (
        <div className="mt-6">
          <div className="glass p-4 rounded-md">
            <h4 className="font-semibold">Contributors</h4>
            <div className="text-xs text-muted mt-1">Commits per author from the full git history.</div>
            <div className="mt-3 text-sm">
              {loading ? <div className="text-muted">Loading contributors…</div> : <ContributorChart data={filteredContributors} />}
            </div>
          </div>
        </div>
      )}

      {hasDependencyData && (
        <div className="mt-6">
          <div className="glass p-4 rounded-md">
            <h4 className="font-semibold">Dependencies</h4>
            <div className="text-xs text-muted mt-1">Declared in package.json and requirements.txt.</div>
            <div className="mt-3 text-sm grid grid-cols-1 md:grid-cols-2 gap-2">
              {filteredDependencies.map((dependency: any, i: number) => (
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
          </div>
        </div>
      )}

      {hasTopFiles && (
        <div className="mt-6">
          <h4 className="font-semibold">Top Files (by size)</h4>
          <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
            {filteredTopFiles.map((file: any) => (
              <div key={file.path} className="glass p-3 rounded-md flex items-center justify-between">
                <div>
                  <div className="font-medium">{file.path}</div>
                  <div className="text-xs text-muted">{humanBytes(file.size)}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {hasReportArtifacts && (
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="glass p-4 rounded-md">
            <h4 className="font-semibold">Architecture report</h4>
            <div className="text-xs text-muted mt-1">Generated Markdown and Mermaid outputs from the repository graph.</div>
            <div className="mt-3 space-y-3 text-sm">
              {diagram && (
                <div className="rounded-md border border-white/10 bg-white/5 p-3">
                  <div className="text-xs uppercase tracking-[0.18em] text-muted">Architecture diagram source</div>
                  <pre className="mt-2 max-h-44 overflow-auto whitespace-pre-wrap text-xs text-slate-200">{diagram}</pre>
                </div>
              )}

              <button
                onClick={() => downloadText('repo_summary.md', summaryMarkdown || '# RepoMiner Summary\n\nNo summary available yet.', 'text/markdown')}
                className="inline-flex items-center gap-2 rounded-md bg-white/10 px-3 py-2 text-sm font-medium"
              >
                <ArrowDownToLine size={16} />
                Download summary Markdown
              </button>
              <button
                onClick={() => downloadText('repo_onboarding.md', onboardingMarkdown || '# Repository Onboarding\n\nNo onboarding doc available yet.', 'text/markdown')}
                className="inline-flex items-center gap-2 rounded-md bg-white/10 px-3 py-2 text-sm font-medium"
              >
                <FileText size={16} />
                Download onboarding Markdown
              </button>
              <button
                onClick={() => downloadPdfBase64('repo_summary.pdf', pdfBase64)}
                disabled={!pdfBase64}
                className="inline-flex items-center gap-2 rounded-md bg-white/10 px-3 py-2 text-sm font-medium disabled:opacity-60"
              >
                <ArrowDownToLine size={16} />
                Download summary PDF
              </button>
            </div>
          </div>

          {summaryMarkdown && (
            <div className="glass p-4 rounded-md">
              <h4 className="font-semibold">Summary preview</h4>
              <div className="mt-3 max-h-80 overflow-auto text-sm leading-6 text-slate-200">
                <ReactMarkdown>{summaryMarkdown}</ReactMarkdown>
              </div>
            </div>
          )}
        </div>
      )}

      {!loading && !hasLanguageData && !hasExtensionData && !hasHotspotData && !hasContributorData && !hasDependencyData && !hasTopFiles && !hasReportArtifacts && (
        <div className="mt-6 text-muted">No analytics data is available for this repository yet.</div>
      )}
    </div>
  )
}
