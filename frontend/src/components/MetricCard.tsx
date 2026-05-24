import React from 'react'
import { motion } from 'framer-motion'

export default function MetricCard({title,value,sub}:{title:string,value:string|number,sub?:string}){
  return (
    <motion.div initial={{opacity:0, y:6}} animate={{opacity:1, y:0}} className="glass p-4 rounded-lg shadow-soft-lg">
      <div className="text-xs text-muted">{title}</div>
      <div className="mt-2 text-2xl font-bold">{value}</div>
      {sub && <div className="text-sm text-muted mt-1">{sub}</div>}
    </motion.div>
  )
}
