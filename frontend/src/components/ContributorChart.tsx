import React from 'react'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts'

export default function ContributorChart({data}:{data:{name:string, commits:number}[]}){
  const chartData = (data||[]).map(d=>({name:d.name, commits:d.commits}))
  const rowHeight = 28
  const minHeight = 160
  const height = Math.max(minHeight, chartData.length * rowHeight + 40)
  const longestName = chartData.reduce((max, d) => Math.max(max, d.name.length), 0)
  const yAxisWidth = Math.min(180, Math.max(80, longestName * 7))

  return (
    <div style={{height}}>
      <ResponsiveContainer>
        <BarChart data={chartData} layout="vertical" margin={{top: 4, right: 16, bottom: 4, left: 0}}>
          <XAxis type="number" tick={{fontSize: 11}} allowDecimals={false} />
          <YAxis
            type="category"
            dataKey="name"
            tick={{fontSize: 12}}
            width={yAxisWidth}
            interval={0}
          />
          <Tooltip cursor={{fill: 'rgba(255,255,255,0.04)'}} />
          <Bar dataKey="commits" fill="#7c5cff" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
