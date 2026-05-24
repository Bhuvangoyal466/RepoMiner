import React from 'react'

export default function Toast({children}:{children:React.ReactNode}){
  return (
    <div className="fixed top-6 right-6 bg-black/70 text-white p-3 rounded-md shadow-soft-lg">{children}</div>
  )
}
