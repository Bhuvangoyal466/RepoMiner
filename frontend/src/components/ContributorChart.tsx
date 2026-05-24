import React from 'react'
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from 'recharts'

export default function ContributorChart({data}:{data:{name:string, commits:number}[]}){
  const chartData = (data||[]).map(d=>({name:d.name, commits:d.commits}))
  return (
    <div style={{height:220}}>
      <ResponsiveContainer>
        <BarChart data={chartData}>
          <XAxis dataKey="name" tick={{fontSize:11}} />
          <YAxis />
          <Tooltip />
          <Bar dataKey="commits" fill="#7c5cff" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
