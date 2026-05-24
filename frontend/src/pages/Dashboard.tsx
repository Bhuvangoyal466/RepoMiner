import React, { useEffect, useState } from 'react'
import MetricCard from '../components/MetricCard'
import ContributorChart from '../components/ContributorChart'
import { exportStats, getRepoStats } from '../lib/api'
import { Cell, Legend, Pie, PieChart, ResponsiveContainer } from 'recharts'

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
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    let active = true
    setLoading(true)
    getRepoStats('active')
      .then((nextStats) => {
        if (active) setStats(nextStats)
      })
      .catch(() => {
        if (active) setStats(null)
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [])

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

  const languageData = stats?.languages
    ? Object.entries(stats.languages).map(([name, value]) => ({ name, value: Number(value) }))
    : []

  const topExtensions = stats
    ? Object.entries(stats.extension_breakdown || stats.extensions || {})
        .sort((a: any, b: any) => Number(b[1]) - Number(a[1]))
        .slice(0, 8)
        .map(([name, value]) => `${name} (${value})`)
    : []

  return (
    <div className="p-6 h-full overflow-auto">
      <div className="flex items-center justify-between mb-4 gap-4">
        <div>
          <h2 className="text-2xl font-semibold">Repository Analytics</h2>
          <div className="text-sm text-muted">High-fidelity metrics, findings, and exports.</div>
        </div>
        <div className="flex gap-2">
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

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass p-4 rounded-md">
          <h4 className="font-semibold">Language Breakdown</h4>
          <div style={{ height: 260 }} className="mt-4">
            {loading ? (
              <div className="text-muted">Loading chart…</div>
            ) : languageData.length ? (
              <ResponsiveContainer>
                <PieChart>
                  <Pie
                    dataKey="value"
                    data={languageData}
                    outerRadius={90}
                    innerRadius={36}
                  >
                    {languageData.map((entry, index) => (
                      <Cell key={entry.name} fill={palette[index % palette.length]} />
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
    </div>
  )
}
